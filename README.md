# 100-Bagger Screener

Ein monatlich aktualisierter Screener für US-Aktien unter 500 Mio. USD Market Cap, basierend auf den Mustern aus Tony's Studie *An Analysis of 100-baggers*.

## Setup

```bash
python -m venv venv
source venv/Scripts/activate   # Windows bash (Linux/macOS: venv/bin/activate)
pip install -r pipeline/requirements.txt
```

## Pipeline ausführen (monatlich)

```bash
venv/Scripts/python pipeline/run_pipeline.py
```

Dauer: ca. 30–60 Minuten für ~6.800 US-Ticker.

Output:
- `docs/data.json` — Ergebnis-Datenfile für das Dashboard
- `pipeline/pipeline_log.txt` — Protokoll (passed / filtered / skipped pro Ticker)

## Dashboard ansehen

Lokal starten:

```bash
venv/Scripts/python -m http.server 8080 --directory docs
```

Dann im Browser: http://localhost:8080

Alternativ: Ordner `docs/` auf GitHub Pages, Netlify Drop oder einem anderen statischen Host deployen.

## Tests

```bash
venv/Scripts/python -m pytest pipeline/tests/ -v
```

Aktueller Stand: 38 Tests.

## Kriterien (Kurzfassung)

**Hard Filter (Titel muss alle erfüllen):**
- Market Cap < 500 Mio. USD
- MRQ EPS > 0
- Tagesvolumen > 100.000 USD
- ≥ 8 Quartale Berichts-Historie
- US-Listing (NYSE / NASDAQ / AMEX)

**Scoring (max 100 Punkte):**
- EPS-Wachstumsbeschleunigung (35)
- PEG-Ratio (25)
- Market Cap Smallness (15)
- Umsatzwachstum (15)
- Turnaround-Bonus (10)

## Online-Hosting

Das Dashboard läuft als statische Seite auf **https://thblees.github.io/100bagger/** und wird monatlich automatisch per GitHub Actions aktualisiert. Setup-Anleitung: [GITHUB_SETUP.md](GITHUB_SETUP.md).

## Dokumentation

- Design-Spec: [docs/superpowers/specs/2026-04-21-100bagger-screener-design.md](docs/superpowers/specs/2026-04-21-100bagger-screener-design.md)
- Implementation Plan: [docs/superpowers/plans/2026-04-21-100bagger-screener.md](docs/superpowers/plans/2026-04-21-100bagger-screener.md)
- Originalstudie: [100-baggers.md](100-baggers.md)

## Datenquelle

- Ticker-Universum: NASDAQ Trader FTP (nasdaqlisted.txt, otherlisted.txt)
- Fundamentals: yfinance 1.3.0 (`Ticker.info`, `Ticker.get_earnings_dates`, `Ticker.quarterly_income_stmt`)

## Disclaimer

Dieser Screener ist kein Investment-Ratschlag. Die Kriterien basieren auf der öffentlichen Studie von Tony (tsanalysis.com) und sind eine heuristische Übersetzung in konkrete Filter. Vergangene Muster garantieren keine zukünftige Performance.
