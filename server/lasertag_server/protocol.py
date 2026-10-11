"""Wire format shared with the weapon firmware (firmware/main/proto.h).

header (16 bytes) | payload | HMAC-SHA256 truncated to 16 bytes
"""
import hashlib
import hmac
import struct
from dataclasses import dataclass

HDR = struct.Struct("<2sBBBBHII")
MAGIC = b"LT"
VERSION = 1
MAC_LEN = 16
MAX_PAYLOAD = 64
PLAYER_ALL = 0xFF

# weapon -> server
HELLO, STATUS, HIT, DEATH, PING = 0x01, 0x02, 0x03, 0x04, 0x05
# server -> weapon
ACK, PONG, GAME_START, GAME_STOP, RESPAWN, SET_IDENTITY = 0x81, 0x82, 0x83, 0x84, 0x85, 0x86

STATUS_FMT = struct.Struct("<HBBBBHBb6sHHIII")
HIT_FMT = struct.Struct("<BBBBHI")
DEATH_FMT = struct.Struct("<BBI")
PING_FMT = struct.Struct("<Q")
ACK_FMT = struct.Struct("<II")
GAME_START_FMT = struct.Struct("<HHBBBB")
IDENTITY_FMT = struct.Struct("<BB")

SENSOR_NAMES = {1: "Stirn vorn", 2: "Stirn hinten", 3: "Brust", 4: "Ruecken",
                5: "Schultern", 6: "Waffe"}
HEAD_SENSORS = {1, 2}


@dataclass
class Packet:
    type: int
    team: int
    player: int
    session: int
    seq: int
    payload: bytes


@dataclass
class Status:
    hp: int
    ammo: int
    magazines: int
    alive: bool
    running: bool
    battery_mv: int
    charging: bool
    rssi: int
    bssid: str
    rtt_ms: int
    rtt_max_ms: int
    shots: int
    hits_taken: int
    pending: int


@dataclass
class Hit:
    shooter_team: int
    shooter_player: int
    sensor: int
    hp_after: int
    time_ms: int


@dataclass
class Death:
    killer_team: int
    killer_player: int
    time_ms: int


def _mac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()[:MAC_LEN]


def build(key: bytes, ptype: int, team: int, player: int, session: int, seq: int,
          payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too long")
    body = HDR.pack(MAGIC, VERSION, ptype, team, player, len(payload), session, seq) + payload
    return body + _mac(key, body)


def parse(key: bytes, data: bytes) -> Packet | None:
    """Return the packet if format and MAC are valid, else None."""
    if len(data) < HDR.size + MAC_LEN:
        return None
    magic, ver, ptype, team, player, length, session, seq = HDR.unpack_from(data)
    if magic != MAGIC or ver != VERSION or length > MAX_PAYLOAD:
        return None
    if len(data) != HDR.size + length + MAC_LEN:
        return None
    if not hmac.compare_digest(_mac(key, data[:-MAC_LEN]), data[-MAC_LEN:]):
        return None
    return Packet(ptype, team, player, session, seq, data[HDR.size:HDR.size + length])


def parse_status(pl: bytes) -> Status | None:
    if len(pl) != STATUS_FMT.size:
        return None
    (hp, ammo, mags, alive, running, mv, chg, rssi, bssid, rtt, rtt_max, shots, hits,
     pending) = STATUS_FMT.unpack(pl)
    return Status(hp, ammo, mags, bool(alive), bool(running), mv, bool(chg), rssi,
                  bssid.hex(":"), rtt, rtt_max, shots, hits, pending)


def parse_hit(pl: bytes) -> Hit | None:
    if len(pl) != HIT_FMT.size:
        return None
    st, sp, sensor, _, hp, t = HIT_FMT.unpack(pl)
    return Hit(st, sp, sensor, hp, t)


def parse_death(pl: bytes) -> Death | None:
    if len(pl) != DEATH_FMT.size:
        return None
    return Death(*DEATH_FMT.unpack(pl))


def parse_hello(pl: bytes) -> str:
    return pl.rstrip(b"\0").decode(errors="replace")


def game_start_payload(max_hp: int, damage: int, magazine: int, magazines: int,
                       friendly_fire: bool, respawn_s: int) -> bytes:
    return GAME_START_FMT.pack(max_hp, damage, magazine, magazines, int(friendly_fire),
                               respawn_s)
