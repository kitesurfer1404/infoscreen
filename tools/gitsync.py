#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import logging
import asyncio
import websockets
from configparser import ConfigParser

# ------------------------
# Config
# ------------------------
CONFIG_FILE = "gitsync.ini"
CONFIG_REQUIRED = { "config": ["repository",
                                "directory",
                                "file",
                                "check_interval",
                                "websocket_uri",
                                "notify_server"
                                ] }

HOSTCONFIG_REQUIRED = { "content": ["repository", "branch", "directory"] }

config = None
hostconfig = None

logging.basicConfig(level=logging.INFO)

# ------------------------
# Read and check config
# ------------------------
def read_config(config_file, required_options):
    conf = ConfigParser()

    # Read file
    logging.info(f"Reading config file '{config_file}'...")
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
    logging.info(f"Config file '{config_file}' complete.")
    return conf


# ------------------------
# Shell helper
# ------------------------
def run(cmd, check=True):
    logging.info(f"→ {cmd}")
    ret = None
    try:
        ret = subprocess.run(cmd, shell=True, check=check, text=True, capture_output=True)
    except Exception as e:
        logging.exception(f"Unexpected Error: {cmd}")

    return ret


# ------------------------
# Notify server to reload clients
# ------------------------
async def notify_server(msg):
    ws = None

    try:
        ws = await websockets.connect(config["config"]["websocket_uri"])
        logging.info("WS: Connected.")
        logging.info(f"WS: Sending message: {msg}")
        await ws.send(msg)
    except Exception as e:
        logging.error(f"WS: Error: {e}")
    finally:
        if ws is not None:
            try:
                await ws.close()
                logging.info("WS: Disconnected.")
            except Exception as e:
                logging.error(f"WS: Error during close: {e}")


# ------------------------
# Check for repository and clone if not available
# ------------------------
def git_check_or_clone_repository(repository, directory):
    if not os.path.isdir(directory):
        logging.info(f"Directory {directory} does not exist. Cloning...")
        os.makedirs(directory, exist_ok=True)
        run(f"git clone {repository} {directory}")


# ------------------------
# Check and update repository
# ------------------------
def git_update_repository(directory):
    logging.info(f"Checking {directory} for updates...")

    run(f"git -C {directory} fetch")

    git_local = run(f"git -C {directory} rev-parse @").stdout.strip()
    git_remote = run(f"git -C {directory} rev-parse @{{u}}").stdout.strip()

    if git_local != git_remote:
        logging.info(f"Changes found. Updating...")
        run(f"git -C {directory} pull")
        if config.getboolean("config", "notify_server"):
            logging.info(f"Notifying webserver!")
            asyncio.run(notify_server("reload"))
    else:
        logging.info(f"Nothing changed.")


# ------------------------
# Switch to branch
# ------------------------
def git_content_switch_branch():
    branch = host_config["content"]["branch"]
    directory = host_config["content"]["directory"]
    logging.info(f"Switching to branch {branch}")
    run(f"git -C {directory} checkout {branch}")


# ------------------------
# Sleep + restart
# ------------------------
def wait_and_restart(check_interval):
    logging.info(f"Going to sleep for {check_interval} s. Good night.")
    logging.info("-" * 50)

    time.sleep(check_interval)

    # Restart script
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ------------------------
# Start
# ------------------------
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    config = read_config(CONFIG_FILE, CONFIG_REQUIRED)

    git_check_or_clone_repository(config["config"]["repository"], config["config"]["directory"])
    git_update_repository(config["config"]["directory"])

    host_config_file = os.path.join(config["config"]["directory"], config["config"]["file"])
    host_config = read_config(host_config_file, HOSTCONFIG_REQUIRED)

    git_check_or_clone_repository(host_config["content"]["repository"], host_config["content"]["directory"])
    git_content_switch_branch()
    git_update_repository(host_config["content"]["directory"])

    wait_and_restart(config.getint("config","check_interval"))

