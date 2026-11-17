# ⚡ DashStream & TeslaMate Suite (v37.0)
**In-Car Media Gateway, Live Telemetry Cockpit & AI Telegram Sentinel for Tesla Vehicles**

![Version](https://img.shields.io/badge/Release-v37.0-e82127?style=for-the-badge&logo=tesla&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Docker%20%7C%20Ubuntu%20%7C%20Tailscale-38bdf8?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-4ade80?style=for-the-badge)

**DashStream** ist eine komplette, selbstgehostete Open-Source-Suite für **Jellyfin**, **Audiobookshelf** und **TeslaMate** (`PostgreSQL` + `MQTT`). Sie wurde speziell für den Chromium-Browser in Tesla-Fahrzeugen (Model 3 / Model Y) entwickelt und kombiniert ruckelfreies In-Car-Streaming mit Echtzeit-Fahrzeugtelemetrie und einem intelligenten **Telegram-Wächter-Bot**.

---

## 📦 Projektstruktur (Komplett-Paket)

* **`dashstream/dashstream.html`** — Zero-Dependency Single-File Web-UI für Jellyfin & Audiobookshelf mit Live-Akku-Leiste, Lade-Prognose, Kinder-Touch-Sperre & Secret Toybox.
* **`bridge/bridge.py`** — Verbindet den lokalen TeslaMate-MQTT-Broker und die PostgreSQL-Datenbank verzögerungsfrei (und **ohne** das Auto aufzuwecken!) mit dem Web-Frontend.
* **`telegram-bot/bot.py`** — Interaktiver Telegram-Bot mit Inline-Cockpit-Buttons, Sprachsteuerung (Voice-to-Command), K.I.T.T.-Sprachausgabe, GPS-Wächter & 24h-Vampire-Drain-Analyse.
* **`scripts/backup_all.sh`** — Vollautomatisches Backup-Skript für die PostgreSQL-Datenbank und alle Docker-Compose-Stacks.
* **`install.sh`** — Interaktiver **1-Klick-Installer**, der alle Komponenten automatisch einrichtet.

---

## ✨ Highlights & Features (v37.0)

### 🎬 1. DashStream In-Car Media Player
* **🔋 Live-Akku-Prognose am Film-Ende:** Berechnet während des Films live gegen deine aktuelle Ladeleistung (`kW`) oder den Standverbrauch, mit wie viel Prozent Akku du am Ende der Folge aussteigst.
* **📲 Instant Exit Handoff Sync (P-Gang & Tür-Sensor):** Sobald du auf `P` schaltest oder die Fahrertür öffnest, speichert DashStream sekundengenau den Zeitstempel auf Jellyfin zum nahtlosen Weiterschauen/-hören auf dem Smartphone.
* **⏭️ Serien-Autopilot & Skip-Intro:** `+85s Intro überspringen`-Button und automatischer Episoden-Wechsel in den letzten 15 Sekunden.
* **🔒 Kinder-Schloss (Touch-Lock) & 🌙 Sleep-Timer:** Verhindert versehentliches Wegklicken durch Kinder auf der Rückbank (Entsperren per Doppelklick) und stoppt den Stream nach 30/60/90 Minuten.
* **🕹️ Secret Toybox (7 Modi):** 3x Tippen auf das Versions-Badge öffnet u. a. das 80er K.I.T.T.-Cockpit, die Red Alert 2 Chrono-Spule und den Cyberpunk-Synthwave-Arpeggiator.

### 🤖 2. Intelligenter Telegram-Bot & Hintergrund-Wächter
* **🎛️ Klickbares Cockpit-Dashboard:** Alle wichtigen Aktionen direkt über Inline-Buttons unter jeder Nachricht steuerbar.
* **🎙️ Echte Sprachsteuerung & Freitext-KI:** Unterstützt Sprachnachrichten und natürliche Textbefehle im Chat.
* **🪫 `/drain` (24h Vampire-Drain & Schlaf-Diagnose):** Berechnet den Akkuverlust der letzten 24 Stunden in %, km, kWh und Watt sowie die Tiefschlaf-Quote (`asleep` vs. `online`).
* **🚨 Automatische Push-Wächter:** Abfahrts-Alarm, Ankunfts-Tracker mit Google-Maps-Pin und täglicher 21:00-Uhr-Lade-Checker (<35 % Akku nach Fahrttagen).

---

## 🚀 Schnell-Installation (1-Klick-Installer)

Öffne dein Terminal auf dem Server und führe folgende Befehle aus:

    git clone https://github.com/bierzelt-kind/dashstream.git
    cd dashstream
    sudo ./install.sh

Der interaktive Assistent fragt automatisch nach deinem TeslaMate-Pfad, kopiert die Oberfläche in deinen Jellyfin-Container und richtet auf Wunsch den Telegram-Bot inklusive Systemd-Service ein.

---

## 📱 Telegram-Befehle im Überblick

* **`/start`** oder **`/help`** — Öffnet das interaktive Button-Cockpit und die Befehlsübersicht.
* **`/tesla`** — Großes Fahrzeug-Dossier (Status, Akku-Balken, Klima, Reifendruck, Tacho, letzte Ladung).
* **`/drain`** oder **`/strom`** — 24-Stunden-Ruhestrom-Analyse (Verlust in %, kWh, Ø Watt, Schlaf-Stunden).
* **`/wo`** oder **`/ort`** — Passiver GPS-Standort aus der Datenbank mit direktem Google-Maps-Pin.
* **`/kitt [Text]`** — Schickt eine deutsche Sprachnachricht im K.I.T.T.-Stil.
* **`/jfon`** / **`/more`** / **`/jfoff`** — Öffnet den Tailscale-Streaming-Tunnel für 2h, verlängert ihn oder schließt alle Ports.
* **`/neu`** & **`/wunsch [Titel]`** — Zeigt die 5 neuesten Filme/Folgen auf Jellyfin bzw. öffnet die Jellyseerr-Suche.
* **`/server`** & **`/backup`** — Zeigt System-Status bzw. startet ein Komplett-Backup aller Datenbanken & Docker-Configs.

---

## 🛡️ Sicherheit & Batterie-Schutz (Zero-Wakeup-Garantie)
Weder `dashstream.html` noch `bridge.py` oder `bot.py` senden API-Requests an die offiziellen Tesla-Server. Alle Daten stammen zu 100 % passiv aus der lokalen PostgreSQL-Datenbank und dem MQTT-Broker, sodass das Fahrzeug ungestört im Tiefschlaf bleibt.
