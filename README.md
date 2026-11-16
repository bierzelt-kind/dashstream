# ⚡ DashStream (v33.1) — In-Car Media & Telemetry Gateway

**DashStream** is a single-file, zero-dependency custom web frontend for **Jellyfin**, **Audiobookshelf**, and **TeslaMate**, engineered specifically for the in-car Chromium browser of Tesla vehicles (Model 3 / Model Y).

---

## ✨ Key Features in v33.1

* **🔋 Live Telemetry Edge Bar & Cost Cockpit (`TeslaMate` + `PostgreSQL`):**
  * Top-edge glowing progress bar displaying real-time State of Charge (SoC), charge limit, kW power, and range.
  * Instant PostgreSQL fallback so battery, climate, and tire stats display immediately even while the vehicle is asleep.
  * Interactive **Live Cockpit Modal** displaying all 4 tire pressures (TPMS in bar), inside/outside temperatures, live charging cost calculator (€), 5-session charging history, and a `50 km/h` simulator.
* **📶 Automatic Adaptive Bitrate & Stall-Protection:**
  * Dynamically switches between `Max (Direct)`, `1080p (8M)`, `720p (3M)`, and `480p (1.2M)` based on cellular link speed and buffer stall detection.
* **📺 Stealth Co-Pilot Mode & Canvas Drive Renderer:**
  * Hidden 5-tap logo unlock activates a real-time `<canvas>` video renderer to prevent hardware video freeze in Drive (`D`).
* **🕹️ Secret Toybox Easter Egg (`7 Interactive Modes`):**
  * Triggered via 3-tap on the `v33.1` badge or via search keywords (`plaid`, `cnc`, `kitt`, `camp`).
  * **🔴 K.I.T.T. AI (TV-Accurate 80s Cockpit):** Auto/Normal/Pursuit mode indicators, 3-column voice modulator, 8-bulb Larson scanner, and reactive German voice alerts (`speechSynthesis`).
  * **⚡ Red Alert 2 Chrono-Coil:** High-voltage Tesla coil lightning renderer & global coordinate teleporter.
  * **🌆 Cyberpunk Synthwave:** 3D retrowave horizon grid with live 110-BPM WebAudio bass arpeggiator.
  * **💕 Date-Night Romance Mode:** Floating embers, cozy bass groove & K.I.T.T. compliment generator.
  * **🚀 Plaid Hyperspace, 🛰️ C&C EVA Radar & 🔥 Camp-Mode Fireplace.**
