"""python -m lasertag_server [--config config.json] [--key SECRET] ..."""
import argparse
import asyncio
import csv
import dataclasses
import json
import logging
import time
from pathlib import Path

from .game import Game, Rules
from .udp import WeaponProtocol
from .web import WebServer

log = logging.getLogger("server")


def load_config(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def make_rules(base: Rules, data: dict) -> Rules:
    fields = {f.name: f.type for f in dataclasses.fields(Rules)}
    values = dataclasses.asdict(base)
    for k, v in data.items():
        if k in fields:
            values[k] = bool(v) if k == "friendly_fire" else int(v)
    r = Rules(**values)
    # clamp to what the firmware accepts
    r.max_hp = min(max(r.max_hp, 1), 65535)
    r.damage = min(max(r.damage, 1), 65535)
    r.magazine = min(max(r.magazine, 1), 255)
    r.magazines = min(max(r.magazines, 0), 255)
    r.respawn_s = max(r.respawn_s, 0)
    r.duration_s = max(r.duration_s, 0)
    return r


async def main():
    ap = argparse.ArgumentParser(prog="lasertag_server")
    ap.add_argument("--config", help="JSON: teams, players, rules, key")
    ap.add_argument("--key", help="HMAC shared secret (= LT_HMAC_KEY in the firmware)")
    ap.add_argument("--udp-port", type=int, default=4210)
    ap.add_argument("--http-port", type=int, default=8080)
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--admin-token", help="required as ?token= for controls in the web UI")
    ap.add_argument("--no-control", action="store_true",
                    help="do not force the weapons' running state (free play)")
    ap.add_argument("--log-dir", default="logs")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    cfg = load_config(a.config)
    key = (a.key or cfg.get("key") or "change-me").encode()
    if key == b"change-me":
        log.warning("using the default HMAC key 'change-me'")

    log_dir = Path(a.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    events = (log_dir / f"events-{stamp}.jsonl").open("a", buffering=1)
    rtt_file = (log_dir / f"rtt-{stamp}.csv").open("a", buffering=1, newline="")
    rtt_csv = csv.writer(rtt_file)
    rtt_csv.writerow(["time", "player", "bssid", "rssi", "rtt_ms", "rtt_max_ms"])

    def log_event(ev: dict):
        ev = {"time": round(time.time(), 3), **ev}
        events.write(json.dumps(ev) + "\n")
        if ev["ev"] not in ("hit",):
            log.info("%s", ev)

    def log_rtt(pl, st):
        rtt_csv.writerow([round(time.time(), 3), pl.id, st.bssid, st.rssi, st.rtt_ms,
                          st.rtt_max_ms])

    loop = asyncio.get_running_loop()
    udp = WeaponProtocol(key)
    teams = {int(k): v for k, v in cfg.get("teams", {}).items()} or None
    names = {int(k): v for k, v in cfg.get("players", {}).items()}
    game = Game(udp.send, teams=teams, names=names, control_weapons=not a.no_control,
                log=log_event, rtt_log=log_rtt)
    game.rules = make_rules(Rules(), cfg.get("rules", {}))
    udp.game = game
    await loop.create_datagram_endpoint(lambda: udp, local_addr=(a.bind, a.udp_port))

    def on_command(c: dict):
        cmd = c["cmd"]
        if cmd == "start":
            game.start_round(make_rules(game.rules, c.get("rules", {})))
        elif cmd == "stop":
            game.stop_round()
        elif cmd == "respawn":
            game.respawn(c.get("player"))
        elif cmd == "identity":
            game.set_identity(int(c["player"]), int(c["team"]), c.get("new_id"))
        elif cmd == "name":
            game.set_name(int(c["player"]), str(c["name"]))
        elif cmd == "rules":
            game.rules = make_rules(game.rules, c.get("rules", {}))

    web = WebServer(game, a.admin_token, on_command)
    http = await asyncio.start_server(web.handle, a.bind, a.http_port)
    log.info("UDP %d, web UI http://%s:%d/", a.udp_port, a.bind, a.http_port)

    async with http:
        while True:
            await asyncio.sleep(0.5)
            game.tick()
            await web.broadcast()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
