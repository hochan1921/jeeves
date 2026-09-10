#!/usr/bin/env python3
"""画面を出す。data/*.md への PUT だけ受ける。

python3 -m http.server は書き込みを受けないので、その分だけを足したもの。
台帳は data/*.md ひとつきり。画面は写しを持たず、直した内容をここへ書き戻す。
"""
import hashlib, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


def tag(b):
    """中身そのものの札。これが変わっていたら、誰かが先に書いている。"""
    return '"%s"' % hashlib.sha1(b).hexdigest()[:16]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        # 画面も管理票も、古いものを掴ませない
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def writable(self):
        """data/ 直下の .md だけ。それ以外はどう頼まれても書かない。"""
        p = os.path.abspath(self.translate_path(self.path.split("?")[0]))
        return p if os.path.dirname(p) == DATA and p.endswith(".md") else None

    def do_GET(self):
        p = self.writable()
        if not p or not os.path.isfile(p):
            return super().do_GET()
        body = open(p, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", tag(body))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        # 断る場合も本文は読み切る。読まずに閉じると相手には通信断に見える
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        p = self.writable()
        if not p:
            # 理由の一行は latin-1 しか通らないので、日本語は本文のほうへ
            return self.send_error(403, "Forbidden", "data/*.md にだけ書けます")
        now = open(p, "rb").read() if os.path.isfile(p) else b""
        want = self.headers.get("If-Match")
        if want and want != tag(now):
            return self.send_error(409, "Conflict", "先に書き換えられています")
        tmp = p + ".tmp"
        with open(tmp, "wb") as f:
            f.write(body)
        os.replace(tmp, p)  # 途中で切れた管理票を残さない
        self.send_response(204)
        self.send_header("ETag", tag(body))
        self.end_headers()


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    print(f"管理票 http://localhost:{PORT}  （同じ Wi-Fi の端末からも書き換えられます）")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
