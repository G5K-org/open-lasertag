#!/usr/bin/env python3
"""Simulated weapons for testing the server without hardware.

Each weapon behaves like the firmware on the wire: HELLO, STATUS every
second, PING, reliable HIT/DEATH until ACK, and it follows GAME_START,
GAME_STOP, RESPAWN and SET_IDENTITY. Hits between simulated players are
random.

    python3 sim_weapon.py --count 6 --key change-me
"""
import argparse
import asyncio
import os
import random
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lasertag_server import protocol as p  # noqa: E402

RESEND_S = 0.25


class SimWeapon(asyncio.DatagramProtocol):
    def __init__(self, team, player, args, world):
        self.team, self.player = team, player
        self.args, self.world = args, world
        self.key = args.key.encode()
        self.session = struct.unpack("<I", os.urandom(4))[0]
        self.seq = 0
        self.server_session, self.server_seq = None, 0
        self.pending = {}  # seq -> [packet, last_send]
        self.running = True  # standalone default like the firmware
        self.max_hp, self.damage, self.magazine, self.respawn_s = 100, 10, 30, 10
        self.hp, self.ammo, self.alive, self.died_at = 100, 30, True, 0.0
        self.shots = self.hits_taken = 0
        self.rtt = self.rtt_max = 0
        self.bssid = bytes([0x02, 0, 0, 0, 0, random.randint(1, 3)])

    def connection_made(self, transport):
        self.transport = transport

    def packet(self, ptype, payload=b""):
        self.seq += 1
        return p.build(self.key, ptype, self.team, self.player, self.session, self.seq, payload)

    def send(self, ptype, payload=b""):
        self.transport.sendto(self.packet(ptype, payload))

    def send_reliable(self, ptype, payload):
        pkt = self.packet(ptype, payload)
        self.pending[self.seq] = [pkt, time.monotonic()]
        self.transport.sendto(pkt)
        self.transport.sendto(pkt)

    def datagram_received(self, data, addr):
        pkt = p.parse(self.key, data)
        if pkt is None or pkt.player not in (p.PLAYER_ALL, self.player):
            return
        if self.server_session == pkt.session and pkt.seq <= self.server_seq:
            return
        self.server_session, self.server_seq = pkt.session, pkt.seq
        if pkt.type == p.ACK:
            session, seq = p.ACK_FMT.unpack(pkt.payload)
            if session == self.session:
                self.pending.pop(seq, None)
        elif pkt.type == p.PONG:
            (t_us,) = p.PING_FMT.unpack(pkt.payload)
            self.rtt = int((time.monotonic_ns() // 1000 - t_us) / 1000)
            self.rtt_max = max(self.rtt_max, self.rtt)
        elif pkt.type == p.GAME_START:
            (self.max_hp, self.damage, self.magazine, _, _,
             self.respawn_s) = p.GAME_START_FMT.unpack(pkt.payload)
            self.running = True
            self.reset()
        elif pkt.type == p.GAME_STOP:
            self.running = False
        elif pkt.type == p.RESPAWN and self.running and not self.alive:
            self.reset()
        elif pkt.type == p.SET_IDENTITY:
            self.team, self.player = p.IDENTITY_FMT.unpack(pkt.payload)

    def reset(self):
        self.hp, self.ammo, self.alive = self.max_hp, self.magazine, True

    def take_hit(self, shooter):
        if not (self.running and self.alive):
            return
        self.hits_taken += 1
        self.hp = max(0, self.hp - self.damage)
        sensor = random.choice([1, 2, 3, 3, 4, 4, 5])
        self.send_reliable(p.HIT, p.HIT_FMT.pack(shooter.team, shooter.player, sensor, 0,
                                                 self.hp, int(time.monotonic() * 1000)))
        if self.hp == 0:
            self.alive, self.died_at = False, time.monotonic()
            self.send_reliable(p.DEATH, p.DEATH_FMT.pack(shooter.team, shooter.player,
                                                         int(time.monotonic() * 1000)))

    async def run(self):
        self.send(p.HELLO, b"sim-1.0".ljust(16, b"\0"))
        last_status = 0.0
        while True:
            await asyncio.sleep(0.1)
            now = time.monotonic()
            for entry in self.pending.values():
                if now - entry[1] >= RESEND_S:
                    entry[1] = now
                    self.transport.sendto(entry[0])
            if self.respawn_s and not self.alive and now - self.died_at >= self.respawn_s:
                self.reset()
            if now - last_status >= 1.0:
                last_status = now
                self.send(p.PING, p.PING_FMT.pack(time.monotonic_ns() // 1000))
                self.send(p.STATUS, p.STATUS_FMT.pack(
                    self.hp, self.ammo, 0, self.alive, self.running, 3900, 0,
                    random.randint(-75, -45), self.bssid, self.rtt, self.rtt_max,
                    self.shots, self.hits_taken, len(self.pending)))
                self.rtt_max = 0
            # random duel
            if self.running and self.alive and random.random() < self.args.rate / 10:
                enemies = [w for w in self.world if w.team != self.team and w.alive]
                if enemies:
                    self.shots += 1
                    self.ammo = self.ammo - 1 if self.ammo > 0 else self.magazine
                    if random.random() < 0.5:
                        random.choice(enemies).take_hit(self)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=4)
    ap.add_argument("--teams", type=int, default=2)
    ap.add_argument("--key", default="change-me")
    ap.add_argument("--server", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4210)
    ap.add_argument("--rate", type=float, default=0.5, help="shots per second per weapon")
    ap.add_argument("--first-id", type=int, default=1)
    a = ap.parse_args()
    loop = asyncio.get_running_loop()
    world = []
    for i in range(a.count):
        w = SimWeapon(i % a.teams, a.first_id + i, a, world)
        # each weapon on its own local port, like separate devices
        await loop.create_datagram_endpoint(lambda w=w: w, remote_addr=(a.server, a.port))
        world.append(w)
    print(f"{a.count} simulated weapons -> {a.server}:{a.port}")
    await asyncio.gather(*(w.run() for w in world))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
