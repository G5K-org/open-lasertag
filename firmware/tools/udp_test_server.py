#!/usr/bin/env python3
"""Minimal UDP test server for the weapon firmware (protocol in main/proto.h).

Prints every packet, acks HIT/DEATH, answers PING with PONG. Commands on
stdin:  start [hp dmg mag mags ff respawn_s] | stop | respawn [player] |
        id <player> <team> <new_player>

    python3 udp_test_server.py --key change-me
"""
import argparse
import asyncio
import hashlib
import hmac
import os
import struct
import sys

HDR = struct.Struct("<2sBBBBHII")
MAC_LEN = 16
ALL = 0xFF

HELLO, STATUS, HIT, DEATH, PING = 0x01, 0x02, 0x03, 0x04, 0x05
ACK, PONG, GAME_START, GAME_STOP, RESPAWN, SET_IDENTITY = 0x81, 0x82, 0x83, 0x84, 0x85, 0x86

STATUS_FMT = struct.Struct("<HBBBBHBb6sHHIII")
HIT_FMT = struct.Struct("<BBBBHI")
DEATH_FMT = struct.Struct("<BBI")
SENSORS = {1: "Stirn vorn", 2: "Stirn hinten", 3: "Brust", 4: "Ruecken", 5: "Schultern", 6: "Waffe"}


class Server(asyncio.DatagramProtocol):
    def __init__(self, key, weapon_port):
        self.key = key
        self.weapon_port = weapon_port
        self.session = struct.unpack("<I", os.urandom(4))[0]
        self.seq = 0
        self.weapons = {}  # player -> (ip, port)
        self.seen = set()  # (player, session, seq) for dedup

    def connection_made(self, transport):
        self.transport = transport

    def build(self, ptype, player, payload=b""):
        self.seq += 1
        hdr = HDR.pack(b"LT", 1, ptype, 0, player, len(payload), self.session, self.seq)
        mac = hmac.new(self.key, hdr + payload, hashlib.sha256).digest()[:MAC_LEN]
        return hdr + payload + mac

    def send(self, ptype, player, payload=b"", addr=None):
        pkt = self.build(ptype, player, payload)
        targets = [addr] if addr else (
            list(self.weapons.values()) if player == ALL else [self.weapons.get(player)])
        for t in filter(None, targets):
            self.transport.sendto(pkt, (t[0], self.weapon_port))

    def datagram_received(self, data, addr):
        if len(data) < HDR.size + MAC_LEN:
            return
        magic, ver, ptype, team, player, length, session, seq = HDR.unpack_from(data)
        body, mac = data[:-MAC_LEN], data[-MAC_LEN:]
        if magic != b"LT" or ver != 1 or len(data) != HDR.size + length + MAC_LEN:
            return
        if not hmac.compare_digest(hmac.new(self.key, body, hashlib.sha256).digest()[:MAC_LEN], mac):
            print(f"{addr[0]}: bad MAC")
            return
        self.weapons[player] = addr
        pl = data[HDR.size:HDR.size + length]
        if ptype in (HIT, DEATH):
            self.send(ACK, player, struct.pack("<II", session, seq), addr)
        key = (player, session, seq)
        if key in self.seen:
            return
        self.seen.add(key)
        who = f"T{team}/P{player}"
        if ptype == PING:
            self.send(PONG, player, pl, addr)
        elif ptype == HELLO:
            print(f"{who} HELLO fw {pl.rstrip(b'\0').decode(errors='replace')} from {addr[0]}")
        elif ptype == STATUS:
            (hp, ammo, mags, alive, running, mv, chg, rssi, bssid, rtt, rtt_max, shots, hits,
             pending) = STATUS_FMT.unpack(pl)
            print(f"{who} HP {hp} ammo {ammo} {'alive' if alive else 'DEAD'}"
                  f"{'' if running else ' (stopped)'} bat {mv} mV{' chg' if chg else ''}"
                  f" rssi {rssi} AP {bssid.hex(':')} rtt {rtt}/{rtt_max} ms shots {shots}"
                  f" hits {hits} pending {pending}")
        elif ptype == HIT:
            st, sp, sensor, _, hp, t = HIT_FMT.unpack(pl)
            print(f"{who} HIT by T{st}/P{sp} at {SENSORS.get(sensor, sensor)}, HP {hp}")
        elif ptype == DEATH:
            kt, kp, t = DEATH_FMT.unpack(pl)
            print(f"{who} DEATH by T{kt}/P{kp}")


async def stdin_commands(server):
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    while line := (await reader.readline()).decode().split():
        cmd, args = line[0], [int(a) for a in line[1:]]
        if cmd == "start":
            hp, dmg, mag, mags, ff, resp = (args + [100, 10, 30, 0, 0, 10][len(args):])[:6]
            server.send(GAME_START, ALL, struct.pack("<HHBBBB", hp, dmg, mag, mags, ff, resp))
        elif cmd == "stop":
            server.send(GAME_STOP, ALL)
        elif cmd == "respawn":
            server.send(RESPAWN, args[0] if args else ALL)
        elif cmd == "id" and len(args) == 3:
            server.send(SET_IDENTITY, args[0], struct.pack("<BB", args[1], args[2]))
        else:
            print("start [hp dmg mag mags ff respawn_s] | stop | respawn [player] | id <player> <team> <new>")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="change-me")
    ap.add_argument("--port", type=int, default=4210)
    ap.add_argument("--weapon-port", type=int, default=4211)
    a = ap.parse_args()
    loop = asyncio.get_running_loop()
    _, server = await loop.create_datagram_endpoint(
        lambda: Server(a.key.encode(), a.weapon_port), local_addr=("0.0.0.0", a.port))
    print(f"listening on UDP {a.port}")
    await stdin_commands(server)


if __name__ == "__main__":
    asyncio.run(main())
