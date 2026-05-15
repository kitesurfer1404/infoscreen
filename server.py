#!/usr/bin/env python3

from aiohttp import web
from pathlib import Path
from configparser import ConfigParser
import asyncio
import json
import base64
import logging
import sys
import os

# ------------------------
# Config
# ------------------------
CONFIG_FILE = "config.ini" # Reads server config from this file
CONFIG_REQUIRED = { "server": ["listen_addr", 
                               "listen_port", 
                               "ctrl_username", 
                               "ctrl_password",
                               "webdir",
                               "ctrl_path",
                               "ws_path_public",
                               "ws_path_ctrl",
                               "autorun_default",
                               "autorun_loop_default",
                               "autorun_delay_default",
                               "default_img"
                               ] }

config = None
app = None
active_img = None
clients = set()

logging.basicConfig(level=logging.INFO)

# ------------------------
# Basic auth middleware
# ------------------------
@web.middleware
async def basic_auth_middleware(request, handler):
    if request.path.startswith(config["server"]["ctrl_path"]):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Basic "):
            return web.Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Login"'},
                text="Authentication required"
            )
            logging.info(f"Client: Auth required.")

        # Decode base64
        encoded = auth_header.split(" ")[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)

        # Check username and password
        if username != config["server"]["ctrl_username"] or password != config["server"]["ctrl_password"]:
            return web.Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Login"'},
                text="Invalid credentials"
            )
            logging.info(f"Client: Invalid credentials.")

    # Grant access
    return await handler(request)


# ------------------------
# Secure File-Loader
# ------------------------
def safe_path(path):
    # Prevent ../../ attacks
    webdir = os.path.abspath(f'./{config["server"]["webdir"]}')
    full_path = os.path.abspath(os.path.join(webdir, path.strip("/")))
    if not full_path.startswith(webdir):
        raise web.HTTPForbidden(text="Access denied")

    # Prevent GIT dir access and file download
    if ".git" in full_path:
        raise web.HTTPNotFound(text="404: Not Found")

    return full_path


# ------------------------
# Static Webserver
# ------------------------
async def static_handler(request):
    try:
        path = request.match_info.get("path", "")

        if path == "" or path.endswith("/"):
            path = path + "index.html"

        file_path = safe_path(path)

        if not os.path.exists(file_path):
            raise web.HTTPNotFound()

        return web.FileResponse(file_path)

    except web.HTTPException:
        raise
    except Exception as e:
        logging.info(f"Static error: {e}")
        raise web.HTTPInternalServerError()


# ------------------------
# Content dir to JSON
# ------------------------
def get_json_content():
    extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    p = Path(config["server"]["webdir"] + "/content")
    dirs = sorted([d for d in p.iterdir() if d.is_dir()])

    json_content = { 'content' : []}
    
    for d in dirs:
        # PATH
        json_path = str(d).removeprefix(config["server"]["webdir"])
        
        # Skip .git dirs
        if ".git" in json_path:
            continue

        json_images = [
            p.name for p in sorted(Path(d).iterdir())
            if p.suffix.lower() in extensions
        ]

        # AUTORUN, LOOP, DELAY from config.txt
        config_txt = d / 'config.txt'
        json_autorun = config["server"]["autorun_default"]
        json_loop = config["server"]["autorun_loop_default"]
        json_delay = config["server"]["autorun_delay_default"]
        if config_txt.exists():
            file_content = config_txt.read_text().splitlines()
            for line in file_content:
                if line.startswith("autorun"):
                    json_autorun = line.split("=")[1].strip().strip('"')
                if line.startswith("loop"):
                    json_loop = line.split("=")[1].strip().strip('"')
                if line.startswith("delay"):
                    json_delay = line.split("=")[1].strip().strip('"')

        # Build JSON
        json_tmp = json.dumps({
          'path' : json_path,
          'autorun' : json_autorun,
          'loop' : json_loop,
          'delay' : json_delay,
          'images' : json_images
        })

        json_content['content'].append(json_tmp)

    return json_content


# ------------------------
# WebSocket Handler
# ------------------------
async def websocket_handler(request):
    global active_img, config

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    clients.add(ws)
    logging.info(f"New client connected: {request.remote} (Clients: {len(clients)})")

    try:
        async for message in ws:
            msg = "";

            if message.type == web.WSMsgType.TEXT:
                msg = message.data.strip()

            logging.info(f"Received message from {request.remote}: {msg}")

            # Keep alive Handling
            if msg == "ping":
                logging.info(f"→ Reply: pong")
                await ws.send_str("pong")
                continue

            # Return content as JSON string
            if msg.startswith('getcontent'):
                content = get_json_content()
                logging.info(f"→ Sending content.")
                await ws.send_str(f"content:{json.dumps(content)}")
                continue

            # Return active image
            if msg.startswith('getactive'):
                logging.info(f"→ Sending active image: {active_img}")
                await ws.send_str(f"active:" + active_img)
                continue

            # Process set-methods only on ctrl-path (basic auth protected) or from local host
            if request.path == config["server"]["ws_path_ctrl"] or request.remote == "127.0.0.1":
            
                # Set active image and notify all clients
                if msg.startswith('setactive:'):
                    active_img = msg.removeprefix('setactive:')
                    logging.info(f"→ Broadcasting active image: {active_img}")
                    await broadcast(f"active:" + active_img)
                    continue

                # Send reload to all clients, e.g. after content change
                if msg.startswith('reload'):
                    active_img = config["server"]["default_img"]
                    logging.info(f"→ Broadcasting reload.")
                    await broadcast(f"reload:")
                    continue

    except Exception as e:
        logging.error(f"WS handler error: {e}")

    finally:
        clients.discard(ws)
        logging.info(f"Client disconnected. (Clients: {len(clients)})")

    return ws


# ------------------------
# Websocket Broadcast
# ------------------------
async def broadcast(msg):
    dead = []
    for ws in clients:
        try:
            if not ws.closed:
                await ws.send_str(msg)
        except:
            dead.append(ws)

    for dc in dead:
        clients.discard(dc)


# ------------------------
# Shutdown procedures
# ------------------------
async def on_shutdown(app):
    logging.info(f"Shutdown: Closing Websockets...")
    for ws in list(clients):
        await ws.close(code=1001, message="Server shutdown")

async def on_cleanup(app):
    logging.info(f"Cleanup")
    sys.exit(0)


# ------------------------
# Read and check config
# ------------------------
def read_config(config_file, required_options):
    conf = ConfigParser()

    # Read file
    read_files = conf.read(config_file)
    if not read_files:
        logging.error(f"Error: Unable to read config file '{config_file}'")
        sys.exit(1)

    missing = []

    # Test sections + options
    for section, options in required_options.items():
        if not conf.has_section(section):
            missing.append(f"Section missing: [{section}]")
            continue

        for option in options:
            if not conf.has_option(section, option):
                missing.append(f"Option missing: [{section}] {option}")

    # List errors and exit
    if missing:
        logging.error("Error in config:")
        for m in missing:
            logging.error(f"  {m}")

        sys.exit(1)

    # No errors
    logging.info(f"Config complete.")
    return conf


# ------------------------
# App setup
# ------------------------
def app_setup():
    global app

    #app = web.Application()  # without Basic Auth
    app = web.Application(middlewares=[basic_auth_middleware])

    app.add_routes([
        # Websocket handlers
        web.get(config["server"]["ws_path_public"], websocket_handler),
        web.get(config["server"]["ws_path_ctrl"], websocket_handler),

        # Static files
        web.get("/{path:.*}", static_handler),
    ])

    # Graceful shutdown
    app.on_shutdown.append(on_shutdown)
    app.on_cleanup.append(on_cleanup)

# ------------------------
# Start
# ------------------------
if __name__ == "__main__":
    config = read_config(CONFIG_FILE, CONFIG_REQUIRED)
    active_img = config["server"]["default_img"]
    app_setup()
    web.run_app(app, host=config["server"]["listen_addr"], port=config.getint("server", "listen_port"))
