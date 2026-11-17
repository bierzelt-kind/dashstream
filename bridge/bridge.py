import json, time, subprocess, os
import paho.mqtt.client as mqtt
import psycopg2

state = {
    "live": True, "version": "v35.0", "soc": 80, "limit_soc": 80, "kw": 0,
    "added_kwh": 0.0, "eta_min": 0, "range_km": 350,
    "tpms_fl": 2.9, "tpms_fr": 2.9, "tpms_rl": 2.9, "tpms_rr": 2.9,
    "inside_temp": 21.0, "outside_temp": 15.0, "speed": 0, "car_state": "SCHLÄFT / BEREIT"
}
dirty = True
last_check = 0
last_hash = ""

def get_web_dir():
    cmd = "[ -d /jellyfin/jellyfin-web ] && echo /jellyfin/jellyfin-web || echo /usr/share/jellyfin/web"
    r = subprocess.run(["docker", "exec", "jellyfin", "sh", "-c", cmd], capture_output=True, text=True)
    return r.stdout.strip() or "/usr/share/jellyfin/web"

WEB_DIR = get_web_dir()

def load_db_fallback():
    global dirty
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DATABASE_HOST", "database"),
            database=os.environ.get("DATABASE_NAME", "teslamate"),
            user=os.environ.get("DATABASE_USER", "teslamate"),
            password=os.environ.get("DATABASE_PASS", "teslamate_db_pass_2026")
        )
        cur = conn.cursor()
        cur.execute("SELECT battery_level, ROUND(rated_battery_range_km), outside_temp, inside_temp FROM positions WHERE battery_level IS NOT NULL ORDER BY date DESC LIMIT 1;")
        row = cur.fetchone()
        if row:
            if row[0] is not None: state["soc"] = int(row[0])
            if row[1] is not None: state["range_km"] = int(row[1])
            if row[2] is not None: state["outside_temp"] = round(float(row[2]), 1)
            if row[3] is not None: state["inside_temp"] = round(float(row[3]), 1)
        cur.execute("SELECT charge_limit_soc FROM charging_processes WHERE charge_limit_soc IS NOT NULL ORDER BY start_date DESC LIMIT 1;")
        crow = cur.fetchone()
        if crow and crow[0]: state["limit_soc"] = int(crow[0])
        cur.execute("""
            SELECT to_char(start_date AT TIME ZONE 'Europe/Berlin', 'DD.MM.'),
                   COALESCE(ROUND(charge_energy_added::numeric, 1), 0),
                   COALESCE(ROUND(cost::numeric, 2), ROUND((charge_energy_added * 0.38)::numeric, 2), 0),
                   COALESCE(ea.city, ea.name, 'Wallbox / SuC')
            FROM charging_processes cp
            LEFT JOIN addresses ea ON cp.address_id = ea.id
            WHERE charge_energy_added > 0.5
            ORDER BY start_date DESC LIMIT 5;
        """)
        ch_list = []
        for r in cur.fetchall():
            ch_list.append({"date": r[0], "kwh": float(r[1]), "eur": float(r[2]), "loc": r[3]})
        state["charge_history"] = ch_list
        if ch_list and state.get("added_kwh", 0) == 0:
            state["last_added_kwh"] = ch_list[0]["kwh"]
            state["last_cost_eur"] = ch_list[0]["eur"]
        conn.close()
        dirty = True
    except Exception: pass

def push_live_json(force=False):
    global last_hash
    chk = json.dumps({k: v for k, v in state.items() if k != "updated"}, sort_keys=True)
    if not force and chk == last_hash and os.path.exists("/dev/shm/tesla_live.json"): return
    last_hash = chk
    state["updated"] = int(time.time())
    tmp = "/dev/shm/tesla_live.json"
    with open(tmp, "w") as f: f.write(json.dumps(state))
    subprocess.run(["docker", "cp", tmp, f"jellyfin:{WEB_DIR}/tesla_live.json"], capture_output=True)

def ensure_setup():
    global WEB_DIR
    WEB_DIR = get_web_dir()
    if os.path.exists("/tesla-ui/dashstream.html"):
        subprocess.run(["docker", "cp", "-L", "/tesla-ui/dashstream.html", f"jellyfin:{WEB_DIR}/tesla.html"])
        subprocess.run(["docker", "exec", "jellyfin", "chmod", "644", f"{WEB_DIR}/tesla.html"])
    push_live_json(force=True)

def on_connect(client, userdata, flags, rc, *args):
    client.subscribe("teslamate/cars/+/+")

def on_message(client, userdata, msg):
    global dirty
    k = msg.topic.split("/")[-1]
    v = msg.payload.decode("utf-8", errors="ignore").strip()
    if not v: return
    try:
        if k == "battery_level": state["soc"] = int(float(v))
        elif k == "charge_limit_soc": state["limit_soc"] = int(float(v))
        elif k == "charger_power": state["kw"] = int(float(v))
        elif k == "charge_energy_added": state["added_kwh"] = round(float(v), 2)
        elif k == "time_to_full_charge": state["eta_min"] = int(round(float(v) * 60))
        elif k == "rated_battery_range_km": state["range_km"] = int(round(float(v)))
        elif k == "tpms_pressure_fl": state["tpms_fl"] = round(float(v), 2)
        elif k == "tpms_pressure_fr": state["tpms_fr"] = round(float(v), 2)
        elif k == "tpms_pressure_rl": state["tpms_rl"] = round(float(v), 2)
        elif k == "tpms_pressure_rr": state["tpms_rr"] = round(float(v), 2)
        elif k == "inside_temp": state["inside_temp"] = round(float(v), 1)
        elif k == "outside_temp": state["outside_temp"] = round(float(v), 1)
        elif k == "speed": state["speed"] = int(float(v))
        elif k == "state":
            st_map = {"online": "ONLINE", "asleep": "SCHLÄFT", "driving": "FAHRT", "charging": "LÄDT", "suspended": "STANDBY"}
            state["car_state"] = st_map.get(v.lower(), v.upper())
        dirty = True
    except Exception: pass

load_db_fallback()
ensure_setup()
try: client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError: client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
while True:
    try: client.connect("mosquitto", 1883, 60); break
    except Exception: time.sleep(3)
client.loop_start()
while True:
    now = time.time()
    if now - last_check > 120: last_check = now; load_db_fallback()
    if dirty: dirty = False; push_live_json()
    time.sleep(2)
