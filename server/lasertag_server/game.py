"""Game state: players, teams, rounds, scoring and respawn release.

Pure logic without network I/O. Outgoing commands go through the `send`
callback, time comes from `clock`, so tests can drive it directly.
"""
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Callable

from . import protocol as p

ONLINE_TIMEOUT_S = 3.0
# a dead status this soon after RESPAWN means the command got lost
RESPAWN_CONFIRM_S = 5.0
SEEN_PER_PLAYER = 512
FEED_LEN = 50


@dataclass
class Rules:
    max_hp: int = 100
    damage: int = 10
    magazine: int = 30
    magazines: int = 0          # 0 = unlimited
    friendly_fire: bool = False
    respawn_s: int = 10         # released by the server
    duration_s: int = 600       # 0 = until stopped
    points_hit: int = 10
    points_head_bonus: int = 5  # extra for headband sensors
    points_kill: int = 100
    points_team_kill: int = -100


@dataclass
class Player:
    id: int
    team: int
    name: str = ""
    firmware: str = ""
    addr: tuple | None = None
    last_seen: float = 0.0
    status: p.Status | None = None
    status_at: float = 0.0
    alive: bool = True
    died_at: float = 0.0
    released_at: float = 0.0
    death_credited: bool = False
    killed_by: int | None = None
    kills: int = 0
    deaths: int = 0
    hits_given: int = 0
    hits_taken: int = 0
    team_kills: int = 0
    score: int = 0

    def reset_round(self, now: float):
        self.alive = True
        self.died_at = 0.0
        self.released_at = now
        self.death_credited = False
        self.killed_by = None
        self.kills = self.deaths = self.hits_given = self.hits_taken = 0
        self.team_kills = self.score = 0


@dataclass
class ZoneStats:
    """RTT samples per access point (BSSID = hall zone)."""
    samples: deque = field(default_factory=lambda: deque(maxlen=2000))
    max_ms: int = 0
    rssi_sum: int = 0
    rssi_n: int = 0

    def add(self, rtt: int, rtt_max: int, rssi: int):
        self.samples.append(rtt)
        self.max_ms = max(self.max_ms, rtt_max, rtt)
        self.rssi_sum += rssi
        self.rssi_n += 1

    def summary(self) -> dict:
        s = sorted(self.samples)
        n = len(s)
        return {
            "n": n,
            "avg_ms": round(sum(s) / n, 1) if n else None,
            "p95_ms": s[min(n - 1, int(n * 0.95))] if n else None,
            "max_ms": self.max_ms,
            "rssi_avg": round(self.rssi_sum / self.rssi_n) if self.rssi_n else None,
        }


class Game:
    def __init__(self, send: Callable[[int, int, bytes], None],
                 teams: dict[int, dict] | None = None, names: dict[int, str] | None = None,
                 control_weapons: bool = True, clock: Callable[[], float] = time.monotonic,
                 log: Callable[[dict], None] | None = None,
                 rtt_log: Callable[[Player, p.Status], None] | None = None):
        self.send = send  # (ptype, player id or PLAYER_ALL, payload)
        self.clock = clock
        self.log = log or (lambda ev: None)
        self.rtt_log = rtt_log or (lambda pl, st: None)
        self.teams = teams or {0: {"name": "Rot", "color": "#e53935"},
                               1: {"name": "Blau", "color": "#1e88e5"}}
        self.names = names or {}
        self.control_weapons = control_weapons
        self.rules = Rules()
        self.players: dict[int, Player] = {}
        self.running = False
        self.round_no = 0
        self.round_started = 0.0
        self.round_ended = 0.0
        self.winner: int | None = None
        self.feed: deque = deque(maxlen=FEED_LEN)
        self.zones: dict[str, ZoneStats] = {}
        self._seen: dict[int, deque] = {}
        self._seen_set: dict[int, set] = {}

    # ---- packets from weapons -------------------------------------------

    def is_duplicate(self, pkt: p.Packet) -> bool:
        """Dedup on (player, session, seq); hits arrive at least twice."""
        key = (pkt.session, pkt.seq)
        seen = self._seen_set.setdefault(pkt.player, set())
        if key in seen:
            return True
        order = self._seen.setdefault(pkt.player, deque())
        order.append(key)
        seen.add(key)
        if len(order) > SEEN_PER_PLAYER:
            seen.discard(order.popleft())
        return False

    def player(self, pkt: p.Packet, addr) -> Player:
        pl = self.players.get(pkt.player)
        if pl is None:
            pl = Player(pkt.player, pkt.team, self.names.get(pkt.player, f"Spieler {pkt.player}"))
            self.players[pkt.player] = pl
            self.log({"ev": "join", "player": pkt.player, "team": pkt.team})
        pl.team = pkt.team
        pl.addr = addr
        pl.last_seen = self.clock()
        return pl

    def handle(self, pkt: p.Packet, addr) -> None:
        if pkt.type in (p.HIT, p.DEATH):
            # ack every copy, the weapon resends until it gets one
            self.send(p.ACK, pkt.player, p.ACK_FMT.pack(pkt.session, pkt.seq))
        if self.is_duplicate(pkt):
            return
        pl = self.player(pkt, addr)
        if pkt.type == p.PING:
            self.send(p.PONG, pkt.player, pkt.payload)
        elif pkt.type == p.HELLO:
            pl.firmware = p.parse_hello(pkt.payload)
            self.log({"ev": "hello", "player": pl.id, "fw": pl.firmware, "ip": addr[0]})
        elif pkt.type == p.STATUS:
            st = p.parse_status(pkt.payload)
            if st:
                pl.status = st
                pl.status_at = self.clock()
                if st.rtt_ms or st.rtt_max_ms:
                    self.rtt_log(pl, st)
                    self.zones.setdefault(st.bssid, ZoneStats()).add(st.rtt_ms, st.rtt_max_ms,
                                                                     st.rssi)
        elif pkt.type == p.HIT:
            hit = p.parse_hit(pkt.payload)
            if hit:
                self.on_hit(pl, hit)
        elif pkt.type == p.DEATH:
            death = p.parse_death(pkt.payload)
            if death:
                self.on_death(pl, death)

    def on_hit(self, victim: Player, hit: p.Hit):
        if not self.running:
            return
        victim.hits_taken += 1
        shooter = self.players.get(hit.shooter_player)
        same_team = hit.shooter_team == victim.team
        if shooter and not same_team:
            shooter.hits_given += 1
            shooter.score += self.rules.points_hit
            if hit.sensor in p.HEAD_SENSORS:
                shooter.score += self.rules.points_head_bonus
        self.log({"ev": "hit", "victim": victim.id, "shooter": hit.shooter_player,
                  "sensor": hit.sensor, "hp": hit.hp_after})

    def _mark_dead(self, pl: Player, now: float):
        pl.alive = False
        pl.died_at = now
        pl.death_credited = False
        pl.killed_by = None
        pl.deaths += 1

    def on_death(self, victim: Player, death: p.Death):
        if not self.running:
            return
        now = self.clock()
        if victim.alive:
            self._mark_dead(victim, now)
        elif victim.death_credited:
            return
        # the status may have reported the death first; credit it now
        victim.death_credited = True
        victim.killed_by = death.killer_player
        killer = self.players.get(death.killer_player)
        team_kill = death.killer_team == victim.team
        if killer:
            if team_kill:
                killer.team_kills += 1
                killer.score += self.rules.points_team_kill
            else:
                killer.kills += 1
                killer.score += self.rules.points_kill
        killer_name = killer.name if killer else f"Spieler {death.killer_player}"
        self.feed.appendleft({"t": round(now - self.round_started), "killer": killer_name,
                              "killer_team": death.killer_team, "victim": victim.name,
                              "victim_team": victim.team, "team_kill": team_kill})
        self.log({"ev": "death", "victim": victim.id, "killer": death.killer_player})

    # ---- commands from the web UI ---------------------------------------

    def start_round(self, rules: Rules | None = None):
        if rules:
            self.rules = rules
        self.running = True
        self.round_no += 1
        self.round_started = self.clock()
        self.winner = None
        self.feed.clear()
        for pl in self.players.values():
            pl.reset_round(self.round_started)
        self.send(p.GAME_START, p.PLAYER_ALL, self._start_payload())
        self.log({"ev": "round_start", "round": self.round_no, "rules": asdict(self.rules)})

    def stop_round(self):
        if not self.running:
            return
        self.running = False
        self.round_ended = self.clock()
        scores = self.team_scores()
        self.winner = max(scores, key=scores.get) if scores else None
        if scores and list(scores.values()).count(scores[self.winner]) > 1:
            self.winner = None  # draw
        self.send(p.GAME_STOP, p.PLAYER_ALL, b"")
        self.log({"ev": "round_end", "round": self.round_no, "scores": scores,
                  "winner": self.winner})

    def respawn(self, player_id: int | None = None):
        for pl in self.players.values():
            if player_id is None or pl.id == player_id:
                self._release(pl, self.clock())

    def set_identity(self, player_id: int, team: int, new_id: int | None = None):
        pl = self.players.get(player_id)
        if pl is None or not (0 <= team <= 7):
            return
        new_id = player_id if new_id is None else new_id
        if not (1 <= new_id <= 254):
            return
        self.send(p.SET_IDENTITY, player_id, p.IDENTITY_FMT.pack(team, new_id))
        pl.team = team
        if new_id != player_id:
            del self.players[player_id]
            pl.id = new_id
            self.players[new_id] = pl

    def set_name(self, player_id: int, name: str):
        pl = self.players.get(player_id)
        if pl:
            pl.name = name[:24]
            self.names[player_id] = pl.name

    # ---- periodic -------------------------------------------------------

    def tick(self):
        """Call about once per second: round timer, respawn release and
        bringing the weapons' reported state in line with the server."""
        now = self.clock()
        if self.running and self.rules.duration_s and \
                now - self.round_started >= self.rules.duration_s:
            self.stop_round()
        for pl in self.players.values():
            if not self.online(pl):
                continue
            st = pl.status
            if self.running and not pl.alive and now - pl.died_at >= self.rules.respawn_s:
                self._release(pl, now)
            if st is None:
                continue
            fresh = pl.status_at > pl.released_at  # sent after the last (re)spawn
            if self.running and pl.alive and fresh and not st.alive:
                if now - pl.released_at < RESPAWN_CONFIRM_S:
                    self.send(p.RESPAWN, pl.id, b"")  # lost, repeat
                else:
                    self._mark_dead(pl, now)  # DEATH packet still on its way
            if not self.control_weapons:
                continue
            # server -> weapon packets are not acked, so repeat until the
            # status shows the weapon followed
            if self.running and not st.running:
                self.send(p.GAME_START, pl.id, self._start_payload())
            elif not self.running and st.running:
                self.send(p.GAME_STOP, pl.id, b"")

    def _release(self, pl: Player, now: float):
        pl.alive = True
        pl.released_at = now
        self.send(p.RESPAWN, pl.id, b"")

    def _start_payload(self) -> bytes:
        r = self.rules
        # respawn_s = 0: the weapon waits for the server's RESPAWN
        return p.game_start_payload(r.max_hp, r.damage, r.magazine, r.magazines,
                                    r.friendly_fire, 0)

    # ---- views ----------------------------------------------------------

    def online(self, pl: Player) -> bool:
        return self.clock() - pl.last_seen < ONLINE_TIMEOUT_S

    def team_scores(self) -> dict[int, int]:
        scores = {t: 0 for t in self.teams}
        for pl in self.players.values():
            scores[pl.team] = scores.get(pl.team, 0) + pl.score
        return scores

    def snapshot(self) -> dict:
        now = self.clock()
        elapsed = (now if self.running else self.round_ended) - self.round_started \
            if self.round_no else 0
        players = []
        for pl in sorted(self.players.values(), key=lambda x: (x.team, -x.score, x.id)):
            st = pl.status
            respawn_in = None
            if self.running and not pl.alive:
                respawn_in = max(0, round(self.rules.respawn_s - (now - pl.died_at)))
            players.append({
                "id": pl.id, "team": pl.team, "name": pl.name, "online": self.online(pl),
                "ip": pl.addr[0] if pl.addr else None, "fw": pl.firmware,
                "alive": pl.alive, "respawn_in": respawn_in,
                "kills": pl.kills, "deaths": pl.deaths, "hits_given": pl.hits_given,
                "hits_taken": pl.hits_taken, "team_kills": pl.team_kills, "score": pl.score,
                "status": asdict(st) if st else None,
            })
        return {
            "running": self.running, "round": self.round_no, "elapsed": round(elapsed),
            "duration": self.rules.duration_s, "winner": self.winner,
            "rules": asdict(self.rules),
            "teams": {str(t): {**v, "score": s} for t, v in self.teams.items()
                      for s in [self.team_scores().get(t, 0)]},
            "players": players,
            "feed": list(self.feed),
            "zones": {b: z.summary() for b, z in sorted(self.zones.items())},
        }
