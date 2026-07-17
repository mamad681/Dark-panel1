import asyncio
import json
import os
import hashlib
import secrets
import time
import aiofiles
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
from collections import deque, defaultdict
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import Response, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DarkPanel")

IRAN_TZ = ZoneInfo("Asia/Tehran")

app = FastAPI(title="Dark Panel", docs_url=None, redoc_url=None)

APP_NAME = "Dark Panel"
APP_CREATOR = "adel"

# ── Persistence ───────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / "darkpanel_state.json"
SECRET_FILE = DATA_DIR / "darkpanel_secret.key"
SAVE_LOCK = asyncio.Lock()


def _load_or_create_secret() -> str:
    env_secret = os.environ.get("SECRET_KEY")
    if env_secret:
        return env_secret
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SECRET_FILE.exists():
            existing = SECRET_FILE.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        new_secret = secrets.token_urlsafe(32)
        SECRET_FILE.write_text(new_secret, encoding="utf-8")
        return new_secret
    except Exception as e:
        logger.warning(f"Could not persist SECRET_KEY: {e}")
        return secrets.token_urlsafe(32)


CONFIG = {
    "port": int(os.environ.get("PORT", 8000)),
    "secret": _load_or_create_secret(),
    "host": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost"),
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Default super-admin credentials (overridable via env vars) ────────────────
DEFAULT_SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL", "mohammadadel.zare@gmail.com")
DEFAULT_SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "Adel5129")


def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}{CONFIG['secret']}".encode()).hexdigest()


# ── In-memory / persisted state ────────────────────────────────────────────────
SUPERADMIN: dict = {
    "email": DEFAULT_SUPERADMIN_EMAIL,
    "password_hash": hash_password(DEFAULT_SUPERADMIN_PASSWORD),
}
ADMINS: dict = {}          # admin_id -> {email, password_hash, created_at, expire_at, max_configs, active, note}
ADMINS_LOCK = asyncio.Lock()

LINKS: dict = {}           # config_id -> config dict  (kept name LINKS for relay-module compatibility)
LINKS_LOCK = asyncio.Lock()
SUBS: dict = {}            # sub-group_id -> {..., owner_admin_id}
SUBS_LOCK = asyncio.Lock()

connections: dict = {}
stats = {
    "total_bytes": 0,
    "total_requests": 0,
    "total_errors": 0,
    "start_time": time.time(),
}
error_logs: deque = deque(maxlen=50)
activity_logs: deque = deque(maxlen=200)
hourly_traffic: dict = defaultdict(int)
http_client: httpx.AsyncClient | None = None

# پروتکل‌های پشتیبانی‌شده برای هر کانفیگ (سازگار با کلاینت‌های V2Ray/Xray/Hiddify)
PROTOCOLS = ("vless-ws", "vless-xhttp-packet-up", "vless-xhttp-stream-up", "trojan-ws")
DEFAULT_PROTOCOL = "vless-ws"
PROTOCOL_LABELS = {
    "vless-ws": "VLESS · WebSocket",
    "vless-xhttp-packet-up": "VLESS · XHTTP (packet-up)",
    "vless-xhttp-stream-up": "VLESS · XHTTP (stream-up)",
    "trojan-ws": "Trojan · WebSocket",
}

FINGERPRINTS = ("chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized")
DEFAULT_FINGERPRINT = "chrome"

DEFAULT_ALPN_BY_PROTOCOL = {
    "vless-ws": "http/1.1",
    "vless-xhttp-packet-up": "h2,http/1.1",
    "vless-xhttp-stream-up": "h2,http/1.1",
    "trojan-ws": "http/1.1",
}
DEFAULT_PORT = 443
MIN_PORT, MAX_PORT = 1, 65535
DEFAULT_SPEED_LIMIT = 0


def log_activity(kind: str, message: str, level: str = "info"):
    activity_logs.append({
        "kind": kind,
        "level": level,
        "message": message,
        "time": datetime.now().isoformat(),
    })


async def load_state():
    global LINKS, SUBS, ADMINS, SUPERADMIN
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = await f.read()
            data = json.loads(raw)
            LINKS.update(data.get("links", {}))
            SUBS.update(data.get("subs", {}))
            ADMINS.update(data.get("admins", {}))
            if "superadmin" in data:
                if not os.environ.get("SUPERADMIN_EMAIL") and not os.environ.get("SUPERADMIN_PASSWORD"):
                    SUPERADMIN.update(data["superadmin"])
            logger.info(f"State loaded: {len(LINKS)} configs, {len(ADMINS)} admins, {len(SUBS)} subs")
    except Exception as e:
        logger.warning(f"Could not load state: {e}")


async def save_state():
    async with SAVE_LOCK:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "links": dict(LINKS),
                "subs": dict(SUBS),
                "admins": dict(ADMINS),
                "superadmin": dict(SUPERADMIN),
                "saved_at": datetime.now().isoformat(),
            }
            tmp = DATA_FILE.with_suffix(".tmp")
            async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            tmp.replace(DATA_FILE)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")


# ── Auth (sessions) ────────────────────────────────────────────────────────────
SESSION_COOKIE = "dp_session"
SESSION_TTL = 60 * 60 * 24 * 30  # 30 روز

SESSIONS: dict = {}   # token -> {"role": "super"|"admin", "admin_id": str|None, "exp": float}
SESSIONS_LOCK = asyncio.Lock()


async def create_session(role: str, admin_id: str | None) -> str:
    token = secrets.token_urlsafe(32)
    async with SESSIONS_LOCK:
        SESSIONS[token] = {"role": role, "admin_id": admin_id, "exp": time.time() + SESSION_TTL}
    return token


async def get_session(token: str | None) -> dict | None:
    if not token:
        return None
    async with SESSIONS_LOCK:
        s = SESSIONS.get(token)
        if s is None:
            return None
        if s["exp"] < time.time():
            SESSIONS.pop(token, None)
            return None
        return s


async def destroy_session(token: str | None):
    if not token:
        return
    async with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


async def require_session(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    s = await get_session(token)
    if s is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if s["role"] == "admin":
        admin = ADMINS.get(s["admin_id"])
        if admin is None or not admin_is_usable(admin):
            await destroy_session(token)
            raise HTTPException(status_code=401, detail="admin disabled or expired")
    return s


async def require_super(request: Request) -> dict:
    s = await require_session(request)
    if s["role"] != "super":
        raise HTTPException(status_code=403, detail="forbidden")
    return s


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global http_client
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
    timeout = httpx.Timeout(30.0, connect=10.0)
    http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
    await load_state()
    log_activity("system", "سرور راه‌اندازی شد", "ok")
    logger.info(f"{APP_NAME} started on port {CONFIG['port']}")


@app.on_event("shutdown")
async def shutdown():
    await save_state()
    if http_client:
        await http_client.aclose()


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_host(request: Request | None = None) -> str:
    if request is not None:
        h = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if h:
            h = h.split(":")[0]
            CONFIG["host"] = h
            return h
    return os.environ.get("RAILWAY_PUBLIC_DOMAIN", CONFIG["host"])


def generate_uuid() -> str:
    h = secrets.token_hex(16)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def generate_trojan_password() -> str:
    return secrets.token_hex(16)


def now_ir() -> datetime:
    return datetime.now(IRAN_TZ)


def parse_size_to_bytes(value: float, unit: str) -> int:
    unit = (unit or "GB").upper()
    if unit == "GB": return int(value * 1024 ** 3)
    if unit == "MB": return int(value * 1024 ** 2)
    if unit == "KB": return int(value * 1024)
    return int(value)


def parse_speed_to_bytes(value: float, unit: str) -> int:
    if value <= 0:
        return 0
    unit = (unit or "MBIT").upper()
    if unit == "MBIT":
        return int(value * 1024 * 1024 / 8)
    if unit == "KB":
        return int(value * 1024)
    if unit == "MB":
        return int(value * 1024 * 1024)
    return int(value)


def fmt_bytes(b: int) -> str:
    if b < 1024: return f"{b} B"
    if b < 1024 ** 2: return f"{b/1024:.1f} KB"
    if b < 1024 ** 3: return f"{b/1024**2:.2f} MB"
    return f"{b/1024**3:.2f} GB"


def uptime() -> str:
    secs = int(time.time() - stats["start_time"])
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ── Admin helpers ──────────────────────────────────────────────────────────────
def admin_is_usable(admin: dict) -> bool:
    if not admin.get("active", True):
        return False
    exp = admin.get("expire_at")
    if exp:
        try:
            if datetime.now() > datetime.fromisoformat(exp):
                return False
        except Exception:
            pass
    return True


def admin_public(admin_id: str, admin: dict) -> dict:
    used = sum(1 for l in LINKS.values() if l.get("owner_admin_id") == admin_id)
    exp = admin.get("expire_at")
    days_left = None
    expired = False
    if exp:
        try:
            delta = datetime.fromisoformat(exp) - datetime.now()
            days_left = max(0, delta.days + (1 if delta.seconds > 0 else 0))
            expired = delta.total_seconds() < 0
        except Exception:
            pass
    return {
        "id": admin_id,
        "email": admin.get("email"),
        "created_at": admin.get("created_at"),
        "expire_at": exp,
        "days_left": days_left,
        "expired": expired,
        "max_configs": admin.get("max_configs", 0),
        "used_configs": used,
        "active": admin.get("active", True),
        "note": admin.get("note", ""),
        "usable": admin_is_usable(admin),
    }


def owner_allowed(owner_admin_id: str | None) -> bool:
    if owner_admin_id is None:
        return True
    admin = ADMINS.get(owner_admin_id)
    if admin is None:
        return False
    return admin_is_usable(admin)


# ── Link (config) generation ──────────────────────────────────────────────────
def generate_vless_link(uuid: str, host: str, remark: str, protocol: str,
                         fingerprint: str | None = None, alpn: str | None = None,
                         port: int | None = None) -> str:
    fp = (fingerprint or DEFAULT_FINGERPRINT).strip() or DEFAULT_FINGERPRINT
    if fp not in FINGERPRINTS:
        fp = DEFAULT_FINGERPRINT
    alpn_val = (alpn or "").strip() or DEFAULT_ALPN_BY_PROTOCOL.get(protocol, "http/1.1")
    port_val = port or DEFAULT_PORT
    if not (MIN_PORT <= port_val <= MAX_PORT):
        port_val = DEFAULT_PORT

    if protocol == "vless-ws":
        path = f"/ws/{uuid}"
        params = {"encryption": "none", "security": "tls", "type": "ws",
                  "host": host, "path": path, "sni": host, "fp": fp, "alpn": alpn_val}
    else:
        mode = protocol.replace("vless-xhttp-", "")
        path = f"/xhttp-siz10/{mode}/{uuid}"
        params = {"encryption": "none", "security": "tls", "type": "xhttp", "mode": mode,
                  "host": host, "path": path, "sni": host, "fp": fp, "alpn": alpn_val}
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"vless://{uuid}@{host}:{port_val}?{query}#{quote(remark)}"


def generate_trojan_link(config_id: str, password: str, host: str, remark: str,
                          fingerprint: str | None = None, alpn: str | None = None,
                          port: int | None = None) -> str:
    fp = (fingerprint or DEFAULT_FINGERPRINT).strip() or DEFAULT_FINGERPRINT
    if fp not in FINGERPRINTS:
        fp = DEFAULT_FINGERPRINT
    alpn_val = (alpn or "").strip() or DEFAULT_ALPN_BY_PROTOCOL.get("trojan-ws", "http/1.1")
    port_val = port or DEFAULT_PORT
    if not (MIN_PORT <= port_val <= MAX_PORT):
        port_val = DEFAULT_PORT
    path = f"/trojan-ws/{config_id}"
    params = {"security": "tls", "type": "ws", "host": host, "path": path,
              "sni": host, "fp": fp, "alpn": alpn_val}
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"trojan://{password}@{host}:{port_val}?{query}#{quote(remark)}"


def link_share_url(link: dict, host: str) -> str:
    remark = f"{APP_NAME}-{link.get('label','')}"
    proto = link.get("protocol", DEFAULT_PROTOCOL)
    if proto == "trojan-ws":
        return generate_trojan_link(
            link["id"], link["secret"], host, remark,
            fingerprint=link.get("fingerprint"), alpn=link.get("alpn"), port=link.get("port"),
        )
    return generate_vless_link(
        link["id"], host, remark, proto,
        fingerprint=link.get("fingerprint"), alpn=link.get("alpn"), port=link.get("port"),
    )


def is_link_expired(link: dict) -> bool:
    exp = link.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.now() > datetime.fromisoformat(exp)
    except Exception:
        return False


def is_link_allowed(link: dict | None) -> bool:
    if link is None:
        return False
    if not link.get("active", True):
        return False
    if is_link_expired(link):
        return False
    if not owner_allowed(link.get("owner_admin_id")):
        return False
    lb = link.get("limit_bytes", 0)
    if lb > 0 and link.get("used_bytes", 0) >= lb:
        return False
    return True


def unique_ips_for_uuid(uuid: str) -> set:
    return {c.get("ip") for c in connections.values() if c.get("uuid") == uuid and c.get("ip")}


def is_ip_allowed(link: dict | None, uuid: str, ip: str) -> bool:
    if link is None:
        return False
    limit = int(link.get("ip_limit", 0) or 0)
    if limit <= 0:
        return True
    ips = unique_ips_for_uuid(uuid)
    if ip in ips:
        return True
    return len(ips) < limit


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "نامشخص"


def link_public(link: dict, host: str) -> dict:
    d = dict(link)
    d["share_url"] = link_share_url(link, host)
    d["protocol_label"] = PROTOCOL_LABELS.get(link.get("protocol"), link.get("protocol"))
    d["expired"] = is_link_expired(link)
    d["allowed"] = is_link_allowed(link)
    return d


# ── Basic endpoints ────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return RedirectResponse(url="/login")


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "uptime": uptime()}


# ── Auth API ───────────────────────────────────────────────────────────────────
@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="ایمیل و رمز عبور الزامی است")

    pw_hash = hash_password(password)

    if email == SUPERADMIN["email"].strip().lower() and pw_hash == SUPERADMIN["password_hash"]:
        token = await create_session("super", None)
        resp = JSONResponse({"ok": True, "role": "super"})
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                         max_age=SESSION_TTL, secure=request.url.scheme == "https")
        log_activity("auth", "ورود سوپر ادمین", "ok")
        return resp

    for admin_id, admin in ADMINS.items():
        if admin.get("email", "").strip().lower() == email and admin.get("password_hash") == pw_hash:
            if not admin_is_usable(admin):
                raise HTTPException(status_code=403, detail="حساب ادمین غیرفعال یا منقضی شده است")
            token = await create_session("admin", admin_id)
            resp = JSONResponse({"ok": True, "role": "admin"})
            resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                             max_age=SESSION_TTL, secure=request.url.scheme == "https")
            log_activity("auth", f"ورود ادمین {email}", "ok")
            return resp

    raise HTTPException(status_code=401, detail="ایمیل یا رمز عبور اشتباه است")


@app.post("/api/logout")
async def api_logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    await destroy_session(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/api/me")
async def api_me(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    s = await get_session(token)
    if s is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if s["role"] == "super":
        return {"role": "super", "email": SUPERADMIN["email"]}
    admin = ADMINS.get(s["admin_id"])
    if admin is None or not admin_is_usable(admin):
        await destroy_session(token)
        raise HTTPException(status_code=401, detail="admin disabled or expired")
    return {"role": "admin", **admin_public(s["admin_id"], admin)}


@app.post("/api/change-password")
async def api_change_password(request: Request, s=Depends(require_session)):
    body = await request.json()
    new_password = (body.get("password") or "").strip()
    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="رمز عبور جدید خیلی کوتاه است")
    if s["role"] == "super":
        SUPERADMIN["password_hash"] = hash_password(new_password)
    else:
        ADMINS[s["admin_id"]]["password_hash"] = hash_password(new_password)
    await save_state()
    return {"ok": True}


# ── Super-admin: manage admins/resellers ──────────────────────────────────────
@app.get("/api/admins")
async def list_admins(_=Depends(require_super)):
    return [admin_public(aid, a) for aid, a in ADMINS.items()]


@app.post("/api/admins")
async def create_admin(request: Request, _=Depends(require_super)):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    expire_days = body.get("expire_days")
    max_configs = int(body.get("max_configs") or 0)
    note = (body.get("note") or "").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="ایمیل معتبر وارد کنید")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="رمز عبور خیلی کوتاه است")
    if email == SUPERADMIN["email"].strip().lower():
        raise HTTPException(status_code=400, detail="این ایمیل متعلق به سوپر ادمین است")

    async with ADMINS_LOCK:
        for a in ADMINS.values():
            if a.get("email", "").strip().lower() == email:
                raise HTTPException(status_code=400, detail="این ایمیل قبلاً ثبت شده است")
        admin_id = secrets.token_hex(8)
        expire_at = None
        if expire_days is not None and str(expire_days).strip() != "":
            expire_at = (datetime.now() + timedelta(days=int(expire_days))).isoformat()
        ADMINS[admin_id] = {
            "email": email,
            "password_hash": hash_password(password),
            "created_at": datetime.now().isoformat(),
            "expire_at": expire_at,
            "max_configs": max_configs,
            "active": True,
            "note": note,
        }
    await save_state()
    log_activity("admin", f"ادمین جدید ساخته شد: {email}", "ok")
    return admin_public(admin_id, ADMINS[admin_id])


@app.patch("/api/admins/{admin_id}")
async def update_admin(admin_id: str, request: Request, _=Depends(require_super)):
    admin = ADMINS.get(admin_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="ادمین یافت نشد")
    body = await request.json()

    if "password" in body and body["password"]:
        if len(body["password"]) < 4:
            raise HTTPException(status_code=400, detail="رمز عبور خیلی کوتاه است")
        admin["password_hash"] = hash_password(body["password"])
    if "active" in body:
        admin["active"] = bool(body["active"])
    if "max_configs" in body:
        admin["max_configs"] = int(body["max_configs"] or 0)
    if "note" in body:
        admin["note"] = (body["note"] or "").strip()
    if "add_days" in body and body["add_days"]:
        add_days = int(body["add_days"])
        base = datetime.now()
        if admin.get("expire_at"):
            try:
                current = datetime.fromisoformat(admin["expire_at"])
                if current > base:
                    base = current
            except Exception:
                pass
        admin["expire_at"] = (base + timedelta(days=add_days)).isoformat()
    if "expire_days" in body:
        ed = body["expire_days"]
        admin["expire_at"] = (datetime.now() + timedelta(days=int(ed))).isoformat() if ed not in (None, "") else None

    await save_state()
    log_activity("admin", f"ادمین {admin['email']} ویرایش شد", "info")
    return admin_public(admin_id, admin)


@app.delete("/api/admins/{admin_id}")
async def delete_admin(admin_id: str, _=Depends(require_super)):
    admin = ADMINS.pop(admin_id, None)
    if admin is None:
        raise HTTPException(status_code=404, detail="ادمین یافت نشد")
    removed = [cid for cid, l in LINKS.items() if l.get("owner_admin_id") == admin_id]
    for cid in removed:
        LINKS.pop(cid, None)
    await save_state()
    log_activity("admin", f"ادمین {admin['email']} حذف شد ({len(removed)} کانفیگ حذف شد)", "warn")
    return {"ok": True, "removed_configs": len(removed)}


# ── Configs (created by admins; super-admin can view all) ────────────────────
@app.get("/api/links")
async def list_links(request: Request, s=Depends(require_session)):
    host = get_host(request)
    items = LINKS.values()
    if s["role"] == "admin":
        items = [l for l in items if l.get("owner_admin_id") == s["admin_id"]]
    return [link_public(l, host) for l in items]


@app.post("/api/links")
async def create_link(request: Request, s=Depends(require_session)):
    if s["role"] != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین‌ها می‌توانند کانفیگ بسازند")
    admin = ADMINS.get(s["admin_id"])
    if admin is None or not admin_is_usable(admin):
        raise HTTPException(status_code=403, detail="حساب شما غیرفعال یا منقضی شده است")

    max_configs = int(admin.get("max_configs", 0) or 0)
    if max_configs > 0:
        used = sum(1 for l in LINKS.values() if l.get("owner_admin_id") == s["admin_id"])
        if used >= max_configs:
            raise HTTPException(status_code=403, detail=f"سقف تعداد کانفیگ شما ({max_configs}) پر شده است")

    body = await request.json()
    label = (body.get("label") or "کانفیگ جدید").strip()
    protocol = body.get("protocol") or DEFAULT_PROTOCOL
    if protocol not in PROTOCOLS:
        raise HTTPException(status_code=400, detail="پروتکل نامعتبر است")

    limit_value = float(body.get("limit_value") or 0)
    limit_unit = body.get("limit_unit") or "GB"
    limit_bytes = parse_size_to_bytes(limit_value, limit_unit)

    speed_value = float(body.get("speed_value") or 0)
    speed_unit = body.get("speed_unit") or "MBIT"
    speed_limit_bytes = parse_speed_to_bytes(speed_value, speed_unit)

    ip_limit = int(body.get("ip_limit") or 0)
    port = int(body.get("port") or DEFAULT_PORT)
    if not (MIN_PORT <= port <= MAX_PORT):
        port = DEFAULT_PORT
    fingerprint = (body.get("fingerprint") or DEFAULT_FINGERPRINT).strip() or DEFAULT_FINGERPRINT
    if fingerprint not in FINGERPRINTS:
        fingerprint = DEFAULT_FINGERPRINT
    alpn = (body.get("alpn") or "").strip()

    expire_days = body.get("expire_days")
    expires_at = None
    if expire_days is not None and str(expire_days).strip() != "":
        expires_at = (datetime.now() + timedelta(days=int(expire_days))).isoformat()

    config_id = generate_uuid()
    if protocol == "trojan-ws":
        secret = generate_trojan_password()
        auth_hash = hashlib.sha224(secret.encode()).hexdigest()
    else:
        secret = config_id
        auth_hash = None

    link = {
        "id": config_id,
        "owner_admin_id": s["admin_id"],
        "protocol": protocol,
        "secret": secret,
        "auth_hash": auth_hash,
        "label": label,
        "limit_bytes": limit_bytes,
        "used_bytes": 0,
        "created_at": datetime.now().isoformat(),
        "active": True,
        "expires_at": expires_at,
        "note": "",
        "sub_id": None,
        "fingerprint": fingerprint,
        "alpn": alpn,
        "port": port,
        "ip_limit": ip_limit,
        "speed_limit_bytes": speed_limit_bytes,
    }
    async with LINKS_LOCK:
        LINKS[config_id] = link
    await save_state()
    log_activity("link", f"کانفیگ «{label}» ساخته شد ({PROTOCOL_LABELS.get(protocol)})", "ok")
    return link_public(link, get_host(request))


def _get_owned_link_or_404(config_id: str, s: dict) -> dict:
    link = LINKS.get(config_id)
    if link is None:
        raise HTTPException(status_code=404, detail="کانفیگ یافت نشد")
    if s["role"] == "admin" and link.get("owner_admin_id") != s["admin_id"]:
        raise HTTPException(status_code=403, detail="دسترسی ندارید")
    return link


@app.patch("/api/links/{config_id}")
async def update_link(config_id: str, request: Request, s=Depends(require_session)):
    link = _get_owned_link_or_404(config_id, s)
    body = await request.json()

    if "active" in body:
        link["active"] = bool(body["active"])
    if "label" in body:
        link["label"] = (body["label"] or link["label"]).strip()
    if "limit_value" in body:
        link["limit_bytes"] = parse_size_to_bytes(float(body.get("limit_value") or 0), body.get("limit_unit") or "GB")
    if "speed_value" in body:
        link["speed_limit_bytes"] = parse_speed_to_bytes(float(body.get("speed_value") or 0), body.get("speed_unit") or "MBIT")
    if "ip_limit" in body:
        link["ip_limit"] = int(body["ip_limit"] or 0)
    if "expire_days" in body:
        ed = body["expire_days"]
        link["expires_at"] = (datetime.now() + timedelta(days=int(ed))).isoformat() if ed not in (None, "") else None
    if "reset_usage" in body and body["reset_usage"]:
        link["used_bytes"] = 0

    await save_state()
    return link_public(link, get_host(request))


@app.delete("/api/links/{config_id}")
async def delete_link(config_id: str, s=Depends(require_session)):
    link = _get_owned_link_or_404(config_id, s)
    async with LINKS_LOCK:
        LINKS.pop(config_id, None)
    await save_state()
    log_activity("link", f"کانفیگ «{link['label']}» حذف شد", "warn")
    return {"ok": True}


# ── Stats / activity (dashboard widgets) ──────────────────────────────────────
@app.get("/stats")
async def get_stats(s=Depends(require_session)):
    if s["role"] == "admin":
        own_ids = {cid for cid, l in LINKS.items() if l.get("owner_admin_id") == s["admin_id"]}
        conns = [c for c in connections.values() if c.get("uuid") in own_ids]
        used_bytes = sum(l.get("used_bytes", 0) for l in LINKS.values() if l.get("owner_admin_id") == s["admin_id"])
        return {
            "total_configs": len(own_ids),
            "active_connections": len(conns),
            "used_bytes": used_bytes,
            "used_fmt": fmt_bytes(used_bytes),
            "uptime": uptime(),
        }
    return {
        "total_admins": len(ADMINS),
        "total_configs": len(LINKS),
        "active_connections": len(connections),
        "total_bytes": stats["total_bytes"],
        "total_bytes_fmt": fmt_bytes(stats["total_bytes"]),
        "total_requests": stats["total_requests"],
        "total_errors": stats["total_errors"],
        "uptime": uptime(),
    }


@app.get("/api/activity")
async def get_activity(s=Depends(require_session)):
    if s["role"] == "super":
        return list(activity_logs)[-100:]
    return []


# ── Public subscription (base64) ──────────────────────────────────────────────
@app.get("/sub/{config_id}")
async def subscription_single(config_id: str, request: Request):
    link = LINKS.get(config_id)
    if link is None or not is_link_allowed(link):
        raise HTTPException(status_code=404, detail="not found")
    import base64
    content = link_share_url(link, get_host(request))
    return Response(content=base64.b64encode(content.encode()).decode(), media_type="text/plain")


# ── Login / dashboard pages ───────────────────────────────────────────────────
from pages import render_login_page, render_admin_dashboard, render_super_dashboard


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return HTMLResponse(render_login_page())


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    s = await get_session(token)
    if s is None:
        return RedirectResponse(url="/login")
    if s["role"] == "super":
        return HTMLResponse(render_super_dashboard())
    admin = ADMINS.get(s["admin_id"])
    if admin is None or not admin_is_usable(admin):
        await destroy_session(token)
        return RedirectResponse(url="/login")
    return HTMLResponse(render_admin_dashboard())


# ── Relay endpoints (VLESS / Trojan over WebSocket, VLESS over XHTTP) ─────────
from relay_vless import websocket_tunnel
from relay_trojan import trojan_websocket_tunnel
from xhttp_siz10 import router as xhttp_router

app.include_router(xhttp_router)


@app.websocket("/ws/{config_id}")
async def ws_endpoint(websocket: WebSocket, config_id: str):
    await websocket_tunnel(websocket, config_id)


@app.websocket("/trojan-ws/{config_id}")
async def trojan_ws_endpoint(websocket: WebSocket, config_id: str):
    await trojan_websocket_tunnel(websocket, config_id)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=CONFIG["port"], log_level="info")
