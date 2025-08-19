#!/usr/bin/env python3
import os, re, sys, time
from datetime import datetime, timezone, timedelta
from typing import List

import requests
try:
    # solidne retry na 429/5xx
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter
    HAVE_RETRY = True
except Exception:
    HAVE_RETRY = False

DNS_URL  = "https://dns.pl/deleted_domains.txt"
DATA_DIR = "data"

# domena .pl – prosto i bezpiecznie
DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-\.]*\.pl$", re.IGNORECASE)
# linia z datą źródła (np. "2025-08-19 08:11:02 MEST")
DATE_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\S+$")

def session_with_retries() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "pl-deleted-domains/1.0 (+https://github.com/applowiec/pl-deleted-domains)"
    })
    if HAVE_RETRY:
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

def fetch_text(url: str) -> str:
    sess = session_with_retries()
    resp = sess.get(url, timeout=30)
    # diagnostyka do logów Actions
    print(f"HTTP status: {resp.status_code}")
    preview = resp.text.splitlines()[:20]
    print("=== PODGLĄD PIERWSZYCH LINII ===")
    for i, ln in enumerate(preview, 1):
        print(f"{i:02d}: {ln}")
    print("=== KONIEC PODGLĄDU ===")
    resp.raise_for_status()
    return resp.text

def parse_domains(raw: str) -> tuple[str, List[str]]:
    """
    Zwraca (timestamp_ze_źródła, lista_domen)
    - bierze pierwszą linię wyglądającą na timestamp (DATE_LINE_RE)
    - wszystkie linie wyglądające na domenę .pl (DOMAIN_RE)
    """
    src_ts = ""
    domains: List[str] = []
    seen = set()

    for ln in (l.strip() for l in raw.splitlines()):
        if not ln:
            continue
        if not src_ts and DATE_LINE_RE.match(ln):
            src_ts = ln
            continue
        if DOMAIN_RE.match(ln):
            low = ln.lower()
            if low not in seen:
                seen.add(low)
                domains.append(ln)

    return src_ts, domains

def write_outputs(today: str, src_ts: str, domains: List[str]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    # TXT – każda domena w osobnej linii
    txt_path = os.path.join(DATA_DIR, f"{today}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(domains) + ("\n" if domains else ""))

    # MD – H1 + H2 z timestampem źródła + lista punktowana domen
    md_path  = os.path.join(DATA_DIR, f"{today}.md")
    title    = f"{today} — usunięto {len(domains)} domen"
    now_str  = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"## {now_str}\n\n")
        if src_ts:
            f.write(f"{src_ts}\n\n")  # zwykła linia – bez bulletu
        for d in domains:
            f.write(f"- {d}\n")

    print(f"Zapisano: {md_path} ({len(domains)} domen), {txt_path}")

def main() -> None:
    # data w strefie PL (CE(S)T)
    # GitHub runner ma UTC – ale nazwa pliku chcemy w YYYY-MM-DD w PL
    pl = timezone(timedelta(hours=2))  # latem CEST; zimą możesz zmienić na 1h
    today = datetime.now(pl).strftime("%Y-%m-%d")

    raw = fetch_text(DNS_URL)
    src_ts, domains = parse_domains(raw)
    print(f"Rozpoznany timestamp źródła: '{src_ts}'")
    print(f"Liczba domen po filtrze: {len(domains)}")

    write_outputs(today, src_ts, domains)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("BŁĄD:", repr(e))
        sys.exit(1)
