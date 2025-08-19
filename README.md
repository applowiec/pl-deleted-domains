# 📉 pl-deleted-domains

To repozytorium codziennie automatycznie publikuje listę domen usuniętych z rejestru **.pl** (zarządzanego przez [NASK / DNS.pl](https://dns.pl)).  
Dane są pobierane ze strony [dns.pl/deleted_domains.txt](https://dns.pl/deleted_domains.txt) i zapisywane w formacie Markdown (`.md`) oraz tekstowym (`.txt`).  
Proces jest w pełni zautomatyzowany przy użyciu **GitHub Actions** – aktualizacja uruchamia się codziennie o godzinie **10:00 czasu polskiego (08:00 UTC)**.

---

## 🔗 Najnowszy raport

👉 [Raport z dnia 2025-08-19](data/2025-08-19.md) — *usunięto 2312 domen*  

---

## 📂 Archiwum

Pełna historia usuniętych domen znajduje się w folderze [`/data`](data).

Każdy plik ma nazwę w formacie `YYYY-MM-DD.md`, np.:  

- [2025-08-19](data/2025-08-19.md)  
- 2025-08-20  
- 2025-08-21  
- …  

---

## ⚙️ Format danych

Pliki generowane są w dwóch formatach:  

- **Markdown (`.md`)** — z nagłówkiem, liczbą usuniętych domen i listą w punktach  
- **TXT (`.txt`)** — czysta lista domen, jedna domena w wierszu  

---

## 📊 Przykład wpisu

```markdown
2025-08-19 — usunięto 2312 domen

2025-08-19 08:11:02 MEST

- 0.edu.pl
- 123leasing.pl
- 1982.pl
- 1by1.com.pl
- …
