# ⚡ DashStream (v29.0) — In-Car Media & Telemetry Gateway

**DashStream** is a single-file, zero-dependency custom web frontend for **Jellyfin**, **Audiobookshelf**, and **TeslaMate**, engineered for the in-car Chromium browser of Tesla vehicles.

## ✨ Key Features in v29.0
* **🔋 Live Telemetry Edge Bar & Cockpit (`TeslaMate` + `PostgreSQL`):** Real-time SoC, charge limit, kW power, range, 4x TPMS tire pressures, inside/outside temperatures, and a `50 km/h` simulator.
* **📶 Automatic Adaptive Bitrate:** Dynamically switches between `Max`, `1080p`, `720p`, and `480p` based on cellular downlink and buffer stall detection.
* **📺 Stealth Co-Pilot Mode & Canvas Drive Renderer:** Hidden 5-tap logo unlock activates a real-time `<canvas>` video renderer to prevent hardware video freeze in Drive (`D`).
* **🔐 365-Day Persistent Auth:** Dual `localStorage` + cookie persistence with silent background re-login.
* **🕹️ Secret Toybox Easter Egg:** Trigger via 3-tap on `v29.0` badge or search `plaid`, `cnc`, `kitt`, `camp` (Plaid Warp, C&C EVA Radar, German-speaking K.I.T.T. AI, Campfire & Rainbow Charge Bar).
