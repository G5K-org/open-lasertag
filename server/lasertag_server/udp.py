"""UDP endpoint to the weapons."""
import asyncio
import logging
import os
import struct

from . import protocol as p

log = logging.getLogger("udp")


class WeaponProtocol(asyncio.DatagramProtocol):
    def __init__(self, key: bytes):
        self.key = key
        self.session = struct.unpack("<I", os.urandom(4))[0]
        self.seq = 0
        self.game = None  # set after construction
        self.transport = None
        self.bad_mac = 0

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        pkt = p.parse(self.key, data)
        if pkt is None:
            self.bad_mac += 1
            log.debug("invalid packet from %s", addr[0])
            return
        self.game.handle(pkt, addr)

    def send(self, ptype: int, player: int, payload: bytes):
        """Send to one player or, with PLAYER_ALL, to every known weapon.
        Replies go to the source address of the weapon's last packet
        (the firmware sends from its bound port LT_LOCAL_PORT)."""
        if self.transport is None:
            return
        self.seq += 1
        pkt = p.build(self.key, ptype, 0, player, self.session, self.seq, payload)
        if player == p.PLAYER_ALL:
            targets = [pl.addr for pl in self.game.players.values() if pl.addr]
        else:
            pl = self.game.players.get(player)
            targets = [pl.addr] if pl and pl.addr else []
        for addr in targets:
            self.transport.sendto(pkt, addr)
