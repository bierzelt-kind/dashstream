#!/bin/bash
docker cp dashstream.html jellyfin:/usr/share/jellyfin/web/dashstream.html
docker cp dashstream.html jellyfin:/usr/share/jellyfin/web/tesla.html
echo 'DashStream installiert: /web/dashstream.html'
