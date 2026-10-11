"""ESP-NOW gateway (gateway/ firmware) on a USB serial port.

Line protocol, hex encoded:
    gateway -> server   LT:<sender mac>:<packet>
    server -> gateway   LT:<target mac | ffffffffffff>:<packet>
Other lines are log output of the gateway.

Stdlib only (termios), so Linux and macOS.
"""
import asyncio
import logging
import os
import termios
import tty

log = logging.getLogger("gateway")
BROADCAST = "ffffffffffff"
RETRY_S = 2.0


class SerialGateway:
    def __init__(self, port: str, on_packet):
        self.port = port
        self.on_packet = on_packet  # (data: bytes, mac: str)
        self.fd = None
        self.buf = b""
        self.loop = None

    async def run(self):
        """Keep the port open; reopen after the gateway was unplugged/reset."""
        self.loop = asyncio.get_running_loop()
        while True:
            if self.fd is None:
                try:
                    self._open()
                    log.info("gateway on %s", self.port)
                except OSError as e:
                    log.debug("gateway %s: %s", self.port, e)
            await asyncio.sleep(RETRY_S)

    @property
    def connected(self) -> bool:
        return self.fd is not None

    def _open(self):
        fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            tty.setraw(fd)
            attrs = termios.tcgetattr(fd)
            attrs[2] &= ~termios.HUPCL  # no DTR/RTS toggle on close (would reset the chip)
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except termios.error:
            os.close(fd)
            raise
        self.fd = fd
        self.buf = b""
        self.loop.add_reader(fd, self._readable)

    def _close(self):
        if self.fd is not None:
            self.loop.remove_reader(self.fd)
            os.close(self.fd)
            self.fd = None
            log.warning("gateway %s lost", self.port)

    def _readable(self):
        try:
            chunk = os.read(self.fd, 4096)
        except BlockingIOError:
            return
        except OSError:
            chunk = b""
        if not chunk:
            self._close()
            return
        self.buf += chunk
        *lines, self.buf = self.buf.split(b"\n")
        if len(self.buf) > 4096:
            self.buf = b""
        for raw in lines:
            line = raw.strip().decode(errors="replace")
            if line.startswith("LT:"):
                parts = line.split(":")
                if len(parts) == 3 and len(parts[1]) == 12:
                    try:
                        self.on_packet(bytes.fromhex(parts[2]), parts[1].lower())
                    except ValueError:
                        pass
            elif line:
                log.info("gw: %s", line)

    def send(self, mac: str, data: bytes):
        if self.fd is None:
            return
        try:
            os.write(self.fd, f"LT:{mac}:{data.hex()}\n".encode())
        except OSError:
            self._close()
