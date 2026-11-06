import json
import os
import re
import shutil
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import ticket_lookup

HOST, PORT = "127.0.0.1", 8765
INDEX = Path(__file__).with_name("sip-chatbot.html")
CATEGORIZE_PAGE = Path(__file__).with_name("sip-categorize.html")
RECOMMEND_PAGE = Path(__file__).with_name("sip-recommend.html")
STATIC_DIR = Path(__file__).with_name("static")
STATIC_FILES = {
    "/static/app.js": "text/javascript; charset=utf-8",
    "/static/categorize.js": "text/javascript; charset=utf-8",
    "/static/style.css": "text/css; charset=utf-8",
    "/static/theme.js": "text/javascript; charset=utf-8",
}
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
INSTALL_CMD = ["npm", "install", "-g", "@github/copilot"]
LOG_LIMIT = 8000
LLM_TIMEOUT = 120
INDEX_DATA = None
LANGS = ("en", "it")


class SetupError(Exception):
    """Setup failure identified by a key the page translates (see ERRORS in sip-chatbot.html)."""

    def __init__(self, key, code=None):
        super().__init__(key)
        self.key, self.code = key, code


def error_info(e):
    if isinstance(e, SetupError):
        return {"key": e.key, "code": e.code}
    return {"key": "generic", "detail": str(e)}

lock = threading.Lock()
state_lock = threading.Lock()
install = {"running": False, "log": "", "error": None}
login = {"running": False, "output": "", "error": None, "proc": None}


def find_copilot():
    path = shutil.which("copilot")
    if path:
        return path
    # PATH ovog procesa može biti zastareo odmah posle `npm install -g`
    npm = shutil.which("npm")
    if not npm:
        return None
    try:
        prefix = subprocess.run([npm, "prefix", "-g"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return None
    for name in ("copilot.cmd", "copilot"):
        for base in (prefix, os.path.join(prefix, "bin")):
            candidate = os.path.join(base, name)
            if prefix and os.path.isfile(candidate):
                return candidate
    return None


COPILOT = find_copilot()


def is_logged_in():
    if any(os.environ.get(v) for v in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")):
        return True
    home = Path(os.environ.get("COPILOT_HOME") or Path.home() / ".copilot")
    try:
        text = (home / "config.json").read_text(encoding="utf-8")
        text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
        return bool(json.loads(text).get("loggedInUsers"))
    except (OSError, ValueError):
        return False


def kill_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def stream_process(cmd, target, key):
    """Pokreće komandu i dopisuje njen izlaz u target[key]; vraća kod izlaza."""
    proc = subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    with state_lock:
        target["proc"] = proc
    for line in proc.stdout:
        with state_lock:
            target[key] = (target[key] + line)[-LOG_LIMIT:]
    return proc.wait()


def install_worker():
    global COPILOT
    npm = shutil.which("npm")
    try:
        if not npm:
            raise SetupError("npm_missing")
        code = stream_process([npm] + INSTALL_CMD[1:], install, "log")
        if code != 0:
            raise SetupError("install_failed", code)
        found = find_copilot()
        if not found:
            raise SetupError("not_in_path")
        COPILOT = found
    except Exception as e:
        with state_lock:
            install["error"] = error_info(e)
    finally:
        with state_lock:
            install["running"] = False
            install.pop("proc", None)


def login_worker():
    try:
        code = stream_process([COPILOT, "login", "--device-code"], login, "output")
        if code != 0:
            raise SetupError("login_failed", code)
    except Exception as e:
        with state_lock:
            login["error"] = error_info(e)
    finally:
        with state_lock:
            login["running"] = False
            login["proc"] = None


def start_install():
    with state_lock:
        if install["running"] or COPILOT:
            return
        install.update(running=True, log="", error=None)
    threading.Thread(target=install_worker, daemon=True).start()


def start_login():
    with state_lock:
        if login["running"] or not COPILOT:
            return
        login.update(running=True, output="", error=None, proc=None)
    threading.Thread(target=login_worker, daemon=True).start()


def get_status():
    with state_lock:
        if install["running"]:
            state = "installing"
        elif not COPILOT:
            state = "no_copilot"
        elif login["running"]:
            state = "logging_in"
        elif not is_logged_in():
            state = "needs_login"
        else:
            state = "ready"
        out = {
            "state": state,
            "npm": bool(shutil.which("npm")),
            "install_cmd": " ".join(INSTALL_CMD),
            "install_log": install["log"],
            "install_error": install["error"],
            "login_error": login["error"],
        }
        text = login["output"]
    url = re.search(r"https://\S+", text)
    code = re.search(r"\b[A-Z0-9]{4}-[A-Z0-9]{4}\b", text)
    out["login_url"] = url.group(0) if url else None
    out["login_code"] = code.group(0) if code else None
    return out


def run_copilot(prompt):
    """Single independent call (no --continue); raises on failure so lookup() can fall back."""
    with lock:
        proc = subprocess.run([COPILOT, "--silent"], input=prompt, capture_output=True,
                              text=True, encoding="utf-8", timeout=LLM_TIMEOUT)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "empty reply")
    return proc.stdout


def load_index():
    global INDEX_DATA
    if INDEX_DATA is None:
        INDEX_DATA = ticket_lookup.TicketIndex.from_csv()
    return INDEX_DATA


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self):
        return self.headers.get("Host") in ALLOWED_HOSTS

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "{}")
        if self.path in ("/", "/index.html"):
            return self._send(200, INDEX.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if self.path == "/categorize":
            return self._send(200, CATEGORIZE_PAGE.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if self.path == "/recommend":
            return self._send(200, RECOMMEND_PAGE.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if self.path in STATIC_FILES:
            name = self.path.rsplit("/", 1)[1]
            return self._send(200, (STATIC_DIR / name).read_text(encoding="utf-8"), STATIC_FILES[self.path])
        if self.path == "/api/status":
            return self._send(200, json.dumps(get_status()))
        self._send(404, "{}")

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, "{}")
        origin = self.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] not in ALLOWED_HOSTS:
            return self._send(403, "{}")
        if self.path == "/api/install":
            start_install()
            return self._send(200, json.dumps(get_status()))
        if self.path == "/api/login":
            start_login()
            return self._send(200, json.dumps(get_status()))
        if self.path not in ("/api/chat", "/api/categorize", "/api/recommend"):
            return self._send(404, "{}")
        if get_status()["state"] != "ready":
            return self._send(409, json.dumps({"error": "not_ready", "reply": "Copilot is not ready (install or sign-in)."}))
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            prompt = body.get("prompt", "").strip()
            lang = body.get("lang") if body.get("lang") in LANGS else "en"
        except (ValueError, AttributeError):
            return self._send(400, "{}")
        if not prompt:
            return self._send(400, "{}")
        try:
            if self.path == "/api/recommend":
                result = ticket_lookup.recommend(prompt, load_index())
            else:
                handler = ticket_lookup.categorize if self.path == "/api/categorize" else ticket_lookup.lookup
                result = handler(prompt, load_index(), run_copilot)
        except Exception as e:
            return self._send(500, json.dumps({"error": "generic", "reply": str(e)}))
        self._send(200, json.dumps(result))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Tickets loaded: {len(load_index().tickets)}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"SIP Tickets Miner is running at {url} (Ctrl+C to quit)")
    if not COPILOT:
        print("Copilot CLI is not installed. Confirm the installation on the page in your browser.")
    elif not is_logged_in():
        print("Copilot CLI is not signed in. Sign in on the page in your browser.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with state_lock:
            procs = [install.get("proc"), login.get("proc")]
        for p in procs:
            if p:
                kill_tree(p)
