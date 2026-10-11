# Lasertag-Server (Python)

Spielserver für die Waffen-Firmware ([../firmware/](../firmware/)). Nur
Python-Standardbibliothek (≥ 3.10), keine Installation nötig.

![Live-Anzeige während einer Runde](../docs/bilder/server_weboberflaeche.png)

- UDP-Listener als asyncio-`DatagramProtocol`, HMAC-geprüft, Deduplizierung
  über (Spieler-ID, Session, Laufnummer), `ACK` für jeden `HIT`/`DEATH`
- Teams, Punkte, Runden mit Zeitlimit, Respawn-Freigabe durch den Server
- Live-Anzeige als Webseite über WebSocket, mit Bedienung
- Latenz pro Hallenzone: RTT, RSSI und Access Point aus dem Status jeder Waffe

## Starten

```sh
cd server
cp config.example.json config.json    # Key = LT_HMAC_KEY der Firmware, Teams, Namen, Regeln
python3 -m lasertag_server --config config.json
```

Weboberfläche: `http://<server-ip>:8080/`. In der Firmware `LT_SERVER_IP` auf
diese IP und `LT_SERVER_PORT` auf 4210 setzen.

| Option | Bedeutung |
|---|---|
| `--key` | HMAC-Schlüssel (überschreibt `key` aus der Config) |
| `--udp-port` / `--http-port` | Standard 4210 / 8080 |
| `--admin-token TOKEN` | Bedienung nur mit `http://…:8080/?token=TOKEN`, ohne Token nur Anzeige (z. B. für einen Beamer) |
| `--no-control` | Waffen nicht zwingen, den Spielstand des Servers zu übernehmen (freies Spiel ohne Runde) |
| `--log-dir` | Standard `logs/`: `events-*.jsonl` (alle Ereignisse), `rtt-*.csv` (RTT-Messung pro AP) |

## Ablauf

- Waffen melden sich mit `HELLO` und senden jede Sekunde `STATUS`. Wer 3 s
  nichts schickt, gilt als offline. Antworten gehen an die Absenderadresse.
- **Runde starten** schickt `GAME_START` mit den Regeln an alle Waffen; die
  Waffen setzen HP und Munition zurück. Der Respawn läuft über den Server:
  `respawn_s = 0` an die Waffe, nach Ablauf der Zeit kommt `RESPAWN`.
- Befehle vom Server werden von der Waffe nicht quittiert. Der Server
  vergleicht deshalb laufend den gemeldeten Status mit seinem Stand und
  wiederholt `GAME_START`/`GAME_STOP`/`RESPAWN`, bis die Waffe folgt. In der
  Lobby werden Waffen daher gestoppt (außer mit `--no-control`).
- Meldet der Status einen Tod, bevor das `DEATH`-Paket ankommt, wird der
  Spieler sofort als tot geführt; der Abschuss wird gutgeschrieben, sobald
  `DEATH` eintrifft.
- Team- und ID-Wechsel aus der Weboberfläche gehen per `SET_IDENTITY` an die
  Waffe und werden dort im NVS gespeichert.

## Punkte

| Ereignis | Punkte (`rules` in der Config) |
|---|---|
| Treffer | `points_hit` = 10 |
| Treffer am Stirnband (TSOP 1/2) | zusätzlich `points_head_bonus` = 5 |
| Abschuss | `points_kill` = 100 |
| Teamkill (nur mit Friendly Fire) | `points_team_kill` = −100 |

Teampunkte = Summe der Spielerpunkte; bei Rundenende gewinnt das Team mit den
meisten Punkten.

## Ohne Hardware testen

```sh
python3 -m lasertag_server &
python3 sim_weapon.py --count 6 --rate 0.5     # 6 simulierte Waffen, zufällige Duelle
```

Die simulierten Waffen verhalten sich auf dem Netz wie die Firmware.

```sh
python3 -m unittest discover -s tests
```
