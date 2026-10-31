# 🚗 Tesla Theater OS – Die Anleitung für Dummies

Dein eigenes **Netflix & Audible direkt im Tesla** – komplett kostenlos über deinen eigenen Heimserver mit **Jellyfin** und **Audiobookshelf**.

---

## 🤔 Was macht dieses Projekt?
Der normale Jellyfin-Player ist im Tesla-Browser oft fummelig: Die Knöpfe sind während der Fahrt viel zu klein, Filme mit Kinoton (Dolby 5.1 / DTS) bleiben im Tesla stumm und bei schwachem Mobilfunk ruckelt das Bild.

**Tesla Theater OS** legt sich als schicke, dunkle Oberfläche im originalen Tesla-Look direkt über dein Jellyfin:
* **Riesige Touch-Knöpfe** speziell für den 16-Zoll-Bildschirm im Auto (und für dein Handy).
* **Automatischer Ton-Fix (AAC):** Macht stumme Dolby-/DTS-Filme sofort hörbar, ohne dass dein Server schwitzen muss.
* **Funkloch-Schutz (Qualitäts-Umschalter):** Schalte mitten im Film mit einem Tipp zwischen `Max`, `1080p`, `720p (LTE)` und `480p (Funkloch)` um.
* **Hörbücher & Kinder-Hörspiele:** Integriert **Audiobookshelf** direkt als eigenen Reiter plus Mini-Audio-Player.
* **Live-Ladebalken (optional mit TeslaMate):** Zeigt dir oben am Bildschirmrand live deinen Akkustand (%), kW-Ladeleistung und die Restzeit am Supercharger.

---

## 🛠️ Schritt 1: Installation auf deinem Server (Dauert 30 Sekunden)

Du brauchst nur einen Server (z. B. Mini-PC, Raspberry Pi oder NAS), auf dem **Jellyfin als Docker-Container** läuft. Logge dich per Terminal (SSH) auf deinem Server ein und kopiere diese 4 Zeilen hinein:

    git clone https://github.com/bierzelt-kind/tesla-theater-os.git
    cd tesla-theater-os
    chmod +x install.sh
    ./install.sh

**Test zuhause im WLAN:**
Öffne deinen Browser am PC oder Handy und rufe diese Adresse auf (ersetze `192.168.1.100` durch die IP-Adresse deines Servers):

    http://192.168.1.100:8096/web/tesla.html

Logge dich einmal mit deinem normalen Jellyfin-Namen und Passwort ein – fertig.

---

## 🌍 Schritt 2: Unterwegs im Tesla nutzen (Der Tailscale-Trick für Dummies)

Damit du unterwegs am Supercharger oder auf Reisen auf deinen Server zuhause zugreifen kannst, solltest du **keine gefährlichen Portfreigaben** in deiner FritzBox einrichten. Nutze stattdessen **Tailscale** (kostenlos).

Weil man im Tesla-Browser selbst keine VPN-App installieren kann, gibt es **zwei kinderleichte Wege**:

### Methode A: Direkt über das Tesla-LTE mit „Tailscale Funnel“ (Empfohlen)
Mit *Tailscale Funnel* bekommt dein Server zuhause eine eigene, verschlüsselte `https://`-Internetadresse, die du direkt im Tesla-Browser eintippen kannst – ganz ohne Handy-Hotspot:

1. **Tailscale auf dem Server installieren** (falls noch nicht geschehen):

       curl -fsSL https://tailscale.com/install.sh | sh
       sudo tailscale up

2. **Im Tailscale-Konto einmalig HTTPS & Funnel aktivieren:**
   * Gehe auf [login.tailscale.com](https://login.tailscale.com) in den Reiter **DNS** und klicke unten auf **Enable HTTPS**.
   * Gehe in den Reiter **Access Controls (ACLs)**,scrolle nach unten oder füge das Funnel-Attribut hinzu (Tailscale bietet dafür direkt einen 1-Klick-Assistenten an, sobald du den nächsten Befehl ausführst).

3. **Jellyfin (Port 8096) sicher über Tailscale freigeben:**
   Gib auf deinem Server diesen Befehl ein:

       sudo tailscale funnel --bg 8096

   *(Optional für Audiobookshelf auf Port 13378 zusätzlich: `sudo tailscale funnel --bg --https=8444 13378`)*

4. **Im Tesla öffnen:**
   Tailscale zeigt dir im Terminal deine persönliche Adresse an (z. B. `https://mein-server.tail1234.ts.net`). Öffne im Tesla-Browser einfach:

       https://mein-server.tail1234.ts.net/web/tesla.html

### Methode B: Ohne Funnel über die Tailscale-App auf dem Handy
Wenn du kein Funnel einrichten willst:
1. Installiere die kostenlose **Tailscale-App** auf deinem Smartphone und melde dich mit demselben Konto an wie auf deinem Server.
2. Schalte Tailscale auf dem Handy ein. Du findest dort die `100.x.x.x`-IP-Adresse deines Servers.
3. Rufe `http://100.x.x.x:8096/web/tesla.html` direkt auf dem Handy auf (und streame den Ton per Bluetooth ans Auto) oder gib die Verbindung per Handy-Hotspot an den Tesla weiter.

---

## 🖥️ Schritt 3: Echtes Vollbild im Tesla & Geheimfunktionen

* **Vollbild aktivieren (während das Auto in „P“ parkt):**
  Tippe oben rechts im Dashboard auf den blauen Knopf **„Vollbild“**. Die Seite nutzt automatisch den bekannten YouTube-Weiterleitungs-Trick, wodurch das Tesla-Menü verschwindet und das Bild den gesamten Bildschirm füllt.
* **Doppel-Tipp zum Spulen:**
  Tippe im laufenden Video zweimal schnell auf die **linke Bildschirmhälfte** (`-15 Sek.`) oder auf die **rechte Bildschirmhälfte** (`+30 Sek.`).
* **Sprache & Qualität wechseln:**
  Oben im Video-Player kannst du jederzeit mit **`🌐 Ton`** zwischen Deutsch/Englisch und mit **`📶 Quali`** die Datenrate für schwaches Mobilfunknetz umschalten.
* **🔓 Geheimer Beifahrer-Modus (Co-Pilot Override):**
  Normalerweise blendet das Dashboard ab 3 km/h das Videobild aus (StVO-Schutz, der Ton läuft weiter).
  * **Freischalten für den Beifahrer:** Tippe oben links **5-mal schnell hintereinander** auf das **`TESLA | THEATER`**-Logo, bis es rot leuchtet (`CO-PILOT UNLOCKED`).
  * **Panik-Knopf:** Solange das Auto rollt und der Beifahrer-Modus aktiv ist, reicht **ein einziger Tipp mitten auf das laufende Video**, um das Video sofort zu schließen und den Geheimmodus wieder zu verriegeln.
