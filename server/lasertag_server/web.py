"""Minimal HTTP + WebSocket server (stdlib only) for the live scoreboard.

GET /       -> static/index.html
GET /ws     -> WebSocket: server pushes the game snapshot as JSON,
               client sends commands {"cmd": ..., ...}
"""
import asyncio
import base64
import hashlib
import json
import logging
import struct
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

log = logging.getLogger("web")
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
STATIC = Path(__file__).parent / "static"
MAX_FRAME = 64 * 1024


class WebSocket:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def send_text(self, text: str):
        data = text.encode()
        n = len(data)
        if n < 126:
            hdr = struct.pack("!BB", 0x81, n)
        elif n < 65536:
            hdr = struct.pack("!BBH", 0x81, 126, n)
        else:
            hdr = struct.pack("!BBQ", 0x81, 127, n)
        self.writer.write(hdr + data)
        await self.writer.drain()

    async def recv_text(self) -> str | None:
        """Next text message, None when the connection closes."""
        while True:
            b0, b1 = await self.reader.readexactly(2)
            opcode, masked, n = b0 & 0x0F, b1 & 0x80, b1 & 0x7F
            if n == 126:
                n = struct.unpack("!H", await self.reader.readexactly(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", await self.reader.readexactly(8))[0]
            if n > MAX_FRAME or not masked:
                return None  # clients must mask
            mask = await self.reader.readexactly(4)
            data = bytes(c ^ mask[i % 4] for i, c in enumerate(await self.reader.readexactly(n)))
            if opcode == 0x8:
                return None
            if opcode == 0x9:  # ping
                self.writer.write(struct.pack("!BB", 0x8A, len(data)) + data)
                await self.writer.drain()
            elif opcode == 0x1:
                return data.decode(errors="replace")


class WebServer:
    def __init__(self, game, admin_token: str | None, on_command):
        self.game = game
        self.admin_token = admin_token
        self.on_command = on_command
        self.clients: set[WebSocket] = set()

    async def handle(self, reader, writer):
        try:
            request = await reader.readuntil(b"\r\n\r\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
            writer.close()
            return
        lines = request.decode(errors="replace").split("\r\n")
        try:
            method, target, _ = lines[0].split(" ", 2)
        except ValueError:
            writer.close()
            return
        headers = {k.strip().lower(): v.strip()
                   for k, _, v in (ln.partition(":") for ln in lines[1:] if ln)}
        url = urlsplit(target)
        try:
            if url.path == "/ws" and headers.get("upgrade", "").lower() == "websocket":
                token = parse_qs(url.query).get("token", [None])[0]
                await self.websocket(reader, writer, headers, token)
            elif method == "GET" and url.path in ("/", "/index.html"):
                self.respond(writer, 200, "text/html; charset=utf-8",
                             (STATIC / "index.html").read_bytes())
            else:
                self.respond(writer, 404, "text/plain", b"not found")
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()

    @staticmethod
    def respond(writer, code: int, ctype: str, body: bytes):
        reason = {200: "OK", 404: "Not Found"}[code]
        writer.write(f"HTTP/1.1 {code} {reason}\r\nContent-Type: {ctype}\r\n"
                     f"Content-Length: {len(body)}\r\nCache-Control: no-store\r\n"
                     f"Connection: close\r\n\r\n".encode() + body)

    async def websocket(self, reader, writer, headers, token):
        key = headers.get("sec-websocket-key", "")
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                      f"Connection: Upgrade\r\nSec-WebSocket-Accept: {accept}\r\n\r\n").encode())
        await writer.drain()
        ws = WebSocket(reader, writer)
        admin = self.admin_token is None or token == self.admin_token
        self.clients.add(ws)
        try:
            await ws.send_text(json.dumps({"type": "hello", "admin": admin}))
            await ws.send_text(json.dumps({"type": "state", **self.game.snapshot()}))
            while (msg := await ws.recv_text()) is not None:
                if not admin:
                    continue  # read-only viewer
                try:
                    self.on_command(json.loads(msg))
                except (ValueError, KeyError, TypeError) as e:
                    log.warning("bad command %r: %s", msg, e)
                await self.broadcast()
        finally:
            self.clients.discard(ws)

    async def broadcast(self):
        if not self.clients:
            return
        text = json.dumps({"type": "state", **self.game.snapshot()})
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
            except (ConnectionError, RuntimeError):
                self.clients.discard(ws)
