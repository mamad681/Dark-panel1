# relay_trojan.py
# پیاده‌سازی پروتکل Trojan روی WebSocket (سازگار با Xray-core / v2rayNG / Hiddify و...)
#
# فرمت هدر Trojan داخل اولین پیام:
#   hex(SHA224(password))[56 بایت] + CRLF + Trojan-Request + CRLF + Payload
#   Trojan-Request = CMD(1B, 0x01=connect) + ATYP(1B) + DST.ADDR + DST.PORT(2B, big-endian)
#   ATYP: 0x01=IPv4(4B) | 0x03=Domain(1B len + بایت‌ها) | 0x04=IPv6(16B)

import asyncio
import secrets
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from main import (
    LINKS,
    LINKS_LOCK,
    stats,
    hourly_traffic,
    connections,
    error_logs,
    logger,
    is_link_allowed,
    is_ip_allowed,
    save_state,
    log_activity,
    now_ir,
)
from speed_limit import throttle

RELAY_BUF = 256 * 1024


def _ws_client_ip(ws: WebSocket) -> str:
    fwd = ws.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    real_ip = ws.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return ws.client.host if ws.client else "نامشخص"


def parse_trojan_header(chunk: bytes):
    """هدر Trojan را پارس می‌کند و (auth_hex, address, port, remaining_payload) برمی‌گرداند."""
    if len(chunk) < 56 + 2 + 4:
        raise ValueError("chunk too small for trojan header")
    auth_hex = chunk[:56].decode("ascii", errors="ignore").lower()
    pos = 56
    if chunk[pos:pos + 2] != b"\r\n":
        raise ValueError("malformed trojan header (missing CRLF after auth)")
    pos += 2

    cmd = chunk[pos]; pos += 1  # noqa: F841 (فقط CONNECT پشتیبانی می‌شود)
    atyp = chunk[pos]; pos += 1
    if atyp == 0x01:
        address = ".".join(str(b) for b in chunk[pos:pos + 4]); pos += 4
    elif atyp == 0x03:
        dlen = chunk[pos]; pos += 1
        address = chunk[pos:pos + dlen].decode("utf-8", errors="ignore"); pos += dlen
    elif atyp == 0x04:
        ab = chunk[pos:pos + 16]; pos += 16
        address = ":".join(f"{ab[i]:02x}{ab[i+1]:02x}" for i in range(0, 16, 2))
    else:
        raise ValueError(f"unknown trojan ATYP: {atyp}")

    port = int.from_bytes(chunk[pos:pos + 2], "big"); pos += 2
    if chunk[pos:pos + 2] == b"\r\n":
        pos += 2
    return auth_hex, address, port, chunk[pos:]


async def check_and_use(cid: str, n: int) -> bool:
    async with LINKS_LOCK:
        link = LINKS.get(cid)
        if link is None:
            return False
        if not is_link_allowed(link):
            return False
        link["used_bytes"] += n
        stats["total_bytes"] += n
        hourly_traffic[now_ir().strftime("%H:00")] += n
    return True


async def relay_ws_to_tcp(ws: WebSocket, writer: asyncio.StreamWriter, conn_id: str, cid: str):
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            data = msg.get("bytes") or (msg.get("text") or "").encode()
            if not data:
                continue
            if not await check_and_use(cid, len(data)):
                await ws.close(code=1008, reason="quota/disabled/unknown")
                break
            await throttle(cid, len(data))
            stats["total_requests"] += 1
            connections[conn_id]["bytes"] += len(data)
            writer.write(data)
            if writer.transport.get_write_buffer_size() > RELAY_BUF:
                await writer.drain()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        try:
            writer.write_eof()
        except Exception:
            pass


async def relay_tcp_to_ws(ws: WebSocket, reader: asyncio.StreamReader, conn_id: str, cid: str):
    try:
        while True:
            data = await reader.read(RELAY_BUF)
            if not data:
                break
            if not await check_and_use(cid, len(data)):
                await ws.close(code=1008, reason="quota/disabled/unknown")
                break
            await throttle(cid, len(data))
            connections[conn_id]["bytes"] += len(data)
            await ws.send_bytes(data)
    except Exception:
        pass


async def trojan_websocket_tunnel(ws: WebSocket, config_id: str):
    await ws.accept()

    async with LINKS_LOCK:
        link = LINKS.get(config_id)

    if not is_link_allowed(link) or link.get("protocol") != "trojan-ws":
        logger.warning(f"🚫 Trojan-WS rejected cid={config_id[:8]}… (not allowed)")
        await ws.close(code=1008, reason="not authorized")
        return

    ip = _ws_client_ip(ws)
    if not is_ip_allowed(link, config_id, ip):
        logger.warning(f"🚫 Trojan-WS rejected cid={config_id[:8]}… ip={ip} (ip limit reached)")
        log_activity("connection", f"اتصال {ip} به کانفیگ «{link.get('label','?')}» رد شد (محدودیت آی‌پی)", "warn")
        await ws.close(code=1008, reason="ip limit reached")
        return

    conn_id = secrets.token_urlsafe(6)
    connections[conn_id] = {
        "uuid": config_id,
        "ip": ip,
        "transport": "trojan-ws",
        "connected_at": datetime.now().isoformat(),
        "bytes": 0,
    }
    logger.info(f"✅ Trojan-WS [{conn_id}] cid={config_id[:8]}… ip={ip} total={len(connections)}")
    log_activity("connection", f"اتصال جدید از {ip} (کانفیگ {link.get('label','?')})", "info")
    writer = None

    try:
        first_msg = await asyncio.wait_for(ws.receive(), timeout=15.0)
        if first_msg["type"] == "websocket.disconnect":
            return
        first_chunk = first_msg.get("bytes") or (first_msg.get("text") or "").encode()
        if not first_chunk:
            return

        auth_hex, address, port, payload = parse_trojan_header(first_chunk)

        expected_hash = link.get("auth_hash")
        if not expected_hash or auth_hex != expected_hash:
            logger.warning(f"🚫 Trojan-WS auth mismatch cid={config_id[:8]}…")
            await ws.close(code=1008, reason="invalid password")
            return

        if not await check_and_use(config_id, len(first_chunk)):
            await ws.close(code=1008, reason="quota/disabled")
            return

        stats["total_requests"] += 1
        connections[conn_id]["bytes"] += len(first_chunk)
        logger.info(f"➡️  [{conn_id}] → {address}:{port}")

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port), timeout=10.0
        )
        sock = writer.transport.get_extra_info("socket")
        if sock:
            import socket
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if payload:
            writer.write(payload)
            await writer.drain()

        done, pending = await asyncio.wait(
            {
                asyncio.create_task(relay_ws_to_tcp(ws, writer, conn_id, config_id)),
                asyncio.create_task(relay_tcp_to_ws(ws, reader, conn_id, config_id)),
            },
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

        asyncio.create_task(save_state())

    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        stats["total_errors"] += 1
        error_logs.append({"error": "connection timeout", "time": datetime.now().isoformat()})
    except Exception as exc:
        stats["total_errors"] += 1
        error_logs.append({"error": str(exc), "time": datetime.now().isoformat()})
        logger.error(f"Trojan-WS error [{conn_id}]: {exc}")
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        connections.pop(conn_id, None)
        logger.info(f"🔌 Trojan-WS closed [{conn_id}] total={len(connections)}")
