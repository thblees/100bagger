# GitHub Setup

So bekommst du den Screener online und monatlich automatisch aktualisiert.

**Ziel-URL nach Setup:** https://thblees.github.io/100bagger/

## Schritt 1 — Repo auf GitHub anlegen

1. Einloggen auf https://github.com
2. Oben rechts auf `+` → `New repository`
3. Settings:
   - **Owner:** thblees
   - **Repository name:** `100bagger`
   - **Visibility:** Public (wichtig — Actions laufen dann unbegrenzt gratis)
   - **KEINE** Haken bei "Add README", ".gitignore" oder "license" (wir haben lokal schon alles)
4. Auf `Create repository` klicken

## Schritt 2 — Lokales Repo zu GitHub pushen

Im Projektordner ausführen:

```bash
git remote add origin https://github.com/thblees/100bagger.git
git branch -M main
git push -u origin main
```

Bei der ersten Push-Aufforderung nach Benutzernamen/Passwort:
- Benutzername: `thblees`
- Passwort: **Personal Access Token** (nicht dein normales Passwort)

Token erstellen: https://github.com/settings/tokens → `Generate new token (classic)` → Scopes: `repo` anhaken → 30 Tage Laufzeit → kopieren und als Passwort einfügen.

Alternativ GitHub CLI verwenden falls installiert: `gh auth login` einmalig, dann ist Push ohne Token möglich.

## Schritt 3 — GitHub Pages aktivieren

1. Im Repo: `Settings` → `Pages` (linke Sidebar)
2. **Source:** `Deploy from a branch`
3. **Branch:** `main`, Folder: `/docs`
4. `Save`

Nach 1-2 Minuten ist die Seite live unter **https://thblees.github.io/100bagger/**

## Schritt 4 — Actions-Berechtigungen setzen

Damit der Cron-Job das aktualisierte `data.json` zurück ins Repo committen kann:

1. Im Repo: `Settings` → `Actions` → `General`
2. Runter scrollen zu **Workflow permissions**
3. Auf **Read and write permissions** setzen
4. `Save`

## Schritt 5 — Ersten automatischen Lauf anstoßen (optional)

Warten bis zum 1. des Monats, ODER manuell triggern:

1. Im Repo: `Actions` Tab
2. Links `Refresh Screener Data` auswählen
3. Rechts `Run workflow` → `Run workflow`
4. Lauf dauert ~3,5 h. Fortschritt im Actions-Tab live verfolgbar.

Nach erfolgreichem Lauf: `data.json` wird automatisch commitet, GitHub Pages aktualisiert sich, Dashboard zeigt frische Daten.

## Zeitplan

Der Cron läuft **jeden 1. des Monats um 03:00 UTC** (05:00 deutscher Sommerzeit, 04:00 Winterzeit). Wenn du das ändern willst, editiere in `.github/workflows/refresh.yml` die Zeile:

```yaml
    - cron: '0 3 1 * *'
```

Format: `minute stunde tag-des-monats monat wochentag`. Beispiele:
- `0 3 * * 1` → Jeden Montag 03:00 UTC
- `0 3 1,15 * *` → 1. und 15. jedes Monats 03:00 UTC
- `0 3 * * *` → Täglich 03:00 UTC

## Was zu tun wenn der Lauf scheitert

Drei häufige Gründe:

1. **Yahoo rate-limited den Runner** → GitHub sendet dir eine Mail. Lösung: Workflow später neu triggern, oder auf bezahlte Datenquelle umsteigen.
2. **Paket-Versionen nicht kompatibel** → In `pipeline/requirements.txt` die Pins lockern (`==` zu `>=`).
3. **Timeout (>5 h)** → In `refresh.yml` `timeout-minutes` erhöhen (max. 360).

Logs findest du im Actions-Tab pro Lauf. Der `Show pipeline log tail` Step zeigt die letzten 50 Zeilen des Pipeline-Logs.

## Repo-Aktivität aufrechterhalten

GitHub deaktiviert geplante Workflows in Repos, die **60 Tage lang keine Aktivität** hatten. Da unser Cron monatlich committet, bleibt das Repo aktiv. Falls doch mal pausiert: einfach irgendeinen Commit pushen oder den Workflow manuell triggern, dann läuft der Schedule weiter.
