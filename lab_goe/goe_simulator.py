"""Disposable fake go-e Charger HTTP API v2 for the V15 Beta 6 Docker lab.

NEVER connect this server to real hardware. It intentionally implements only
amp, frc, nrg, pnp and diagnostic /lab paths using standard Python libraries.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, urlsplit
import json
import os

LOCK = Lock()
DEFAULT = {"amp": 16, "frc": 0, "phases": 3, "plugged": True}
STATE = dict(DEFAULT)


def snapshot():
    with LOCK:
        amp = STATE["amp"]
        frc = STATE["frc"]
        phases = STATE["phases"]
        plugged = STATE["plugged"]
    current = amp if plugged and frc != 1 else 0
    power = current * phases * 230
    nrg = [0] * 16
    nrg[:3] = [230, 230 if phases == 3 else 0,
               230 if phases == 3 else 0]
    nrg[4:7] = [current, current if phases == 3 else 0,
                current if phases == 3 else 0]
    nrg[11] = power
    return {"amp": amp, "frc": frc, "nrg": nrg,
            "pnp": phases if plugged else 0, "car": 2 if current else 3}


def update_values(args, allow_force_on=False):
    """Apply synthetic commands; return per-key success with no side effects."""
    updates = {}
    result = {}
    for key, candidates in args.items():
        try:
            value = json.loads(candidates[0])
        except (ValueError, IndexError, TypeError):
            result[key] = "invalid JSON"
            continue
        if key == "amp" and type(value) is int and 6 <= value <= 16:
            updates[key] = value
            result[key] = True
        elif key == "frc" and type(value) is int and value in (
                (0, 1, 2) if allow_force_on else (0, 1)):
            updates[key] = value
            result[key] = True
        elif key == "phases" and type(value) is int and value in (1, 3) and allow_force_on:
            updates[key] = value
            result[key] = True
        elif key == "plugged" and type(value) is bool and allow_force_on:
            updates[key] = value
            result[key] = True
        else:
            result[key] = "unsupported value or key"
    with LOCK:
        STATE.update(updates)
    return result


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlsplit(self.path)
        args = parse_qs(url.query)
        if url.path == "/api/status":
            values = snapshot()
            filtered = args.get("filter", [""])[0].split(",")
            if filtered != [""]:
                values = {key: values[key] for key in filtered if key in values}
            self._json(values)
        elif url.path == "/api/set":
            self._json(update_values(args))
        elif url.path in ("/lab/state", "/"):
            self._json(snapshot())
        elif url.path == "/lab/set":
            result = update_values(args, allow_force_on=True)
            self._json({"result": result, "state": snapshot()})
        elif url.path == "/lab/reset":
            with LOCK:
                STATE.clear()
                STATE.update(DEFAULT)
            self._json(snapshot())
        else:
            self._json({"error": "not found"}, status=404)

    def log_message(self, fmt, *args):
        pass  # Keep localhost demo logs short; production is never contacted.


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
