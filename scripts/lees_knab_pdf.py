"""Leest een Knab-transactieoverzicht als pdf en schrijft het weg in hetzelfde formaat als de Knab-csv-export,
zodat bouw_overzicht.py (lees_knab) het gewoon meeneemt.

Of een bedrag af- of bijgeschreven is, staat alleen in de kolom (Af / Bij): dat bepalen we met de x-positie.
Alleen transacties ná de laatste datum in de bestaande csv van dezelfde rekening komen erin (geen dubbelingen).
"""
import csv
import glob
import re
from pathlib import Path

import pdfplumber

MAP = Path(__file__).resolve().parent.parent
DATUM = re.compile(r"^\d{2}-\d{2}-\d{4}$")
BEDRAG = re.compile(r"^\d{1,3}(\.\d{3})*,\d{2}$")
KOP = ["Rekeningnummer", "Transactiedatum", "Valutacode", "CreditDebet", "Bedrag", "Tegenrekeningnummer",
       "Tegenrekeninghouder", "Valutadatum", "Betaalwijze", "Omschrijving", "Type betaling", "Machtigingsnummer",
       "Incassant ID", "Referentie", "Boekdatum"]


def kolommen(pagina):
    """x-posities van de kolomkoppen."""
    w = pagina.extract_words()
    kop = {x["text"]: x["x0"] for x in w if x["text"] in ("Tegenrekening", "Naam", "Omschrijving", "Af", "Bij")}
    return kop


def lees(pad):
    rekening = None
    rijen = []
    with pdfplumber.open(pad) as pdf:
        for p in pdf.pages:
            tekst = p.extract_text() or ""
            m = re.search(r"Rekeningnummer (NL\d{2}KNAB\d{10})", tekst)
            if m:
                rekening = m.group(1)
            kop = kolommen(p)
            if "Af" not in kop or "Bij" not in kop:
                continue
            grens_afbij = (kop["Af"] + kop["Bij"]) / 2
            woorden = p.extract_words(keep_blank_chars=False)
            # groepeer per regel (y)
            regels = {}
            for w in woorden:
                regels.setdefault(round(w["top"] / 3), []).append(w)
            lijst = [sorted(v, key=lambda w: w["x0"]) for _, v in sorted(regels.items())]
            for i, r in enumerate(lijst):
                if len(r) < 3 or not (DATUM.match(r[0]["text"]) and DATUM.match(r[1]["text"])):
                    continue
                if not BEDRAG.match(r[-1]["text"]):
                    continue
                bedrag_w = r[-1]
                bij = bedrag_w["x1"] > grens_afbij
                midden = r[2:-1]
                tegenrek = " ".join(w["text"] for w in midden if w["x0"] < kop.get("Naam", 0) - 2)
                naam = " ".join(w["text"] for w in midden if kop.get("Naam", 0) - 2 <= w["x0"] < kop.get("Omschrijving", 0) - 2)
                oms = " ".join(w["text"] for w in midden if w["x0"] >= kop.get("Omschrijving", 0) - 2)
                # omschrijvingen lopen soms door op de regel erboven of eronder (zonder datum)
                extra = []
                for j in (i - 1, i + 1):
                    if 0 <= j < len(lijst) and lijst[j] and not DATUM.match(lijst[j][0]["text"]):
                        t = " ".join(w["text"] for w in lijst[j])
                        if not re.search(r"Rekeningnummer|Transactie|datum$|Aan dit overzicht|Knab aanvaardt|Pagina", t):
                            extra.append(t)
                if not naam and not tegenrek:  # pinbetaling: winkelnaam staat in de eerste woorden
                    naam = oms.split(" BE ")[0].split(" NL ")[0][:40] if oms else " ".join(extra)[:40]
                rijen.append({
                    "Rekeningnummer": rekening, "Transactiedatum": r[0]["text"], "Valutacode": "EUR",
                    "CreditDebet": "Bijschrijvingen" if bij else "Afschrijvingen",
                    "Bedrag": bedrag_w["text"].replace(".", ""), "Tegenrekeningnummer": tegenrek,
                    "Tegenrekeninghouder": naam, "Valutadatum": r[0]["text"], "Betaalwijze": "",
                    "Omschrijving": (oms + " " + " ".join(extra)).strip(), "Type betaling": "", "Machtigingsnummer": "",
                    "Incassant ID": "", "Referentie": "pdf", "Boekdatum": r[1]["text"],
                })
    return rekening, rijen


def laatste_csv_datum(rekening):
    laatste = None
    for f in glob.glob(str(MAP / "data/afschriften/Knab*.csv")):
        if "uit-pdf" in f:
            continue
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if r["Rekeningnummer"] == rekening:
                    d = r["Transactiedatum"][6:] + r["Transactiedatum"][3:5] + r["Transactiedatum"][:2]
                    laatste = max(laatste or d, d)
    return laatste


if __name__ == "__main__":
    for pad in sorted(glob.glob(str(MAP / "data/afschriften/Knab*.pdf"))):
        rekening, rijen = lees(pad)
        grens = laatste_csv_datum(rekening)
        nieuw = [r for r in rijen if grens is None or
                 (r["Transactiedatum"][6:] + r["Transactiedatum"][3:5] + r["Transactiedatum"][:2]) > grens]
        uit = MAP / "data/afschriften" / f"Knab uit-pdf {rekening[-4:]}.csv"
        with open(uit, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=KOP, delimiter=";")
            w.writeheader()
            w.writerows(nieuw)
        af = sum(float(r["Bedrag"].replace(",", ".")) for r in rijen if r["CreditDebet"] == "Afschrijvingen")
        bij = sum(float(r["Bedrag"].replace(",", ".")) for r in rijen if r["CreditDebet"] == "Bijschrijvingen")
        print(f"{Path(pad).name}: {len(rijen)} transacties (af €{af:,.2f}, bij €{bij:,.2f}); "
              f"na {grens}: {len(nieuw)} nieuw -> {uit.name}")
