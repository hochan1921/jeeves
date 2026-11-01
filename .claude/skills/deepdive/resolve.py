"""Google ニュースのリンクを、元記事の URL にほどいて 1 行で出す。ほどけなければ何も出さない。

中継ページは飛び先を JavaScript で決めるので、WebFetch では先へ進めない。
使い方: python3 -I .claude/skills/deepdive/resolve.py <news.google.com/rss/articles/… の URL>
"""
import json, re, sys, urllib.parse, urllib.request

PREFIX = "https://news.google.com/rss/articles/"
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def resolve(url):
    page = get(url)
    attrs = dict(re.findall(r'data-n-a-(id|ts|sg)="([^"]+)"', page))
    if len(attrs) < 3:
        return None
    inner = ["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                             None, None, None, None, None, 0, 1],
                            "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
             attrs["id"], int(attrs["ts"]), attrs["sg"]]
    req = json.dumps([[["Fbv4je", json.dumps(inner), None, "generic"]]])
    body = urllib.parse.urlencode({"f.req": req}).encode()
    reply = get("https://news.google.com/_/DotsSplashUi/data/batchexecute", body)
    m = re.search(r'https?://[^"\\]+', reply)
    return m.group(0) if m else None


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].startswith(PREFIX):
        try:
            found = resolve(sys.argv[1])
        except Exception:
            found = None
        if found:
            print(found)
