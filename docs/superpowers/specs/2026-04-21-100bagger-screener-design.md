# 100-Bagger Screener — Design

**Datum:** 2026-04-21
**Status:** Design-Spec, wartet auf Nutzer-Review
**Basis:** *An Analysis of 100-baggers* von Tony (tsanalysis.com)

## Ziel

Ein statisches Web-Dashboard, das US-Aktien mit Marktkapitalisierung unter 500 Mio. USD auf die in Tony's Studie identifizierten Muster potenzieller 100-Bagger hin untersucht und die besten 50 Kandidaten sortiert anzeigt. Monatlicher manueller Datenzug via Python-Skript, Auslieferung als einzelne HTML-Datei plus JSON-Datenfile.

## Nicht-Ziele

- Kein Live-/Intraday-Dashboard (monatliche Aktualisierung genügt).
- Kein Backtest/keine Performance-Analyse der historischen Treffer.
- Keine Empfehlung zu Einstiegs-/Ausstiegskursen.
- Keine europäischen/globalen Aktien (nur US-Listings).
- Kein User-Login, kein Mehrbenutzer-Betrieb.

## Studien-Ableitung

Tony identifiziert fünf wiederkehrende Muster in den von ihm analysierten 100-Baggern:

1. Kleine Market Cap beim Einstieg — praktisch universell.
2. Beschleunigende yoy-EPS-Wachstumsraten (nicht nur stabil, sondern sequentiell steigend).
3. PE-Expansion, die mit der Beschleunigung einhergeht.
4. PEG-Ratio bleibt unter 1, idealerweise unter 0,5.
5. Häufig Turnaround-Situationen: vergessene Titel auf dem Weg zurück zur Profitabilität.

## Architektur

Zwei klar getrennte Units:

**Unit A — Data Pipeline (`pipeline/`)**
- Python-Skript, einmal pro Monat manuell ausgeführt.
- Eingabe: Ticker-Liste aller US-gelisteten Aktien (NYSE/NASDAQ/AMEX).
- Datenquelle: `yfinance` (kostenlos, ausreichend für monatlichen Zug).
- Ausgabe: `dashboard/data.json` mit allen Kriterien und Scores pro Titel.

**Unit B — Dashboard (`dashboard/`)**
- Statische HTML-Datei (`index.html`) mit Vanilla JS, Tailwind via CDN.
- Lädt `data.json` beim Start, rendert Tabelle mit Sortier-/Filter-Funktionen.
- Deploybar als GitHub Pages, Netlify Drop oder lokale Datei.

Kommunikation über `data.json` — keine Build-Schritte, keine API, kein Backend.

## Hard Filter (Knockout)

Ein Titel muss ALLE folgenden Kriterien erfüllen, sonst fliegt er raus:

| # | Kriterium | Schwellwert | Begründung |
|---|-----------|-------------|------------|
| 1 | Market Cap | < 500 Mio. USD | Studie: "Beginning with small market caps was practically universal" |
| 2 | MRQ EPS (letztes Quartal) | > 0 | Profitabel oder am Turnaround-Inflection-Point |
| 3 | Durchschn. Tagesvolumen (30 Tage) | > 100.000 USD | Handelbarkeit |
| 4 | Quartalsberichts-Historie | ≥ 8 Quartale | Nötig für Berechnung der Wachstumsbeschleunigung |
| 5 | Listing | NYSE, NASDAQ oder AMEX | Kein OTC-Pink |

**Hinweis zu Filter 2:** Absichtlich MRQ statt TTM, damit Turnaround-Kandidaten genau am Inflection Point nicht ausgeschlossen werden (Tony: "wait until sustainable improvement in fundamentals is imminent"). PEG und Scoring werden auf MRQ-annualisiert (MRQ × 4) umgestellt, wenn TTM negativ.

## Scoring (max 100 Punkte)

### 1. EPS-Wachstumsbeschleunigung (max 35 Punkte)

Stärkster Indikator in der Studie. Gemessen an den yoy-Wachstumsraten der letzten 4 Quartale.

Seien `g_0, g_{-1}, g_{-2}, g_{-3}` die yoy-EPS-Wachstumsraten der letzten vier Quartale (Q0 = jüngstes Quartal). Zwischen diesen vier Werten gibt es drei Vergleichspaare. Ein Paar zählt als "Schritt aufwärts", wenn `g_i > g_{i-1}`.

Regeln werden top-down evaluiert, erste zutreffende Regel gewinnt:

| Regel | Punkte |
|-------|--------|
| 3 Schritte aufwärts (perfekte Leiter: `g_0 > g_{-1} > g_{-2} > g_{-3}`) | 35 |
| 2 Schritte aufwärts UND `g_0 > g_{-3}` (klarer Aufwärtstrend mit einer Delle) | 25 |
| 2 Schritte aufwärts ohne klaren Gesamttrend | 18 |
| 1 Schritt aufwärts UND Maximalwert von `g` liegt in `g_0` oder `g_{-1}` (jüngeres Wachstum ist höher) | 10 |
| sonst | 0 |

### 2. PEG-Ratio (max 25 Punkte)

**Berechnung:**

1. **Effective EPS:** Falls `TTM_EPS > 0`, nutze `TTM_EPS`. Falls `TTM_EPS ≤ 0` (Turnaround-Fall), nutze `MRQ_EPS × 4` (Proxy-Annualisierung). `MRQ_EPS > 0` ist durch Hard Filter 2 garantiert.
2. **Effective PE:** `current_price / effective_EPS`.
3. **Growth Rate:** `g_0` (yoy-Wachstumsrate des letzten Quartals, als Dezimalzahl, z.B. 0.25 für 25 %).
4. **PEG:** `effective_PE / (g_0 × 100)`. Falls `g_0 ≤ 0`, PEG wird als "negativ" behandelt (0 Punkte).

| PEG | Punkte |
|-----|--------|
| 0 < PEG < 0,5 | 25 |
| 0,5 ≤ PEG < 1,0 | 15 |
| 1,0 ≤ PEG < 1,5 | 5 |
| PEG ≥ 1,5 oder negativ | 0 |

### 3. Market Cap Smallness (max 15 Punkte)

Je kleiner die Ausgangsbasis, desto mehr Raum für 100-fach.

| Market Cap | Punkte |
|-----------|--------|
| < 100 Mio. USD | 15 |
| < 250 Mio. USD | 10 |
| < 500 Mio. USD | 5 |

### 4. Umsatzwachstum (max 15 Punkte)

Stützt die Qualität des EPS-Wachstums (kein reines Margen-Feuerwerk). Gemessen als yoy-Umsatzwachstum der letzten 4 Quartale (Durchschnitt).

| Durchschn. yoy-Umsatzwachstum | Punkte |
|-------------------------------|--------|
| > 30 % | 15 |
| > 15 % | 8 |
| > 5 % | 3 |
| ≤ 5 % | 0 |

### 5. Turnaround-Signal (max 10 Bonuspunkte)

| Bedingung | Punkte |
|-----------|--------|
| Vor ≥ 2 Jahren (Q−8 oder früher) EPS ≤ 0, aktuell EPS > 0 UND Kriterium 1 ≥ 20 Punkte | 10 |
| sonst | 0 |

### Gesamtscore

Summe der Einzelscores, max. 100. Ergebnisliste sortiert absteigend nach Gesamtscore. Anzeige: Top 50.

## Dashboard-Funktionen

**Haupttabelle** (Top 50 nach Score):
- Spalten: Rang, Ticker, Firmenname, Sektor, Market Cap, Score (fett), Einzelscores (1–5), PEG, TTM-PE, yoy-EPS-Wachstum letztes Quartal, Link zu Yahoo-Finance-Profil.
- Jede Spalte klickbar sortierbar.

**Filter-Leiste über der Tabelle:**
- Sektor-Dropdown (Multi-Select).
- Market-Cap-Schieberegler (unterer/oberer Rand).
- Min-Score-Schieberegler.
- Suche nach Ticker/Name.

**Detail-Ansicht** (Klick auf Zeile):
- Modal mit allen Rohdaten: EPS-Historie als Mini-Tabelle, Umsatz-Historie, alle Score-Komponenten mit Kurz-Erklärung warum wie viele Punkte.

**Header:**
- Titel, Stand-Datum des Datenzugs, Anzahl gescreenter Titel, Anzahl nach Hard Filter, Erklär-Button "Wie funktioniert der Screener?" (Modal mit Kurzfassung der 5 Kriterien aus der Studie).

## Datenmodell (`data.json`)

```json
{
  "generated_at": "2026-04-21",
  "universe_size": 3247,
  "passed_hard_filter": 412,
  "top_results": [
    {
      "ticker": "XYZ",
      "name": "Example Corp",
      "sector": "Technology",
      "market_cap_usd": 187_500_000,
      "avg_daily_volume_usd": 1_240_000,
      "ttm_eps": 0.42,
      "mrq_eps": 0.14,
      "ttm_pe": 23.8,
      "peg": 0.47,
      "yoy_eps_growth_rates": [0.05, 0.18, 0.34, 0.61],
      "yoy_revenue_growth_avg": 0.27,
      "eps_accel_score": 35,
      "peg_score": 25,
      "mcap_score": 10,
      "revenue_score": 8,
      "turnaround_score": 0,
      "total_score": 78
    }
  ]
}
```

## Fehlerbehandlung

**Data Pipeline:**
- Fehlende Felder bei einem Ticker → Titel wird übersprungen, Logging-Eintrag `skipped: <ticker> (missing <feld>)`.
- API-Rate-Limit (`yfinance` über `requests`): Retry mit exponential backoff, max. 3 Versuche.
- Abbruch der Pipeline → Skript bricht hart ab, letztes gutes `data.json` bleibt.
- Am Ende schreibt die Pipeline in `data.json` plus `pipeline_log.txt` mit Anzahl gescreenter, übersprungener und gefilterter Titel.

**Dashboard:**
- `data.json` nicht erreichbar → sichtbare Fehlermeldung "Datenfile nicht gefunden".
- Feld fehlt in Zeile → "n/a" anzeigen, Score-Berechnung hat im Skript bereits 0 eingesetzt.

## Testing

**Pipeline:**
- Unit-Tests für die 5 Scoring-Funktionen mit handgebauten Fixture-Daten (jeweils Perfekte-Leiter-Fall, Abwärtsfall, Grenzwerte).
- Unit-Test für Hard-Filter-Logik.
- Unit-Test für TTM→MRQ-Fallback bei negativem TTM-EPS.
- Ein Integrations-Test: Pipeline auf 10 bekannte Tickern, geprüft wird nur dass `data.json` valide ist und die erwarteten Felder enthält.

**Dashboard:**
- Manueller Smoke-Test: `data.json` mit 3 Titeln laden, alle Features durchklicken (Sortierung, Filter, Detail-Modal).
- Kein automatisiertes Frontend-Test-Setup — Komplexität zu niedrig, Aufwand unverhältnismäßig.

## Projekt-Struktur

```
Kurs 100bagger/
├── 100-baggers.md              (Originalstudie, existiert)
├── 100-baggers.pdf             (existiert)
├── docs/superpowers/specs/
│   └── 2026-04-21-100bagger-screener-design.md  (dieses Dokument)
├── pipeline/
│   ├── run_pipeline.py         (Main-Skript)
│   ├── fetch.py                (yfinance-Aufrufe, Ticker-Universum)
│   ├── scoring.py              (die 5 Scoring-Funktionen)
│   ├── filters.py              (Hard Filter)
│   ├── tests/
│   │   ├── test_scoring.py
│   │   ├── test_filters.py
│   │   └── test_pipeline_integration.py
│   └── requirements.txt
└── dashboard/
    ├── index.html              (komplettes Dashboard)
    ├── data.json               (Pipeline-Output)
    └── pipeline_log.txt        (Pipeline-Log)
```

## Offene Punkte für die Umsetzung

- **Ticker-Universum:** `yfinance` liefert keine vorgefertigte Liste aller US-Aktien. Entweder NASDAQ FTP-Liste (`ftp.nasdaqtrader.com`) oder Wikipedia-Listen für die drei Börsen als Ausgangspunkt. Ist in der Implementierung zu klären.
- **Laufzeit Pipeline:** Bei ~4.000 Tickern mit je einem yfinance-Call dauert der Zug je nach Rate-Limit ca. 30–60 Minuten. Akzeptabel für monatlichen Lauf, sollte aber dokumentiert sein.
- **Deployment:** Im ersten Schritt lokale `index.html` + `data.json`. GitHub Pages als nächster Schritt optional.
