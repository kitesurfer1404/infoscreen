#!/bin/bash

cd "$(dirname "$0")"

# Pull update at startup
git pull

python3 server.py &
python3 tools/gitsync.py &
unclutter &
xset -dpms s off s noblank s 0 0 s noexpose

# Uncommend next line for reverse SSH tunnel to a frontend server
#autossh -M 0 -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" -o "ExitOnForwardFailure=yes" -N -f -R 8000:localhost:8000 user@myserver.example.com

firefox --kiosk http://localhost:8000
