"""Leest alle Chase- en Target-afschriften (data/tekst/*.txt, gemaakt door pdf_naar_tekst.py)
en schrijft één tabel: data/verwerkt/chase_transacties.csv.

Bedragen: negatief = geld eruit (uitgave/betaling), positief = geld erin.
Voor betaalrekeningen wordt elke regel gecontroleerd tegen het lopende saldo.
"""
import csv, re, pathlib, datetime

TEKST = pathlib.Path("data/tekst")
UIT = pathlib.Path("data/verwerkt"); UIT.mkdir(exist_ok=True)

def bedrag(s):
    s = s.replace("$", "").replace(",", "")
    return float(s)

def jaar_voor(maand, afschrift_datum):
    # Transacties in een latere maand dan de afschriftdatum horen bij het vorige jaar (dec op een jan-afschrift).
    return afschrift_datum.year - 1 if maand > afschrift_datum.month else afschrift_datum.year

def afschrift_datum(naam, tekst):
    m = re.match(r"(\d{8})", naam)
    return datetime.date(int(m[1][:4]), int(m[1][4:6]), int(m[1][6:8]))

def rekening(naam, tekst):
    m = re.search(r"statements-(\d{4})", naam)
    if m: return m[1]
    m = re.search(r"Target Circle Card Ending in: (\d{4})", tekst)
    return m[1] if m else "?"

def lees_betaalrekening(naam, tekst, datum, rek):
    rijen, fouten = [], []
    in_detail, vorige_saldo = False, None
    for ruw in tekst.splitlines():
        regel = re.sub(r"^\*end\*transac(\d)tion detail", r"\1", ruw.strip())
        if "*start*transaction detail" in regel: in_detail = True; continue
        if regel.startswith("*end*transaction detail") or regel.startswith("Ending Balance"):
            in_detail = False; continue
        if not in_detail: continue
        m = re.match(r"Beginning Balance \$?(-?[\d,]+\.\d\d)", regel)
        if m:
            if vorige_saldo is None: vorige_saldo = bedrag(m[1])
            continue
        m = re.match(r"^(\d\d)/(\d\d) (?:\d\d/\d\d )?(.+?) (-?[\d,]*\.\d\d) (-?[\d,]*\.\d\d)$", regel)
        if m:
            mnd, dag = int(m[1]), int(m[2])
            b, saldo = bedrag(m[4]), bedrag(m[5])
            if vorige_saldo is not None and abs(vorige_saldo + b - saldo) > 0.005:
                fouten.append(f"{naam}: saldo klopt niet bij '{regel}'")
            vorige_saldo = saldo
            rijen.append({"datum": datetime.date(jaar_voor(mnd, datum), mnd, dag).isoformat(),
                          "omschrijving": m[3], "bedrag": b})
        elif rijen and regel and not re.match(r"^(DATE|TRANSACTION DETAIL|\(continued\)|Page|\d{6,}|.*through.*|Primary Account)", regel):
            rijen[-1]["omschrijving"] += " " + regel   # vervolgregel van de omschrijving
    return rijen, fouten

def lees_chase_kaart(naam, tekst, datum, rek):
    rijen = []
    in_activiteit = False
    for regel in (r.strip() for r in tekst.splitlines()):
        if re.search(r"ACCOUNT ACTIVITY|AACCCCOOUUNNTT", regel): in_activiteit = True; continue
        if re.match(r"^(\d{4} Totals Year-to-Date|TOTAL FEES|TOTAL INTEREST|INTEREST CHARGES|IINNTTEERREESSTT)", regel):
            in_activiteit = False; continue
        if not in_activiteit: continue
        m = re.match(r"^(\d\d)/(\d\d) (.+?) (-?[\d,]*\.\d\d)$", regel)
        if m:
            mnd, dag = int(m[1]), int(m[2])
            # Op een kaartafschrift is een aankoop positief; wij draaien om: uitgave = negatief.
            rijen.append({"datum": datetime.date(jaar_voor(mnd, datum), mnd, dag).isoformat(),
                          "omschrijving": m[3], "bedrag": -bedrag(m[4])})
    return rijen, []

def lees_target_kaart(naam, tekst, datum, rek):
    rijen = []
    for regel in (r.strip() for r in tekst.splitlines()):
        m = re.match(r"^(\d{1,2})/(\d{1,2}) (.+?) (-?\$[\d,]+\.\d\d)$", regel)
        if m:
            mnd, dag = int(m[1]), int(m[2])
            rijen.append({"datum": datetime.date(jaar_voor(mnd, datum), mnd, dag).isoformat(),
                          "omschrijving": m[3], "bedrag": -bedrag(m[4])})
    return rijen, []

alle, fouten, gezien = [], [], set()
for f in sorted(TEKST.glob("*.txt")):
    tekst = f.read_text(encoding="utf-8")
    datum, rek = afschrift_datum(f.name, tekst), rekening(f.name, tekst)
    sleutel = (rek, datum)
    if sleutel in gezien:
        print(f"overgeslagen (dubbel afschrift): {f.name}"); continue
    gezien.add(sleutel)
    if "Target Circle Card" in tekst:
        soort, lezer = "target-kaart", lees_target_kaart
    elif "CHECKING SUMMARY" in tekst or "SAVINGS SUMMARY" in tekst or "CONSOLIDATED BALANCE" in tekst:
        soort, lezer = "bank", lees_betaalrekening
    else:
        soort, lezer = "chase-kaart", lees_chase_kaart
    rijen, f_fouten = lezer(f.name, tekst, datum, rek)
    fouten += f_fouten
    for r in rijen:
        r.update({"rekening": rek, "soort_rekening": soort, "afschrift": f.name})
    alle += rijen
    print(f"{f.name}: {soort} {rek}, {len(rijen)} transacties, som {sum(r['bedrag'] for r in rijen):.2f}")

with open(UIT / "chase_transacties.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, ["datum", "rekening", "soort_rekening", "omschrijving", "bedrag", "afschrift"])
    w.writeheader(); w.writerows(sorted(alle, key=lambda r: (r["datum"], r["rekening"])))
print(f"\nTotaal {len(alle)} transacties. Saldo-fouten: {len(fouten)}")
for x in fouten: print("  ", x)
