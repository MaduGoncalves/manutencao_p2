import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

K = 600000
L = threading.Lock()
B = {"p": [0, 0], "f": [0, 0], "t": K, "r": False, "s": 0}
Z = Path(__file__).parent / "static"
X = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def w():
    return int(time.time() * 1000)


def g():
    if B["r"]:
        v = B["t"] - (w() - B["s"])
        if v <= 0:
            B["t"] = 0
            B["r"] = False
            return 0
        return v
    return B["t"]


def o():
    return {"p": list(B["p"]), "f": list(B["f"]), "t": g(), "r": B["r"]}


def q(a):
    c = a[0] if a else ""
    try:
        if c in ("p", "f"):
            i, d = int(a[1]), int(a[2])
            if i in (0, 1):
                B[c][i] = max(0, B[c][i] + d)
        elif c == "k":
            if not B["r"] and g() > 0:
                B["s"] = w()
                B["r"] = True
        elif c == "l":
            B["t"] = g()
            B["r"] = False
        elif c == "m":
            v = int(a[1])
            if not B["r"] and v >= 0:
                B["t"] = v * 1000
        elif c == "n":
            B["p"] = [0, 0]
            B["f"] = [0, 0]
            B["t"] = K
            B["r"] = False
            B["s"] = 0
    except (IndexError, ValueError):
        pass


class H(BaseHTTPRequestHandler):
    def y(self, code, body, tipo):
        self.send_response(code)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def a(self, cmd):
        u = self.path.split("?")[0]
        if u.startswith("/api/q"):
            with L:
                if cmd:
                    q([s for s in u[6:].split("/") if s])
                r = o()
            return self.y(200, json.dumps(r).encode(), "application/json")
        if cmd:
            return self.y(404, b"", "text/plain")
        n = "index.html" if u == "/" else u.lstrip("/")
        f = (Z / n).resolve()
        if Z.resolve() in f.parents and f.is_file():
            return self.y(200, f.read_bytes(), X.get(f.suffix, "text/plain"))
        return self.y(404, b"nao encontrado", "text/plain")

    def do_GET(self):
        self.a(False)

    def do_POST(self):
        self.a(True)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Rodando em http://localhost:8000")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
