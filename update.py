#!/usr/bin/env python3
import os, time, requests, sys
from pathlib import Path
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

os.environ["TZ"] = "Europe/Warsaw"
try:
    time.tzset()
except Exception:
    pass

URL = "https://dns.pl/deleted_domains.txt"
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

today = datetime.now().strftime("%Y-%m-%d")
raw_txt = DATA_DIR / f"{today}.txt"
md_file = DATA_DIR / f"{today}.md"

session = requests.Session()
session.headers.update({
    "User-Agent": "pl-deleted-domains (+https://github.com/applowiec/pl-deleted-domains) contact: actions@users.noreply.github.com",
    "Accept": "text/plain,*/*;q=0.1",
    "Connection": "close",
})

retry = Retry(
    total=6,
    connect=6,
    read=6,
    backoff_factor=1.0,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    raise_on_status=False,
)
session.mount("https://", HTTPAdapter(max_retries=retry))
session.mount("http://", HTTPAdapter(max_retries=retry))

try:
    resp = session.get(URL, timeout=30)
except Exception as e:
    print(f"[ERR] request error: {e}", file=sys.stderr)
    sys.exit(1)

print(f"[INFO] GET {URL} -> HTTP {resp.status_code}, {len(resp.content)} bytes")

if resp.status_code in (401, 403, 429, 503):
    print(f"[WARN] Server refused (status {resp.status_code}). Exiting without changes.")
    sys.exit(0)

resp.raise_for_status()

text = resp.text.strip("\n\r")
if not text:
    print("[WARN] Empty response body; exiting without changes.")
    sys.exit(0)

lines = text.splitlines()
if not lines:
    print("[WARN] No lines in response; exiting without changes.")
    sys.exit(0)

src_ts = lines[0].strip()
domains = [ln.strip() for ln in lines[1:] if ln.strip()]

raw_txt.write_text(("\n".join(domains) + "\n") if domains else "", encoding="utf-8")

count = len(domains)
now_str = time.strftime("%Y-%m-%d %H:%M:%S %Z")

with md_file.open("w", encoding="utf-8") as f:
    f.write(f"## {today} — usunięto {count} domen\n\n")
    f.write(f"**{now_str}**\n")
    if src_ts:
        f.write(f"_Źródło DNS.pl: {src_ts}_\n")
    f.write("\n")
    for d in domains:
        f.write(f"- {d}\n")

print(f"[OK] saved: {raw_txt} and {md_file} (count={count})")
