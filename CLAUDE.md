# Gezinsfinanciën 2026

## Doel
Compleet overzicht van de gezinsfinanciën van Myrthe en Jef vanaf 1 januari 2026, na de verhuizing van
Nederland naar Katy, Texas (december 2025). We willen weer grip en inzicht: wat geven we uit en waaraan.
Uiteindelijk willen we besparen, want sinds Bill naar de kinderopvang gaat, staan we net negatief.

## Wensen
- Alles op één plek: Knab (NL, euro) en Chase (VS, dollar), plus online bestellingen per artikel
  (Amazon, Kroger, Target, DoorDash enz.).
- Alles omgerekend naar dollars. Euro-uitgaven rekenen we om tegen de koers van die dag.
- Interne geldstromen eruit filteren, zodat niets dubbel telt: EUR→USD-wissels, creditcardaflossingen,
  overboekingen tussen eigen rekeningen.
- Voorschotten in dollars koppelen aan terugbetalingen in euro (en andersom).
- Twijfelgevallen gaan naar een lijst die Myrthe later met de hand doorloopt.
- Overzicht per maand en per categorie, vaste tegenover variabele lasten en de impact van de opvang,
  daarna concrete besparingskansen en een maandbudget.

## Wat níet
- Ruwe afschriften, bestellingen en rekeningnummers gaan nooit naar GitHub. Alles in `data/` blijft
  lokaal.
- Geen persoonlijk beleggingsadvies.

## Bestanden
- `data/afschriften/`: Chase-pdf's (rekeningen/kaarten 9708, 9862, 0103, 6010, 7970 en twee zonder
  nummer) en drie Knab-csv's (betaalrekening 1133, gezamenlijke rekening 9994, "Lily transfer" 5171).
- `data/bestellingen/`:
  - `amazon_bestellingen_2026.csv` en `amazon_artikelen_2026.csv`: uitgelezen van amazon.com
    (account van Jef). 96 orders en 171 artikelen; de bedragen sluiten op de cent.
  - `gmail_*.csv`: uit Gmail gehaald (Kroger, Target, eten, vaste lasten, overboekingen).
- `data/vermogen_beleggingen.md`: momentopnames van de beleggingsrekeningen.

## Besluiten
- 2026-10-04: we rekenen in USD. Amazon lezen we uit via de ingebouwde browser, want de
  Chrome-extensie werkt niet met Arc. Alle andere winkels halen we uit Gmail (myrthegillis@gmail.com).
- Stortingen op beleggingsrekeningen tellen als sparen, niet als uitgave.

## Kosten
- Geen. Alles draait lokaal (Python in WSL); er zijn geen betaalde API-calls.
