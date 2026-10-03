#!/usr/bin/env python3
"""画面を出す。data/*.md への PUT だけ受ける。

python3 -m http.server は書き込みを受けないので、その分だけを足したもの。
台帳は data/*.md ひとつきり。画面は写しを持たず、直した内容をここへ書き戻す。
本人だけのもの（memory.md / talk.md）は、読ませも書かせもしない。
"""
import hashlib, os, socket, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
PRIVATE = ("memory.md", "talk.md")  # 画面は読まない。同じ回線の人にも見せない


def private(p):
    """本人だけのものか。Mac は名前の大文字小文字を区別しないので、こちらも区別しない。"""
    p = os.path.realpath(p).casefold()
    return any(p == os.path.realpath(os.path.join(DATA, n)).casefold() for n in PRIVATE)


def tag(b):
    """中身そのものの札。これが変わっていたら、誰かが先に書いている。"""
    return '"%s"' % hashlib.sha1(b).hexdigest()[:16]


def taken(port):
    """もう誰かが応答している番号か。127.0.0.1 だけで待ち受ける相手には、OS が断らずに重ねてしまう。"""
    try:
        socket.create_connection(("localhost", port), timeout=1).close()
        return True
    except OSError:
        return False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        # 画面も data/ の中身も、古いものを掴ませない
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def writable(self):
        """data/ 直下の .md だけ。本人だけのものは除く。それ以外はどう頼まれても書かない。"""
        p = os.path.abspath(self.translate_path(self.path.split("?")[0]))
        return p if os.path.dirname(p) == DATA and p.endswith(".md") and not private(p) else None

    def send_head(self):
        # 読むほうも同じ。名前の書き方を変えて頼まれても出さない
        if private(self.translate_path(self.path)):
            self.send_error(404)
            return None
        return super().send_head()

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
        os.replace(tmp, p)  # 途中で切れた台帳を残さない
        self.send_response(204)
        self.send_header("ETag", tag(body))
        self.end_headers()


if __name__ == "__main__":
    if taken(PORT):
        sys.exit(f"{PORT} 番はほかのアプリが使っています。python3 server.py {PORT + 1} のように番号を変えてください")
    os.makedirs(DATA, exist_ok=True)
    print(f"ダッシュボード http://localhost:{PORT}  （同じ Wi-Fi の端末からも書き換えられます）")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
