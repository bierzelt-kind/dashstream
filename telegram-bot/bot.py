import datetime, glob, json, logging, os, subprocess, threading, time, urllib.request
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN, MY_CHAT_ID, JELLYFIN_URL, AUDIOBOOK_URL

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
funnel_timer = None
warn_timer = None
last_low_bat_alert = 0
last_drive_id = None
was_driving = False

async def check_auth(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else 0
    return uid == MY_CHAT_ID

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 Dossier", callback_data="cmd_tesla"),
         InlineKeyboardButton("🪫 Drain-Analyse", callback_data="cmd_drain"),
         InlineKeyboardButton("📍 Standort", callback_data="cmd_wo")],
        [InlineKeyboardButton("🟢 Tunnel 2h AN", callback_data="cmd_jfon"),
         InlineKeyboardButton("🔴 Tunnel AUS", callback_data="cmd_jfoff"),
         InlineKeyboardButton("🗣 K.I.T.T.", callback_data="cmd_kitt")],
        [InlineKeyboardButton("💼 Antonias Reise", callback_data="cmd_reise"),
         InlineKeyboardButton("🎬 Neu", callback_data="cmd_neu"),
         InlineKeyboardButton("🖥 Server", callback_data="cmd_server"),
         InlineKeyboardButton("💾 Backup", callback_data="cmd_backup")]
    ])

def make_bar(pct: int) -> str:
    filled = max(0, min(10, round(pct / 10)))
    col = "🟩" if pct >= 40 else ("🟨" if pct >= 20 else "🟥")
    return col * filled + "⬜" * (10 - filled)

def send_tg_sync(msg: str):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = json.dumps({"chat_id": MY_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": False}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def run_psql(sql: str) -> str:
    r = subprocess.run(
        ["docker", "exec", "teslamate-database-1", "psql", "-U", "teslamate", "-d", "teslamate", "-t", "-A", "-F", "|", "-c", sql],
        capture_output=True, text=True
    )
    return r.stdout.strip()

def background_tesla_sentinel():
    global last_low_bat_alert, last_drive_id, was_driving
    try:
        init_drv = run_psql("SELECT id FROM drives WHERE end_date IS NOT NULL ORDER BY end_date DESC LIMIT 1;")
        if init_drv.isdigit():
            last_drive_id = int(init_drv)
    except Exception:
        pass

    tick = 0
    while True:
        time.sleep(20)
        tick += 1
        try:
            try:
                with open("/dev/shm/tesla_live.json", "r") as f:
                    live_data = json.load(f)
                st = live_data.get("car_state", "SCHLÄFT")
                spd = live_data.get("speed", 0)
                if (st == "FAHRT" or spd > 5) and not was_driving:
                    was_driving = True
                    pos = run_psql("SELECT latitude, longitude, battery_level FROM positions ORDER BY date DESC LIMIT 1;").split("|")
                    maps_url = f"https://www.google.com/maps?q={pos[0]},{pos[1]}" if len(pos) >= 2 else ""
                    send_tg_sync(f"🚨 *BEWEGUNGS-ALARM!*\nDein Tesla fährt ({spd} km/h | Akku: {pos[2] if len(pos)>=3 else '?'}%)!\n📍 [Live-Startpunkt öffnen]({maps_url})")
                elif st != "FAHRT" and spd == 0:
                    was_driving = False
            except Exception:
                pass

            drv_sql = "SELECT d.id, COALESCE(sa.name, sa.city, 'Start'), COALESCE(ea.name, ea.city, 'Zielort'), ROUND(d.distance::numeric, 1), COALESCE(d.duration_min, 0), p.latitude, p.longitude, p.battery_level FROM drives d LEFT JOIN addresses sa ON d.start_address_id = sa.id LEFT JOIN addresses ea ON d.end_address_id = ea.id LEFT JOIN positions p ON d.end_position_id = p.id WHERE d.end_date IS NOT NULL ORDER BY d.end_date DESC LIMIT 1;"
            drv_res = run_psql(drv_sql)
            if drv_res and "|" in drv_res:
                p = drv_res.split("|")
                cur_id = int(p[0])
                if last_drive_id is not None and cur_id > last_drive_id:
                    last_drive_id = cur_id
                    maps_link = f"https://www.google.com/maps?q={p[5]},{p[6]}"
                    send_tg_sync(f"🏁 *Auto angekommen & geparkt!*\n\n📍 *Ziel:* {p[2]}\n🛣 *Strecke:* {p[3]} km in {p[4]} Min.\n🔋 *Akku:* {p[7]}%\n🗺 [Google Maps Pin]({maps_link})")
                elif last_drive_id is None:
                    last_drive_id = cur_id

            now_de = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
            today_str = now_de.strftime("%Y-%m-%d")
            if now_de.hour == 21 and now_de.minute < 5 and globals().get("last_bedtime_check") != today_str:
                globals()["last_bedtime_check"] = today_str
                chk_sql = "SELECT p.battery_level, ROUND(p.rated_battery_range_km), (SELECT COUNT(*) FROM drives WHERE end_date > NOW() - INTERVAL '20 hours'), COALESCE((SELECT COALESCE(ea.name, ea.city) FROM drives d LEFT JOIN addresses ea ON d.end_address_id = ea.id WHERE d.end_date IS NOT NULL ORDER BY d.end_date DESC LIMIT 1), 'Düsseldorf') FROM positions p WHERE p.battery_level IS NOT NULL ORDER BY p.date DESC LIMIT 1;"
                chk = run_psql(chk_sql).split("|")
                if len(chk) >= 4:
                    b_soc, b_rng, drv_today, b_loc = int(chk[0]), chk[1], int(chk[2]), chk[3]
                    is_charging = False
                    try:
                        with open("/dev/shm/tesla_live.json", "r") as lf:
                            ld = json.load(lf)
                            is_charging = (ld.get("kw", 0) > 0 or ld.get("car_state") == "LÄDT")
                    except Exception:
                        pass
                    if drv_today > 0 and b_soc < 35 and not is_charging:
                        send_tg_sync(f"🔌 *21:00 Uhr Lade-Erinnerung!*\n\nDu warst heute unterwegs in *{b_loc}*, stehst bei *{b_soc}% ({b_rng} km)* und das Kabel steckt nicht!")

            if tick % 90 == 0:
                res = run_psql("SELECT battery_level, ROUND(rated_battery_range_km) FROM positions WHERE battery_level IS NOT NULL ORDER BY date DESC LIMIT 1;")
                if res and "|" in res:
                    soc, rng = res.split("|")[:2]
                    if int(soc) <= 12 and (time.time() - last_low_bat_alert) > 21600:
                        last_low_bat_alert = time.time()
                        send_tg_sync(f"🪫 *VAMPIRE-DRAIN WARNUNG!*\nAkku bei *{soc}% ({rng} km)*!")
        except Exception:
            pass

threading.Thread(target=background_tesla_sentinel, daemon=True).start()

def warn_10min():
    send_tg_sync("⚠️ *10-Minuten-Warnung!*\nTunnel schließt in 10 Min.\n👉 Tippe /more für +2h!")

def auto_off():
    global funnel_timer, warn_timer
    if warn_timer: warn_timer.cancel(); warn_timer = None
    for p in ["443", "8443", "10000"]:
        subprocess.run(["tailscale", "funnel", f"--https={p}", "off"], capture_output=True, text=True)
    funnel_timer = None
    send_tg_sync("🛑 *Popcorn-Koma-Schutz:* 2 Stunden sind um – Tunnel ist wieder geschlossen.")

def start_timers(sec=7200):
    global funnel_timer, warn_timer
    if funnel_timer: funnel_timer.cancel()
    if warn_timer: warn_timer.cancel()
    warn_timer = threading.Timer(sec - 600, warn_10min); warn_timer.start()
    funnel_timer = threading.Timer(sec, auto_off); funnel_timer.start()

async def reply_target(update: Update, text: str, markup=True):
    kb = get_main_menu() if markup else None
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=False)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=False)

async def jf_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    r1 = subprocess.run(["tailscale", "funnel", "--bg", "--https=443", "http://127.0.0.1:8096"], capture_output=True, text=True)
    subprocess.run(["tailscale", "funnel", "--bg", "--https=8443", "http://127.0.0.1:13379"], capture_output=True, text=True)
    if r1.returncode == 0:
        start_timers(7200)
        await reply_target(update, "🟢 *Medien-Tunnel für 2 Stunden geöffnet!*\n━━━━━━━━━━━━━━━━━━━━\n🎬 [DashStream Kino öffnen]({JELLYFIN_URL})\n🎧 [Audiobookshelf öffnen]({AUDIOBOOK_URL})")
    else:
        await reply_target(update, f"💥 Fehler:\n`{r1.stderr}`")

async def jf_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    subprocess.run(["tailscale", "funnel", "--bg", "--https=443", "http://127.0.0.1:8096"], capture_output=True, text=True)
    subprocess.run(["tailscale", "funnel", "--bg", "--https=8443", "http://127.0.0.1:13379"], capture_output=True, text=True)
    start_timers(7200)
    await reply_target(update, "⏱ *Tunnel verlängert!* Volle 2 Stunden laufen ab jetzt.")

async def jf_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global funnel_timer, warn_timer
    if not await check_auth(update): return
    if funnel_timer: funnel_timer.cancel(); funnel_timer = None
    if warn_timer: warn_timer.cancel(); warn_timer = None
    for p in ["443", "8443", "10000"]:
        subprocess.run(["tailscale", "funnel", f"--https={p}", "off"], capture_output=True, text=True)
    await reply_target(update, "🔴 *Schotten dicht!* Alle externen Tunnel-Ports sind geschlossen.")

async def drain_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    sql_now = "SELECT battery_level, ROUND(rated_battery_range_km::numeric, 1), EXTRACT(EPOCH FROM date) FROM positions WHERE battery_level IS NOT NULL ORDER BY date DESC LIMIT 1;"
    sql_24h = "SELECT battery_level, ROUND(rated_battery_range_km::numeric, 1), EXTRACT(EPOCH FROM date) FROM positions WHERE battery_level IS NOT NULL AND date <= NOW() - INTERVAL '24 hours' ORDER BY date DESC LIMIT 1;"
    sql_st = "SELECT state, ROUND(SUM(EXTRACT(EPOCH FROM (COALESCE(end_date, NOW()) - GREATEST(start_date, NOW() - INTERVAL '24 hours'))))/3600.0, 1) FROM states WHERE COALESCE(end_date, NOW()) > NOW() - INTERVAL '24 hours' GROUP BY state;"
    now_p = run_psql(sql_now).split("|")
    old_p = run_psql(sql_24h).split("|")
    if len(old_p) < 3:
        old_p = run_psql("SELECT battery_level, ROUND(rated_battery_range_km::numeric, 1), EXTRACT(EPOCH FROM date) FROM positions WHERE battery_level IS NOT NULL ORDER BY date ASC LIMIT 1;").split("|")

    st_rows = run_psql(sql_st).split("\n")
    st_map = {"asleep": 0.0, "online": 0.0, "offline": 0.0}
    for r in st_rows:
        if "|" in r:
            k, v = r.split("|")[:2]
            try: st_map[k] = float(v)
            except Exception: pass

    if len(now_p) >= 3 and len(old_p) >= 3:
        soc_now, rng_now, ts_now = int(now_p[0]), float(now_p[1]), float(now_p[2])
        soc_old, rng_old, ts_old = int(old_p[0]), float(old_p[1]), float(old_p[2])
        hours = max(1.0, (ts_now - ts_old) / 3600.0)
        soc_diff = soc_old - soc_now
        rng_diff = round(rng_old - rng_now, 1)
        kwh_lost = round(max(0.0, soc_diff) * 0.60, 2)
        avg_watts = int(round((kwh_lost * 1000.0) / hours)) if soc_diff > 0 else 15
        sleep_h = round(st_map.get("asleep", 0.0) + st_map.get("offline", 0.0), 1)
        online_h = round(st_map.get("online", 0.0), 1)
        sleep_pct = min(100, int(round((sleep_h / 24.0) * 100)))

        if soc_now <= 20 and online_h < 4:
            diag = "💤 *Tiefschlaf aktiv (Wächter <20% automatisch aus!)*\nDein Tesla spart jetzt maximal Strom (~0,5% pro Tag)."
        elif avg_watts > 140 or online_h > 12:
            diag = "👁️ *Wächtermodus / Standby aktiv!*\nAuto schläft kaum (~220 W Dauerlast durch Kameras)."
        else:
            diag = "✅ *Gesunder Ruhemodus!*\nSteuergeräte schlafen sauber ein, minimaler Standverlust."

        msg = (
            f"🪫 *VAMPIRE-DRAIN & SCHLAF-ANALYSE*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔋 *Aktueller Akku:* `{soc_now}%` ({rng_now} km)\n"
            f"{make_bar(soc_now)}\n\n"
            f"📉 *Verlust (letzte {int(round(hours))}h):* `-{soc_diff}%` (`-{rng_diff} km` / `~{kwh_lost} kWh`)\n"
            f"⚡ *Ø Ruhestrom:* `~{avg_watts} Watt`\n"
            f"😴 *Schlaf-Bilanz (24h):* `{sleep_h}h Tiefschlaf` ({sleep_pct}%) | `{online_h}h Wach`\n\n"
            f"🩺 *KI-Diagnose:*\n{diag}"
        )
        await reply_target(update, msg)
    else:
        await reply_target(update, "⚠️ Noch nicht genügend Messpunkte für die Drain-Analyse.")

async def wo_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    sql = "SELECT p.latitude, p.longitude, p.battery_level, to_char(p.date AT TIME ZONE 'Europe/Berlin', 'DD.MM.YYYY HH24:MI'), COALESCE((SELECT COALESCE(ea.name, ea.city) FROM drives d LEFT JOIN addresses ea ON d.end_address_id = ea.id WHERE d.end_date IS NOT NULL ORDER BY d.end_date DESC LIMIT 1), 'Düsseldorf-Bilk') FROM positions p WHERE p.latitude IS NOT NULL ORDER BY p.date DESC LIMIT 1;"
    res = run_psql(sql).split("|")
    if len(res) >= 5:
        lat, lon, soc, dt, addr = res[:5]
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        await reply_target(update, f"📍 *FAHRZEUG-ORTUNG (PASSIV)*\n━━━━━━━━━━━━━━━━━━━━\n🏠 *Standort:* {addr}\n🧭 *Koordinaten:* `{lat}, {lon}`\n🔋 *Akku vor Ort:* `{soc}%`\n🕒 *Letztes Signal:* {dt} Uhr\n\n🗺 [Exakten Parkplatz auf Google Maps öffnen]({maps_url})")

async def tesla_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    pos_sql = "SELECT battery_level, ROUND(rated_battery_range_km), COALESCE(outside_temp, 0), COALESCE(inside_temp, 0), ROUND(odometer), COALESCE(tpms_pressure_fl, 0), COALESCE(tpms_pressure_fr, 0), COALESCE(tpms_pressure_rl, 0), COALESCE(tpms_pressure_rr, 0), to_char(date AT TIME ZONE 'Europe/Berlin', 'DD.MM.YYYY HH24:MI'), latitude, longitude FROM positions WHERE battery_level IS NOT NULL ORDER BY date DESC LIMIT 1;"
    drv_sql = "SELECT COALESCE(ea.name, ea.city, 'Unbekannt'), ROUND(d.distance::numeric, 1), to_char(d.end_date AT TIME ZONE 'Europe/Berlin', 'DD.MM. HH24:MI') FROM drives d LEFT JOIN addresses ea ON d.end_address_id = ea.id WHERE d.end_date IS NOT NULL ORDER BY d.end_date DESC LIMIT 1;"
    chg_sql = "SELECT COALESCE(charge_energy_added, 0), COALESCE(charge_limit_soc, 80), to_char(COALESCE(end_date, start_date) AT TIME ZONE 'Europe/Berlin', 'DD.MM. HH24:MI') FROM charging_processes ORDER BY start_date DESC LIMIT 1;"
    pos = run_psql(pos_sql).split("|")
    drv = run_psql(drv_sql).split("|")
    chg = run_psql(chg_sql).split("|")
    car_state = "SCHLÄFT / BEREIT"
    try:
        with open("/dev/shm/tesla_live.json", "r") as f:
            car_state = json.load(f).get("car_state", car_state)
    except Exception:
        pass
    if len(pos) >= 12:
        soc, rng, o_tmp, i_tmp, odo, fl, fr, rl, rr, dt, lat, lon = pos[:12]
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        bar = make_bar(int(soc))
        msg = (
            f"🚗 *TESLA MODEL Y – COCKPIT (v37.0)*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 *Status:* `{car_state}`\n"
            f"🔋 *Akku:* *{soc}%* (`{rng} km`) • Limit: `{chg[1] if len(chg)>=2 else 80}%`\n"
            f"{bar}\n\n"
            f"🌡 *Klima:* Innen `{i_tmp}°C` | Außen `{o_tmp}°C`\n"
            f"🛞 *Reifendruck:* VL `{fl}` | VR `{fr}` | HL `{rl}` | HR `{rr}` bar\n"
            f"🛣 *Kilometerstand:* `{odo} km`\n"
            f"📍 *Parkt in:* [{drv[0] if len(drv)>=3 else 'Düsseldorf'}]({maps_url})\n"
            f"⚡ *Letzte Ladung:* `+{chg[0] if len(chg)>=3 else 0} kWh` (`{round(float(chg[0])*0.38, 2) if len(chg)>=3 else 0} €`)\n"
            f"🕒 *Datenstand:* {dt} Uhr"
        )
        await reply_target(update, msg)

async def reise_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    sql = "SELECT COUNT(*), COALESCE(ROUND(SUM(d.distance)::numeric, 1), 0) FROM drives d LEFT JOIN brd_claims b ON d.id = b.drive_id WHERE COALESCE(d.distance, 0) > 0.1 AND COALESCE(b.claimed, FALSE) = FALSE;"
    res = run_psql(sql).split("|")
    if len(res) >= 2:
        cnt, km = int(res[0]), float(res[1])
        await reply_target(update, f"💼 *ANTONIAS REISEKOSTEN (DEZERNAT 55)*\n━━━━━━━━━━━━━━━━━━━━\n🚙 *Offene Dienstfahrten:* `{cnt}`\n📏 *Abrechnungs-Strecke:* `{km:.1f} km`\n💶 *Erstattung (§ 6 LRKG):* *{km*0.30:.2f} €*")

async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await reply_target(update, "⏳ *Voll-Backup läuft...* Sichere Datenbanken, Docker-Configs & Code...")
    r = subprocess.run([os.path.expanduser("~/backup_all.sh")], capture_output=True, text=True)
    out = r.stdout.strip() or "Backup abgeschlossen."
    bfiles = sorted(glob.glob(os.path.expanduser("~/backups/*.tar.gz")), key=os.path.getmtime)[-3:]
    lines = [f"• {os.path.basename(p)} ({os.path.getsize(p)/1048576:.1f} MB)" for p in bfiles]
    flist = "\n".join(lines) if lines else "Keine Archive gefunden"
    await reply_target(update, f"💾 *SERVER-BACKUP ABGESCHLOSSEN*\n━━━━━━━━━━━━━━━━━━━━\n{out}\n\n📂 *Gespeicherte Archive:*\n`{flist}`")

async def server_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    up = subprocess.run(["uptime", "-p"], capture_output=True, text=True).stdout.strip()
    df = subprocess.run(["sh", "-c", "df -h / | tail -1 | awk '{print $3 \" / \" $2 \" (\" $5 \")\"}'"], capture_output=True, text=True).stdout.strip()
    mem = subprocess.run(["sh", "-c", "free -h | awk '/Mem:/ {print $3 \" / \" $2}'"], capture_output=True, text=True).stdout.strip()
    fn = subprocess.run(["tailscale", "funnel", "status"], capture_output=True, text=True).stdout.strip()
    await reply_target(update, f"🖥 *HOME-SERVER DÜSSELDORF-BILK*\n━━━━━━━━━━━━━━━━━━━━\n🔒 *Tailscale Funnel:* {'🟢 OFFEN (Streaming aktiv)' if 'https://' in fn else '🔴 GESCHLOSSEN (Abgesichert)'}\n⏱ *Uptime:* `{up}`\n🧠 *RAM-Nutzung:* `{mem}`\n💾 *SSD-Speicher:* `{df}`")

async def kitt_voice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_override=""):
    if not await check_auth(update): return
    from gtts import gTTS
    custom_txt = custom_override or (" ".join(context.args).strip() if context and context.args else "")
    if not custom_txt:
        pos = run_psql("SELECT battery_level, ROUND(rated_battery_range_km), COALESCE(outside_temp, 15) FROM positions WHERE battery_level IS NOT NULL ORDER BY date DESC LIMIT 1;").split("|")
        soc = pos[0] if len(pos) >= 1 else "80"
        rng = pos[1] if len(pos) >= 2 else "350"
        tmp = pos[2] if len(pos) >= 3 else "15"
        custom_txt = f"Guten Morgen Mischa. Hier spricht KITT aus Düsseldorf Bilk. Alle Systeme laufen normal. Meine Batterie liegt bei {soc} Prozent, das reicht für {rng} Kilometer. Da ich unter 20 Prozent bin, ist der Wächtermodus deaktiviert und ich schlafe bei {tmp} Grad Außentemperatur."
    tts = gTTS(text=custom_txt, lang='de', slow=False)
    ogg_path = "/tmp/kitt_msg.mp3"
    tts.save(ogg_path)
    msg_obj = update.callback_query.message if update.callback_query else update.message
    with open(ogg_path, "rb") as audio_file:
        await msg_obj.reply_voice(voice=audio_file, caption=f"🔴 *K.I.T.T. COMLINK:*\n_{custom_txt}_", parse_mode="Markdown", reply_markup=get_main_menu())

async def neu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    cmd = r"docker exec jellyfin find /media /data -type f \( -name '*.mkv' -o -name '*.mp4' \) -printf '%T@|%f\n' 2>/dev/null | sort -nr | head -n 5"
    r = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True).stdout.strip()
    if not r:
        cmd2 = r"find /mnt /media /home/bierz -maxdepth 4 -type f \( -name '*.mkv' -o -name '*.mp4' \) -printf '%T@|%f\n' 2>/dev/null | sort -nr | head -n 5"
        r = subprocess.run(["sh", "-c", cmd2], capture_output=True, text=True).stdout.strip()
    if r:
        lines = ["🎬 *NEUZUGÄNGE AUF JELLYFIN*\n━━━━━━━━━━━━━━━━━━━━"]
        for row in r.split("\n"):
            if "|" in row:
                fname = row.split("|", 1)[1].rsplit(".", 1)[0]
                lines.append(f"• `{fname}`")
        await reply_target(update, "\n".join(lines))
    else:
        await reply_target(update, "ℹ️ Konnte Medien-Ordner gerade nicht scannen.")

async def wunsch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    query = " ".join(context.args).strip() if context and context.args else ""
    if not query:
        await reply_target(update, "👉 Bitte gib einen Titel an, z.B.: `/wunsch Gladiator 2`")
        return
    await reply_target(update, f"🍿 *Suche für '{query}' bereit!*\n👉 [Hier direkt in Jellyseerr anfordern](http://100.86.200.106:5055)")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await reply_target(update,
        "🤖 *TESLA & HOME-SERVER AI BOT (v37.0)*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Schreib einfach *normale Sätze*, schick *Sprachnachrichten* oder nutze die *Buttons*!\n\n"
        "🪫 */drain* — 24h Stromverlust-, Watt- & Tiefschlaf-Analyse\n"
        "🚗 */tesla* — Komplettes Fahrzeug-Cockpit\n"
        "📍 */wo* — Passiver GPS-Tracker & Google-Maps-Pin\n"
        "🗣 */kitt [Text]* — K.I.T.T. schickt eine Sprachnachricht\n"
        "💼 */reise* — Antonias offene Reisekosten (§ 6 LRKG)\n"
        "💾 */backup* — Komplett-Backup aller Docker-Stacks & DBs\n"
        "🎬 */neu* & */wunsch* — Jellyfin-Neuzugänge & Suche\n"
        "🟢 */jfon* | ⏱ */more* | 🔴 */jfoff* — Tunnel-Steuerung\n"
        "🖥 */server* — System-Check & Firewall-Status"
    )

async def route_smart_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, txt: str):
    t = txt.lower().strip()
    if any(w in t for w in ["drain", "verlust", "strom", "wächter", "sentry", "schläft", "schlaf", "watt", "leer", "vampire"]):
        await drain_status(update, context)
    elif any(w in t for w in ["backup", "sicherung", "sichern"]):
        await backup_cmd(update, context)
    elif any(w in t for w in ["tunnel aus", "schließen", "stopp", "offline", "ausmachen"]):
        await jf_off(update, context)
    elif any(w in t for w in ["verlängern", "mehr zeit", "weiter schauen"]):
        await jf_more(update, context)
    elif any(w in t for w in ["tunnel", "kino", "bibi", "fanny", "stream", "anmachen", "öffnen", "hörbuch"]):
        await jf_on(update, context)
    elif any(w in t for w in ["wo ", "wo?", "standort", "adresse", "parkt", "karte", "gps"]):
        await wo_status(update, context)
    elif any(w in t for w in ["reise", "antonia", "abrechnung", "kilometer", "bezirksregierung", "geld"]):
        await reise_status(update, context)
    elif any(w in t for w in ["server", "speicher", "ram", "ssd", "uptime", "cpu"]):
        await server_status(update, context)
    elif any(w in t for w in ["neu", "filme", "serien", "zuletzt"]):
        await neu_cmd(update, context)
    elif any(w in t for w in ["kitt", "sprich", "sag mal", "sprachnachricht"]):
        clean_p = t.replace("kitt", "").replace("sag mal", "").strip()
        await kitt_voice_cmd(update, context, custom_override=clean_p if len(clean_p) > 8 else "")
    elif any(w in t for w in ["hilfe", "help", "menü", "start", "hallo", "moin"]):
        await help_command(update, context)
    else:
        await tesla_status(update, context)

async def handle_text_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await route_smart_intent(update, context, update.message.text)

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    q = update.callback_query
    await q.answer()
    d = q.data
    if d == "cmd_tesla": await tesla_status(update, context)
    elif d == "cmd_drain": await drain_status(update, context)
    elif d == "cmd_wo": await wo_status(update, context)
    elif d == "cmd_jfon": await jf_on(update, context)
    elif d == "cmd_jfoff": await jf_off(update, context)
    elif d == "cmd_kitt": await kitt_voice_cmd(update, context)
    elif d == "cmd_reise": await reise_status(update, context)
    elif d == "cmd_neu": await neu_cmd(update, context)
    elif d == "cmd_server": await server_status(update, context)
    elif d == "cmd_backup": await backup_cmd(update, context)

async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    import speech_recognition as sr
    from pydub import AudioSegment
    try:
        v_file = await update.message.voice.get_file()
        ogg_p, wav_p = "/tmp/tg_in.ogg", "/tmp/tg_in.wav"
        await v_file.download_to_drive(ogg_p)
        AudioSegment.from_file(ogg_p).export(wav_p, format="wav")
        rec = sr.Recognizer()
        with sr.AudioFile(wav_p) as src:
            audio = rec.record(src)
        txt = rec.recognize_google(audio, language="de-DE")
        await update.message.reply_text(f"🎙 *Verstanden:* „{txt}“", parse_mode="Markdown")
        await route_smart_intent(update, context, txt)
    except Exception:
        await reply_target(update, "⚠️ Konnte die Sprachnachricht akustisch nicht verstehen – nutz einfach die Buttons:")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("jfon", jf_on))
    app.add_handler(CommandHandler("more", jf_more))
    app.add_handler(CommandHandler("jfoff", jf_off))
    app.add_handler(CommandHandler("drain", drain_status))
    app.add_handler(CommandHandler("strom", drain_status))
    app.add_handler(CommandHandler("wo", wo_status))
    app.add_handler(CommandHandler("ort", wo_status))
    app.add_handler(CommandHandler("tesla", tesla_status))
    app.add_handler(CommandHandler("reise", reise_status))
    app.add_handler(CommandHandler("server", server_status))
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CommandHandler("kitt", kitt_voice_cmd))
    app.add_handler(CommandHandler("neu", neu_cmd))
    app.add_handler(CommandHandler("wunsch", wunsch_cmd))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hilfe", help_command))
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CallbackQueryHandler(handle_button_click))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_msg))
    app.run_polling()
