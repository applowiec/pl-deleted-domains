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

# Prosty parser — plik z NASK zwykle zawiera datę / timestamp i listę domen (po jednej w linii).
# Robimy parser: odrzucamy puste linie i wszystko co nie wygląda na domenę .pl
DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*\.pl$", re.IGNORECASE)

def session_with_retry() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "pl-deleted-domains/1.0 (+https://github.com/applowiec/pl-deleted-domains)",
        "Accept": "text/plain,*/*;q=0.1",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    if Retry is not None:
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
    return s

def fetch_deleted_domains() -> Tuple[str, List[str], str]:
    """Zwraca (data_iso, lista_domen, source_timestamp)
       data_iso – YYYY-MM-DD (wg strefy Europe/Warsaw)
       source_timestamp – ewentualny timestamp z nagłówka źródła (gdy uda się wykryć)"""
    s = session_with_retry()
    resp = s.get(DNS_URL, timeout=20)
    if resp.status_code != 200 or not resp.text.strip():
        raise RuntimeError(f"HTTP {resp.status_code} przy pobieraniu {DNS_URL}")

    raw = resp.text.splitlines()
    lines = [ln.strip() for ln in raw if ln.strip()]

    # Spróbuj wyłuskać linię z datą/timestampem (zazwyczaj pierwsze 1-2 linie to data/czas).
    # Jeśli nic sensownego – użyj „dzisiejszej” daty wg Europe/Warsaw.
    source_ts = ""
    possible_header = lines[0] if lines else ""
    # Przyjmijmy, że jeśli linia zaczyna się od YYYY-MM-DD – to to jest data/ts.
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:\b.*)?$", possible_header)
    if m:
        source_ts = possible_header
        date_iso = m.group(1)
        start_idx = 1  # domeny zaczynają się od następnej linii
    else:
        # Nie udało się wyczytać daty z nagłówka – bierz dzisiejszą (Warszawa)
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo("Europe/Warsaw")
        except Exception:
            # fallback: bez zoneinfo
            class _TZ(dt.tzinfo):
                def utcoffset(self, d): return dt.timedelta(hours=2)  # przybliżenie
            tz = _TZ()
        date_iso = dt.datetime.now(tz=tz).strftime("%Y-%m-%d")
        start_idx = 0

    # Przefiltruj linie domen
    domains = [ln for ln in lines[start_idx:] if DOMAIN_RE.match(ln)]
    # Usuń duplikaty zachowując kolejność (na wszelki)
    seen = set()
    uniq = []
    for d in domains:
        if d.lower() not in seen:
            uniq.append(d)
            seen.add(d.lower())
    return date_iso, uniq, source_ts

def write_markdown(date_iso: str, domains: List[str], source_ts: str) -> str:
    """Zapisuje data/YYYY-MM-DD.md. Zwraca ścieżkę pliku."""
    os.makedirs(DATA_DIR, exist_ok=True)
    md_path = os.path.join(DATA_DIR, f"{date_iso}.md")

    header = f"# {date_iso} — usunięto {len(domains)} domen\n\n"
    # Sekcja z „datą ze źródła” — jeżeli wykryliśmy, dodajemy JAKO TEKST, bez listy punktowanej.
    extra = ""
    if source_ts and not DOMAIN_RE.match(source_ts):
        extra = f"{source_ts}\n\n"

    # Lista punktowana tylko dla domen:
    bullet = "\n".join(f"- {d}" for d in domains)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(header)
        if extra:
            f.write(extra)
        f.write(bullet)
        f.write("\n")

    # Dodatkowo prosta wersja TXT:
    txt_path = os.path.join(DATA_DIR, f"{date_iso}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(domains) + "\n")

    return md_path

def main() -> int:
    try:
        date_iso, domains, source_ts = fetch_deleted_domains()
    except Exception as e:
        # Zgłoś błąd jasno – Actions pokaże to w logu
        print(f"[ERROR] Nie udało się pobrać listy: {e}", file=sys.stderr)
        return 2

    if not domains:
        print(f"[WARN] Brak domen do zapisania dla {date_iso}.")
        # Nie uznajemy tego za błąd krytyczny – po prostu kończymy bez zmian.
        return 0

    path = write_markdown(date_iso, domains, source_ts)
    print(f"[OK] Zapisano {len(domains)} domen do: {path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
