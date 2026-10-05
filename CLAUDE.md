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
- Analyse over complete maanden (vanaf jan 2026). September en oktober zijn nog onvolledig, omdat niet
  van alle kaarten het afschrift binnen is.
- Bevestigd door Myrthe (2026-10-05):
  - Cashier's check 9 jan ($4.341): pop-up camper (eenmalig).
  - Inneke Peeters (schoonmoeder): vaste ondersteuning van €800 per maand sinds 25 juni 2026.
  - Nancy Herrera: schoonmaak. Avertano Rendon en Evelyna Rozenfeld: oppas.
  - Bear Graphics: geboortekaartjes Bill.
  - Chase 6010 had in maart en augustus geen afschrift (geen uitgaven).
  - Fugro NL €1.956,84 (4 mei): aankoop aandelen Fugro door Jef, dus sparen/beleggen.
  - ICS-creditcard (NL): alleen ChatGPT €21,48/mnd t/m maart en €28 jaarbijdrage; geen afschriften nodig.
- Lening van de ouders (Gillis-Reyniers): €5.000 in mei, €3.600 terug in juni. Telt als intern, niet als
  inkomen. De €60 per maand "Selfcare" telt wel als inkomen.
- Terugbetalingen van reisgenoten (cruise, weekendjes) verlagen de post Reizen.

## Kosten
- Geen. Alles draait lokaal (Python in WSL); er zijn geen betaalde API-calls.
