"""
File-based IPC between the Python backend and the UE4SS Lua mod.

The Lua mod writes requests to REQUEST_FILE and reads responses from RESPONSE_FILE.
The Python backend polls REQUEST_FILE, processes requests, and writes to RESPONSE_FILE.
"""

import os
import json
import time

_BASE = os.path.join(os.getenv("LOCALAPPDATA", ""), "DiscoFlow")
os.makedirs(_BASE, exist_ok=True)

REQUEST_FILE = os.path.join(_BASE, "request.json")
RESPONSE_FILE = os.path.join(_BASE, "response.json")
STATE_FILE = os.path.join(_BASE, "state.json")


def write_response(data):
    with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def write_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def read_request():
    if not os.path.exists(REQUEST_FILE):
        return None
    try:
        with open(REQUEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        os.remove(REQUEST_FILE)
        return data
    except Exception:
        return None


def poll(handler, interval=0.3):
    """Blocking poll loop. handler(request) -> response dict."""
    while True:
        req = read_request()
        if req:
            try:
                resp = handler(req)
            except Exception as e:
                resp = {"error": str(e)}
            write_response(resp)
        time.sleep(interval)
