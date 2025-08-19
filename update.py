#!/usr/bin/env python3
import os
import re
import sys
import time
import datetime as dt
from typing import List, Tuple

import requests
from requests.adapters import HTTPAdapter
try:
    # Retry dla 429/5xx
    from urllib3.util.retry import Retry
except Exception:
    Retry = None  # będzie bez retry, ale spróbujemy

DNS_URL = "https://dns.pl/deleted_domains.txt"
DATA_DIR = "data"

# Prosty parser – plik z NASK zwykle zawiera datę / timestamp i listę domen (po jednej w linii).
# Robimy parser: odrzucamy puste linie i wszystko co nie wygląda na domenę .pl
DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\.\-\_]*\.pl$", re.IGNORECASE)

def fetch_url(url: str) -> List[str]:
    """Pobiera dane z podanego URL z retry."""
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
    """Zwraca timestamp źródła oraz listę domen .pl"""
    ts = None
    domains: List[str] = []
    print("=== PODGLAD PIERWSZYCH LINII ===")
    for i, line in enumerate(lines[:20], start=1):
        print(f"{i:02d}: {line}")
    print("=== KONIEC PODGLADU ===")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Pierwsza linia to zwykle timestamp
        if ts is None and re.match(r"\d{4}-\d{2}-\d{2}", line):
            ts = line
            continue
        if DOMAIN_RE.match(line):
            domains.append(line.lower())
    if not ts:
        ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return ts, domains

def save_files(ts: str, domains: List[str]) -> None:
    """Zapisuje listę domen do pliku .txt i .md"""
    d = dt.datetime.now()
    date_str = d.strftime("%Y-%m-%d")
    md_file = os.path.join(DATA_DIR, f"{date_str}.md")
    txt_file = os.path.join(DATA_DIR, f"{date_str}.txt")

    # Formatowanie polskich dat i godzin
    date_pl = d.strftime("%d.%m.%Y")
    time_pl = ts.split(" ")[1] if " " in ts else ts

    cnt = len(domains)

    # H1 / H2 wg Twojej specyfikacji
    h1 = f"W dniu {date_pl} usunięto {cnt} domen z rejestru DNS.pl"
    h2 = f"Usunięcie nastąpiło w dniu {date_pl} o godzinie {time_pl}"

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# {h1}\n\n")
        f.write(f"## {h2}\n\n")
        for dom in domains:
            f.write(f"- {dom}\n")

    with open(txt_file, "w", encoding="utf-8") as f:
        for dom in domains:
            f.write(dom + "\n")

    print(f"Rozpoznany timestamp źródła: '{ts}'")
    print(f"Liczba domen po filtrze: {cnt}")
    print(f"Zapisano: {md_file} ({cnt} domen), {txt_file}")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    lines = fetch_url(DNS_URL)
    ts, domains = parse_lines(lines)
    save_files(ts, domains)

if __name__ == "__main__":
    main()
