# pages.py — Dark Panel
# صفحات HTML: ورود، داشبورد سوپر ادمین، داشبورد ادمین
# ساخته شده توسط adel

BASE_STYLE = r"""
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#05070d;--card:rgba(13,17,28,0.92);--accent:#6C5CE7;--accent2:#00D9C0;--text:#EAF0FF;--dim:#5b6b8c;--mid:#9BB0D6;--border:rgba(108,92,231,0.22);--danger:#F87171;--ok:#34D399;--warn:#FBBF24}
html,body{min-height:100%;background:var(--bg)}
body{font-family:'Vazirmatn',sans-serif;color:var(--text)}
.bg{position:fixed;inset:0;background:radial-gradient(ellipse 80% 50% at 50% 0%,rgba(108,92,231,0.12),transparent 70%),var(--bg);z-index:-2}
.grid{position:fixed;inset:0;background-image:linear-gradient(rgba(108,92,231,0.05) 1px,transparent 1px),linear-gradient(90deg,rgba(108,92,231,0.05) 1px,transparent 1px);background-size:44px 44px;z-index:-1}
a{color:inherit}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:16px 26px;border-bottom:1px solid var(--border);background:rgba(10,13,22,.7);backdrop-filter:blur(14px);position:sticky;top:0;z-index:50}
.brand{display:flex;align-items:center;gap:12px}
.brand .logo{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-weight:800;font-size:16px;box-shadow:0 0 22px rgba(108,92,231,.45)}
.brand-name{font-weight:800;font-size:16px}
.brand-sub{font-size:11px;color:var(--dim)}
.container{max-width:1180px;margin:0 auto;padding:26px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:22px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px}
.stat-card .label{font-size:11.5px;color:var(--dim);margin-bottom:8px}
.stat-card .value{font-size:22px;font-weight:800}
.panel{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:22px;margin-bottom:20px}
.panel h2{font-size:15px;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.btn{padding:9px 16px;border-radius:10px;border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;transition:.15s;display:inline-flex;align-items:center;gap:6px}
.btn-primary{background:linear-gradient(135deg,var(--accent),#8b7cf6);color:#fff;box-shadow:0 4px 16px rgba(108,92,231,.32)}
.btn-primary:hover{filter:brightness(1.08)}
.btn-ghost{background:rgba(255,255,255,.05);color:var(--text);border:1px solid var(--border)}
.btn-danger{background:rgba(248,113,113,.12);color:var(--danger);border:1px solid rgba(248,113,113,.3)}
.btn-sm{padding:6px 11px;font-size:12px;border-radius:8px}
.btn:disabled{opacity:.45;cursor:not-allowed}
.grid-form{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:14px}
.field label{display:block;font-size:11px;color:var(--mid);margin-bottom:6px;font-weight:600}
.field input,.field select{width:100%;padding:10px 12px;border-radius:9px;border:1px solid var(--border);background:rgba(0,0,0,.28);color:var(--text);font-family:inherit;font-size:13px;outline:none}
.field input:focus,.field select:focus{border-color:rgba(108,92,231,.6)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:right;font-size:11px;color:var(--dim);font-weight:600;padding:9px 10px;border-bottom:1px solid var(--border)}
td{padding:11px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}
tr:hover td{background:rgba(255,255,255,.015)}
.badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;display:inline-block}
.badge-ok{background:rgba(52,211,153,.14);color:var(--ok)}
.badge-warn{background:rgba(251,191,36,.14);color:var(--warn)}
.badge-danger{background:rgba(248,113,113,.14);color:var(--danger)}
.badge-mid{background:rgba(155,176,214,.14);color:var(--mid)}
.mono{font-family:ui-monospace,monospace;font-size:12px}
.bar-bg{width:100%;height:6px;background:rgba(255,255,255,.08);border-radius:6px;overflow:hidden;margin-top:6px}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--accent2),var(--accent));border-radius:6px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#111624;border:1px solid var(--border);padding:12px 22px;border-radius:12px;font-size:13px;z-index:999;opacity:0;pointer-events:none;transition:.25s}
.toast.show{opacity:1;transform:translateX(-50%) translateY(-6px)}
.toast.err{border-color:rgba(248,113,113,.4);color:var(--danger)}
.toast.ok{border-color:rgba(52,211,153,.4);color:var(--ok)}
.icon-btn{background:none;border:none;color:var(--dim);cursor:pointer;font-size:16px;padding:4px}
.icon-btn:hover{color:var(--text)}
.empty{text-align:center;padding:40px 10px;color:var(--dim);font-size:13px}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:200;backdrop-filter:blur(4px)}
.modal-bg.show{display:flex}
.modal{background:#0d111c;border:1px solid var(--border);border-radius:16px;padding:22px;max-width:360px;width:92%}
.modal h3{font-size:14px;margin-bottom:14px}
.row{display:flex;gap:8px;align-items:center}
.small{font-size:11.5px;color:var(--dim)}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:rgba(108,92,231,.35);border-radius:4px}
"""

HEAD = r"""<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
"""


def render_login_page() -> str:
    return r"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>""" + HEAD + r"""<title>ورود · Dark Panel</title>
<style>""" + BASE_STYLE + r"""
html,body{height:100%;overflow:hidden}
body{display:flex;align-items:center;justify-content:center;padding:20px}
.wrap{width:100%;max-width:400px;position:relative;z-index:2}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:36px 32px;backdrop-filter:blur(20px);box-shadow:0 20px 60px rgba(0,0,0,.5)}
h1{font-size:20px;font-weight:800;margin-bottom:4px}
.sub{font-size:12px;color:var(--mid);margin-bottom:22px}
.err{display:none;background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.25);border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:12.5px;color:var(--danger);align-items:center;gap:8px}
.err.show{display:flex}
.field{margin-bottom:16px}
.field label{display:block;font-size:11px;color:var(--mid);margin-bottom:7px;font-weight:600}
.field input{width:100%;padding:12px 14px;border-radius:11px;border:1px solid var(--border);background:rgba(0,0,0,.32);color:var(--text);font-family:inherit;font-size:14px;outline:none}
.field input:focus{border-color:rgba(108,92,231,.6);box-shadow:0 0 0 3px rgba(108,92,231,.1)}
.footer{margin-top:20px;text-align:center;font-size:11px;color:var(--dim)}
</style></head>
<body>
<div class="bg"></div><div class="grid"></div>
<div class="wrap"><div class="card">
  <div class="brand" style="margin-bottom:22px"><div class="logo">DP</div>
    <div><div class="brand-name">Dark Panel</div><div class="brand-sub">پنل مدیریت کانفیگ V2Ray / Xray</div></div></div>
  <h1>ورود به پنل</h1>
  <p class="sub">ایمیل و رمز عبور خود را وارد کنید</p>
  <div class="err" id="err"><i class="ti ti-alert-circle"></i><span id="err-text"></span></div>
  <form id="form">
    <div class="field"><label>ایمیل</label><input type="email" id="email" required autofocus></div>
    <div class="field"><label>رمز عبور</label><input type="password" id="pw" required></div>
    <button class="btn btn-primary" type="submit" style="width:100%;justify-content:center;padding:12px"><i class="ti ti-login-2"></i> ورود</button>
  </form>
  <div class="footer">Dark Panel · ساخته‌شده توسط <b>adel</b></div>
</div></div>
<script>
document.getElementById('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const err = document.getElementById('err');
  err.classList.remove('show');
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('pw').value;
  try {
    const r = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password})});
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'خطا در ورود');
    window.location.href = '/dashboard';
  } catch (ex) {
    document.getElementById('err-text').textContent = ex.message;
    err.classList.add('show');
  }
});
</script>
</body></html>"""


TOPBAR_TEMPLATE = r"""
<div class="topbar">
  <div class="brand"><div class="logo">DP</div>
    <div><div class="brand-name">Dark Panel</div><div class="brand-sub">__ROLE_LABEL__</div></div></div>
  <div class="row">
    <span class="small" id="whoami"></span>
    <button class="btn btn-ghost btn-sm" onclick="logout()"><i class="ti ti-logout"></i> خروج</button>
  </div>
</div>
"""

COMMON_JS = r"""
async function api(path, opts) {
  opts = opts || {};
  opts.headers = Object.assign({'Content-Type':'application/json'}, opts.headers || {});
  const r = await fetch(path, opts);
  let d = null;
  try { d = await r.json(); } catch(e) {}
  if (!r.ok) { throw new Error((d && d.detail) || ('خطا: ' + r.status)); }
  return d;
}
function toast(msg, ok) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + (ok ? 'ok' : 'err');
  setTimeout(() => t.classList.remove('show'), 3200);
}
async function logout() {
  try { await api('/api/logout', {method:'POST'}); } catch(e) {}
  window.location.href = '/login';
}
function fmtBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024**2) return (b/1024).toFixed(1) + ' KB';
  if (b < 1024**3) return (b/1024**2).toFixed(2) + ' MB';
  return (b/1024**3).toFixed(2) + ' GB';
}
function copyText(t) {
  navigator.clipboard.writeText(t).then(() => toast('لینک کپی شد', true));
}
function showQR(url) {
  const box = document.getElementById('qr-box');
  document.getElementById('qr-img').src = 'https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=' + encodeURIComponent(url);
  box.classList.add('show');
}
function closeModal(id) { document.getElementById(id).classList.remove('show'); }
"""


def render_super_dashboard() -> str:
    topbar = TOPBAR_TEMPLATE.replace("__ROLE_LABEL__", "پنل سوپر ادمین")
    return r"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>""" + HEAD + r"""<title>داشبورد سوپر ادمین · Dark Panel</title>
<style>""" + BASE_STYLE + r"""</style></head>
<body>
<div class="bg"></div><div class="grid"></div>
""" + topbar + r"""
<div class="container">

  <div class="cards" id="stat-cards"></div>

  <div class="panel">
    <h2><i class="ti ti-users"></i> مدیریت ادمین‌ها / نماینده‌ها</h2>

    <div class="grid-form" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
      <div class="field"><label>ایمیل ادمین</label><input id="na-email" type="email" placeholder="admin@example.com"></div>
      <div class="field"><label>رمز عبور</label><input id="na-pass" type="text" placeholder="رمز عبور"></div>
      <div class="field"><label>اعتبار (روز)</label><input id="na-days" type="number" min="0" placeholder="مثلاً 30"></div>
      <div class="field"><label>سقف تعداد کانفیگ</label><input id="na-max" type="number" min="0" placeholder="0 = نامحدود"></div>
      <div class="field"><label>توضیح (اختیاری)</label><input id="na-note" type="text" placeholder="یادداشت"></div>
    </div>
    <button class="btn btn-primary" onclick="createAdmin()"><i class="ti ti-user-plus"></i> ساخت ادمین جدید</button>

    <div style="margin-top:20px;overflow-x:auto">
      <table>
        <thead><tr><th>ایمیل</th><th>وضعیت</th><th>اعتبار</th><th>کانفیگ‌ها</th><th>یادداشت</th><th>عملیات</th></tr></thead>
        <tbody id="admins-body"></tbody>
      </table>
      <div class="empty" id="admins-empty" style="display:none">هنوز ادمینی ساخته نشده است</div>
    </div>
  </div>

  <div class="panel">
    <h2><i class="ti ti-list-details"></i> همه‌ی کانفیگ‌ها (نمای کلی)</h2>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>برچسب</th><th>پروتکل</th><th>ادمین سازنده</th><th>مصرف</th><th>وضعیت</th></tr></thead>
        <tbody id="links-body"></tbody>
      </table>
      <div class="empty" id="links-empty" style="display:none">هنوز کانفیگی ساخته نشده است</div>
    </div>
  </div>

</div>

<div class="modal-bg" id="qr-box" onclick="if(event.target===this) closeModal('qr-box')">
  <div class="modal" style="text-align:center">
    <h3>QR Code</h3>
    <img id="qr-img" style="width:240px;height:240px;border-radius:12px;background:#fff;padding:8px">
    <div style="margin-top:14px"><button class="btn btn-ghost btn-sm" onclick="closeModal('qr-box')">بستن</button></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>""" + COMMON_JS + r"""

let ADMINS_CACHE = [];

function daysBadge(a) {
  if (!a.expire_at) return '<span class="badge badge-mid">بدون انقضا</span>';
  if (a.expired) return '<span class="badge badge-danger">منقضی شده</span>';
  return '<span class="badge badge-ok">' + a.days_left + ' روز مانده</span>';
}

async function loadStats() {
  const s = await api('/stats');
  document.getElementById('stat-cards').innerHTML = `
    <div class="stat-card"><div class="label">تعداد ادمین‌ها</div><div class="value">${s.total_admins}</div></div>
    <div class="stat-card"><div class="label">کل کانفیگ‌ها</div><div class="value">${s.total_configs}</div></div>
    <div class="stat-card"><div class="label">اتصالات زنده</div><div class="value">${s.active_connections}</div></div>
    <div class="stat-card"><div class="label">حجم کل مصرفی</div><div class="value">${s.total_bytes_fmt}</div></div>
  `;
}

async function loadAdmins() {
  const admins = await api('/api/admins');
  ADMINS_CACHE = admins;
  const body = document.getElementById('admins-body');
  document.getElementById('admins-empty').style.display = admins.length ? 'none' : 'block';
  body.innerHTML = admins.map(a => `
    <tr>
      <td class="mono">${a.email}</td>
      <td>${a.active ? '<span class="badge badge-ok">فعال</span>' : '<span class="badge badge-danger">غیرفعال</span>'}</td>
      <td>${daysBadge(a)}</td>
      <td>${a.used_configs} / ${a.max_configs > 0 ? a.max_configs : '∞'}</td>
      <td class="small">${a.note || '—'}</td>
      <td>
        <div class="row">
          <button class="icon-btn" title="افزودن ۳۰ روز" onclick="addDays('${a.id}',30)"><i class="ti ti-calendar-plus"></i></button>
          <button class="icon-btn" title="تغییر سقف کانفیگ" onclick="editMax('${a.id}', ${a.max_configs})"><i class="ti ti-adjustments"></i></button>
          <button class="icon-btn" title="${a.active ? 'غیرفعال کردن' : 'فعال کردن'}" onclick="toggleActive('${a.id}', ${!a.active})"><i class="ti ti-power"></i></button>
          <button class="icon-btn" title="حذف" onclick="deleteAdmin('${a.id}','${a.email}')"><i class="ti ti-trash" style="color:var(--danger)"></i></button>
        </div>
      </td>
    </tr>
  `).join('');
}

async function loadLinks() {
  const links = await api('/api/links');
  const emailById = Object.fromEntries(ADMINS_CACHE.map(a => [a.id, a.email]));
  const body = document.getElementById('links-body');
  document.getElementById('links-empty').style.display = links.length ? 'none' : 'block';
  body.innerHTML = links.map(l => `
    <tr>
      <td>${l.label}</td>
      <td class="small">${l.protocol_label}</td>
      <td class="mono small">${emailById[l.owner_admin_id] || '—'}</td>
      <td class="small">${fmtBytes(l.used_bytes)}${l.limit_bytes ? ' / ' + fmtBytes(l.limit_bytes) : ''}</td>
      <td>${l.allowed ? '<span class="badge badge-ok">فعال</span>' : '<span class="badge badge-danger">غیرفعال/منقضی</span>'}</td>
    </tr>
  `).join('');
}

async function createAdmin() {
  const email = document.getElementById('na-email').value.trim();
  const password = document.getElementById('na-pass').value;
  const expire_days = document.getElementById('na-days').value;
  const max_configs = document.getElementById('na-max').value || 0;
  const note = document.getElementById('na-note').value;
  try {
    await api('/api/admins', {method:'POST', body: JSON.stringify({email, password, expire_days: expire_days || null, max_configs, note})});
    toast('ادمین ساخته شد', true);
    document.getElementById('na-email').value = '';
    document.getElementById('na-pass').value = '';
    document.getElementById('na-days').value = '';
    document.getElementById('na-max').value = '';
    document.getElementById('na-note').value = '';
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function addDays(id, days) {
  const input = prompt('چند روز اضافه شود؟', days);
  if (!input) return;
  try {
    await api('/api/admins/' + id, {method:'PATCH', body: JSON.stringify({add_days: parseInt(input)})});
    toast('اعتبار تمدید شد', true);
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function editMax(id, current) {
  const input = prompt('سقف تعداد کانفیگ (0 = نامحدود):', current);
  if (input === null) return;
  try {
    await api('/api/admins/' + id, {method:'PATCH', body: JSON.stringify({max_configs: parseInt(input || 0)})});
    toast('به‌روزرسانی شد', true);
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function toggleActive(id, next) {
  try {
    await api('/api/admins/' + id, {method:'PATCH', body: JSON.stringify({active: next})});
    toast(next ? 'ادمین فعال شد' : 'ادمین غیرفعال شد', true);
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function deleteAdmin(id, email) {
  if (!confirm('ادمین «' + email + '» و همه‌ی کانفیگ‌های او حذف شود؟')) return;
  try {
    await api('/api/admins/' + id, {method:'DELETE'});
    toast('ادمین حذف شد', true);
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function refreshAll() {
  await loadStats();
  await loadAdmins();
  await loadLinks();
}
refreshAll();
setInterval(refreshAll, 15000);
</script>
</body></html>"""


def render_admin_dashboard() -> str:
    topbar = TOPBAR_TEMPLATE.replace("__ROLE_LABEL__", "پنل ادمین / نماینده")
    return r"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>""" + HEAD + r"""<title>داشبورد ادمین · Dark Panel</title>
<style>""" + BASE_STYLE + r"""</style></head>
<body>
<div class="bg"></div><div class="grid"></div>
""" + topbar + r"""
<div class="container">

  <div class="cards" id="stat-cards"></div>

  <div class="panel">
    <h2><i class="ti ti-plus"></i> ساخت کانفیگ جدید</h2>
    <div class="grid-form">
      <div class="field"><label>برچسب / نام کاربر</label><input id="c-label" type="text" placeholder="مثلاً: مشتری ۱"></div>
      <div class="field"><label>نوع کانفیگ</label>
        <select id="c-protocol">
          <option value="vless-ws">VLESS · WebSocket</option>
          <option value="vless-xhttp-packet-up">VLESS · XHTTP (packet-up)</option>
          <option value="vless-xhttp-stream-up">VLESS · XHTTP (stream-up)</option>
          <option value="trojan-ws">Trojan · WebSocket</option>
        </select>
      </div>
      <div class="field"><label>حجم مجاز</label>
        <div class="row"><input id="c-limit-val" type="number" min="0" step="0.1" placeholder="0 = نامحدود" style="flex:2">
        <select id="c-limit-unit" style="flex:1"><option>GB</option><option>MB</option><option>KB</option></select></div>
      </div>
      <div class="field"><label>اعتبار (روز)</label><input id="c-days" type="number" min="0" placeholder="خالی = بدون انقضا"></div>
      <div class="field"><label>محدودیت سرعت (اختیاری)</label>
        <div class="row"><input id="c-speed-val" type="number" min="0" step="0.5" placeholder="0 = نامحدود" style="flex:2">
        <select id="c-speed-unit" style="flex:1"><option>MBIT</option><option>MB</option><option>KB</option></select></div>
      </div>
      <div class="field"><label>محدودیت تعداد آی‌پی (اختیاری)</label><input id="c-iplimit" type="number" min="0" placeholder="0 = نامحدود"></div>
      <div class="field"><label>پورت (اختیاری)</label><input id="c-port" type="number" min="1" max="65535" placeholder="443"></div>
      <div class="field"><label>Fingerprint (اختیاری)</label>
        <select id="c-fp"><option value="chrome">chrome</option><option value="firefox">firefox</option><option value="safari">safari</option><option value="ios">ios</option><option value="android">android</option><option value="random">random</option></select>
      </div>
      <div class="field"><label>ALPN (اختیاری)</label><input id="c-alpn" type="text" placeholder="مثلاً h2,http/1.1"></div>
    </div>
    <button class="btn btn-primary" onclick="createLink()"><i class="ti ti-server-bolt"></i> ساخت کانفیگ</button>
  </div>

  <div class="panel">
    <h2><i class="ti ti-list-details"></i> کانفیگ‌های من</h2>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>برچسب</th><th>نوع</th><th>مصرف</th><th>انقضا</th><th>وضعیت</th><th>عملیات</th></tr></thead>
        <tbody id="links-body"></tbody>
      </table>
      <div class="empty" id="links-empty" style="display:none">هنوز کانفیگی نساخته‌اید</div>
    </div>
  </div>

</div>

<div class="modal-bg" id="qr-box" onclick="if(event.target===this) closeModal('qr-box')">
  <div class="modal" style="text-align:center">
    <h3>QR Code</h3>
    <img id="qr-img" style="width:240px;height:240px;border-radius:12px;background:#fff;padding:8px">
    <div style="margin-top:14px"><button class="btn btn-ghost btn-sm" onclick="closeModal('qr-box')">بستن</button></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>""" + COMMON_JS + r"""

async function loadStats() {
  const s = await api('/stats');
  document.getElementById('stat-cards').innerHTML = `
    <div class="stat-card"><div class="label">کانفیگ‌های من</div><div class="value">${s.total_configs}</div></div>
    <div class="stat-card"><div class="label">اتصالات زنده</div><div class="value">${s.active_connections}</div></div>
    <div class="stat-card"><div class="label">حجم مصرفی کل</div><div class="value">${s.used_fmt}</div></div>
  `;
}

function expiryBadge(l) {
  if (!l.expires_at) return '<span class="badge badge-mid">بدون انقضا</span>';
  if (l.expired) return '<span class="badge badge-danger">منقضی</span>';
  return '<span class="badge badge-ok">دارد</span>';
}

async function loadLinks() {
  const links = await api('/api/links');
  const body = document.getElementById('links-body');
  document.getElementById('links-empty').style.display = links.length ? 'none' : 'block';
  body.innerHTML = links.map(l => `
    <tr>
      <td>${l.label}</td>
      <td class="small">${l.protocol_label}</td>
      <td class="small">${fmtBytes(l.used_bytes)}${l.limit_bytes ? ' / ' + fmtBytes(l.limit_bytes) : ' / ∞'}
        <div class="bar-bg"><div class="bar-fill" style="width:${l.limit_bytes ? Math.min(100, l.used_bytes/l.limit_bytes*100) : 4}%"></div></div>
      </td>
      <td>${expiryBadge(l)}</td>
      <td>${l.allowed ? '<span class="badge badge-ok">فعال</span>' : '<span class="badge badge-danger">غیرفعال</span>'}</td>
      <td>
        <div class="row">
          <button class="icon-btn" title="کپی لینک" onclick='copyText(${JSON.stringify(l.share_url)})'><i class="ti ti-copy"></i></button>
          <button class="icon-btn" title="QR" onclick='showQR(${JSON.stringify(l.share_url)})'><i class="ti ti-qrcode"></i></button>
          <button class="icon-btn" title="${l.active ? 'غیرفعال کردن' : 'فعال کردن'}" onclick="toggleLink('${l.id}', ${!l.active})"><i class="ti ti-power"></i></button>
          <button class="icon-btn" title="حذف" onclick="deleteLink('${l.id}')"><i class="ti ti-trash" style="color:var(--danger)"></i></button>
        </div>
      </td>
    </tr>
  `).join('');
}

async function createLink() {
  const body = {
    label: document.getElementById('c-label').value || 'کانفیگ جدید',
    protocol: document.getElementById('c-protocol').value,
    limit_value: document.getElementById('c-limit-val').value || 0,
    limit_unit: document.getElementById('c-limit-unit').value,
    expire_days: document.getElementById('c-days').value || null,
    speed_value: document.getElementById('c-speed-val').value || 0,
    speed_unit: document.getElementById('c-speed-unit').value,
    ip_limit: document.getElementById('c-iplimit').value || 0,
    port: document.getElementById('c-port').value || null,
    fingerprint: document.getElementById('c-fp').value,
    alpn: document.getElementById('c-alpn').value,
  };
  try {
    await api('/api/links', {method:'POST', body: JSON.stringify(body)});
    toast('کانفیگ ساخته شد', true);
    document.getElementById('c-label').value = '';
    document.getElementById('c-days').value = '';
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function toggleLink(id, next) {
  try {
    await api('/api/links/' + id, {method:'PATCH', body: JSON.stringify({active: next})});
    toast(next ? 'فعال شد' : 'غیرفعال شد', true);
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function deleteLink(id) {
  if (!confirm('این کانفیگ حذف شود؟')) return;
  try {
    await api('/api/links/' + id, {method:'DELETE'});
    toast('حذف شد', true);
    await refreshAll();
  } catch (e) { toast(e.message, false); }
}

async function refreshAll() {
  await loadStats();
  await loadLinks();
}
refreshAll();
setInterval(refreshAll, 15000);
</script>
</body></html>"""
