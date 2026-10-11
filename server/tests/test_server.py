"""python3 -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lasertag_server import protocol as p  # noqa: E402
from lasertag_server.game import Game, Rules  # noqa: E402

KEY = b"secret"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def pkt(ptype, player, team, seq, payload=b"", session=1):
    return p.parse(KEY, p.build(KEY, ptype, team, player, session, seq, payload))


def status(alive=True, running=True, hp=100):
    return p.STATUS_FMT.pack(hp, 30, 0, alive, running, 3900, 0, -60, b"\x02\0\0\0\0\1",
                             5, 9, 0, 0, 0)


class ProtocolTest(unittest.TestCase):
    def test_roundtrip(self):
        raw = p.build(KEY, p.HIT, 1, 7, 42, 3, b"abc")
        self.assertEqual(len(raw), 16 + 3 + 16)
        got = p.parse(KEY, raw)
        self.assertEqual((got.type, got.team, got.player, got.session, got.seq, got.payload),
                         (p.HIT, 1, 7, 42, 3, b"abc"))

    def test_rejects_tampering_and_wrong_key(self):
        raw = bytearray(p.build(KEY, p.HIT, 1, 7, 42, 3, b"abc"))
        self.assertIsNone(p.parse(b"other", bytes(raw)))
        raw[17] ^= 1
        self.assertIsNone(p.parse(KEY, bytes(raw)))
        self.assertIsNone(p.parse(KEY, bytes(raw[:20])))

    def test_sizes_match_firmware(self):
        # firmware/main/proto.h static asserts
        self.assertEqual((p.HDR.size, p.STATUS_FMT.size, p.HIT_FMT.size, p.DEATH_FMT.size,
                          p.PING_FMT.size, p.ACK_FMT.size, p.GAME_START_FMT.size,
                          p.IDENTITY_FMT.size), (16, 32, 10, 6, 8, 8, 8, 2))

    def test_known_vector(self):
        # header layout check against the C struct order
        raw = p.build(KEY, p.PING, 2, 5, 0x01020304, 0x0A0B0C0D, b"")
        # magic, version, type, team, player, len, session, seq (little endian)
        self.assertEqual(raw[:16].hex(), "4c540105" "0205" "0000" "04030201" "0d0c0b0a")


class GameTest(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.clock = Clock()
        self.g = Game(lambda t, pl, data: self.sent.append((t, pl, data)), clock=self.clock)
        self.addr = ("10.0.0.2", 4211)
        self.seq = 0
        for pid, team in ((1, 0), (2, 1), (3, 0)):
            self.feed(p.HELLO, pid, team, b"fw".ljust(16, b"\0"))
            self.feed(p.STATUS, pid, team, status())
        self.g.start_round(Rules(respawn_s=10, duration_s=60))
        self.sent.clear()

    def feed(self, ptype, player, team, payload=b"", seq=None):
        if seq is None:
            self.seq += 1
            seq = self.seq
        self.g.handle(pkt(ptype, player, team, seq, payload), self.addr)
        return seq

    def hit(self, victim, vteam, shooter, steam, sensor=3, hp=90):
        return self.feed(p.HIT, victim, vteam, p.HIT_FMT.pack(steam, shooter, sensor, 0, hp, 0))

    def death(self, victim, vteam, killer, kteam):
        return self.feed(p.DEATH, victim, vteam, p.DEATH_FMT.pack(kteam, killer, 0))

    def types(self):
        return [t for t, _, _ in self.sent]

    def test_hit_scores_and_dedup(self):
        seq = self.hit(2, 1, 1, 0, sensor=1)
        self.feed(p.HIT, 2, 1, p.HIT_FMT.pack(0, 1, 1, 0, 90, 0), seq=seq)  # second copy
        self.assertEqual(self.types(), [p.ACK, p.ACK])  # every copy acked
        self.assertEqual(self.g.players[1].score, 15)  # hit + head bonus
        self.assertEqual(self.g.players[1].hits_given, 1)
        self.assertEqual(self.g.players[2].hits_taken, 1)

    def test_kill_respawn_release(self):
        self.death(2, 1, 1, 0)
        self.assertFalse(self.g.players[2].alive)
        self.assertEqual(self.g.players[1].kills, 1)
        self.assertEqual(self.g.team_scores()[0], 100)
        self.clock.t += 5
        self.sent.clear()
        self.g.tick()
        self.assertNotIn(p.RESPAWN, self.types())
        self.clock.t += 5
        for pid, team in ((1, 0), (2, 1), (3, 0)):  # keep everyone online
            self.feed(p.STATUS, pid, team, status(alive=pid != 2))
        self.g.tick()
        self.assertIn((p.RESPAWN, 2, b""), self.sent)
        self.assertTrue(self.g.players[2].alive)

    def test_lost_respawn_is_repeated(self):
        self.death(2, 1, 1, 0)
        self.clock.t += 10
        self.g.tick()  # release
        self.clock.t += 1
        self.feed(p.STATUS, 2, 1, status(alive=False))  # weapon missed it
        self.sent.clear()
        self.g.tick()
        self.assertIn((p.RESPAWN, 2, b""), self.sent)
        self.assertTrue(self.g.players[2].alive)

    def test_death_seen_in_status_before_death_packet(self):
        self.clock.t += 10
        self.feed(p.STATUS, 2, 1, status(alive=False, hp=0))
        self.g.tick()
        self.assertFalse(self.g.players[2].alive)
        self.death(2, 1, 1, 0)  # arrives late, still credited once
        self.death(2, 1, 1, 0)
        self.assertEqual(self.g.players[1].kills, 1)
        self.assertEqual(self.g.players[2].deaths, 1)

    def test_team_kill(self):
        self.death(3, 0, 1, 0)
        self.assertEqual(self.g.players[1].team_kills, 1)
        self.assertEqual(self.g.players[1].score, -100)

    def test_round_timer_and_winner(self):
        self.death(2, 1, 1, 0)
        self.clock.t += 61
        self.g.tick()
        self.assertFalse(self.g.running)
        self.assertEqual(self.g.winner, 0)
        self.assertIn((p.GAME_STOP, p.PLAYER_ALL, b""), self.sent)

    def test_no_scoring_outside_round(self):
        self.g.stop_round()
        self.death(2, 1, 1, 0)
        self.assertEqual(self.g.players[1].kills, 0)

    def test_weapon_state_reconciled(self):
        self.feed(p.STATUS, 2, 1, status(running=False))
        self.sent.clear()
        self.g.tick()
        self.assertIn(p.GAME_START, [t for t, pl, _ in self.sent if pl == 2])
        start = next(d for t, pl, d in self.sent if t == p.GAME_START)
        self.assertEqual(p.GAME_START_FMT.unpack(start)[5], 0)  # respawn by server

    def test_set_identity(self):
        self.g.set_identity(2, 0, 9)
        self.assertEqual(self.sent[-1], (p.SET_IDENTITY, 2, bytes([0, 9])))
        self.assertIn(9, self.g.players)
        self.assertNotIn(2, self.g.players)

    def test_snapshot_is_json(self):
        import json
        self.hit(2, 1, 1, 0)
        json.dumps(self.g.snapshot())


if __name__ == "__main__":
    unittest.main()
