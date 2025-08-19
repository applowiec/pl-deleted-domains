#!/usr/bin/env python3
import os
import re
import datetime as dt
from typing import List, Tuple

import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None  # jeśli brak urllib3.retry na runnerze

DNS_URL = "https://dns.pl/deleted_domains.txt"
DATA_DIR = "data"
DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.pl$", re.IGNORECASE)

def fetch_url(url: str) -> List[str]:
    s = requests.Session()
    if Retry is not None:
        retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
    resp = s.get(url, timeout=60)
    print("HTTP status:", resp.status_code)
    resp.raise_for_status()
    return resp.text.splitlines()

def parse_lines(lines: List[str]) -> Tuple[str, List[str]]:
    """Zwraca timestamp z pliku źródłowego i listę domen .pl (po jednej na linię)."""
    ts = None
    domains: List[str] = []

    print("=== PODGLAD PIERWSZYCH LINII ===")
    for i, line in enumerate(lines[:20], start=1):
        print(f"{i:02d}: {line}")
    print("=== KONIEC PODGLADU ===")

    for line in (l.strip() for l in lines):
        if not line:
            continue
        if ts is None and re.match(r"\d{4}-\d{2}-\d{2}", line):
            ts = line  # np. "2025-08-19 08:11:02 MEST"
            continue
        if DOMAIN_RE.match(line):
            domains.append(line.lower())

    if not ts:
        ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return ts, domains

def save_files(ts: str, domains: List[str]) -> None:
    """Zapisuje raport dnia do data/YYYY-MM-DD.md oraz listę do data/YYYY-MM-DD.txt"""
    now = dt.datetime.now()
    day_iso = now.strftime("%Y-%m-%d")     # nazwa pliku
    day_pl  = now.strftime("%d.%m.%Y")     # do nagłówków

    # z ts bierzemy sam czas (HH:MM:SS)
    time_part = ts.split()[1] if " " in ts else ts

    md_path  = os.path.join(DATA_DIR, f"{day_iso}.md")
    txt_path = os.path.join(DATA_DIR, f"{day_iso}.txt")

    count = len(domains)

    h1 = f"W dniu {day_pl} usunięto {count} domen z rejestru DNS.pl"
    h2 = f"Usunięcie nastąpiło w dniu {day_pl} o godzinie {time_part}"

    with open(md_path, "w", encoding="utf-8") as md:
        md.write(f"# {h1}\n\n")
        md.write(f"## {h2}\n\n")
        for d in domains:
            md.write(f"- {d}\n")

    with open(txt_path, "w", encoding="utf-8") as txt:
        for d in domains:
            txt.write(d + "\n")

    print(f"Rozpoznany timestamp źródła: '{ts}'")
    print(f"Liczba domen po filtrze: {count}")
    print(f"Zapisano: {md_path} ({count} domen), {txt_path}")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    lines = fetch_url(DNS_URL)
    ts, domains = parse_lines(lines)
    save_files(ts, domains)

if __name__ == "__main__":
    main()
