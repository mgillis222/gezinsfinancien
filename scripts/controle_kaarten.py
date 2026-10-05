"""Vergelijkt per kaartafschrift de ingelezen regels met de samenvatting van Chase/Target."""
import csv, re, pathlib, collections
rijen = list(csv.DictReader(open("data/verwerkt/chase_transacties.csv", encoding="utf-8")))
per = collections.defaultdict(lambda: [0.0, 0.0])
for r in rijen:
    b = float(r["bedrag"]); per[r["afschrift"]][0 if b < 0 else 1] += b
def g(t, label):
    m = re.search(label + r"\s*([-+])\s*\$([\d,]+\.\d\d)", t); return float(m[2].replace(",", "")) if m else 0.0
for f in sorted(pathlib.Path("data/tekst").glob("*.txt")):
    t = f.read_text(encoding="utf-8")
    if f.name not in per or "CHECKING SUMMARY" in t or "SAVINGS SUMMARY" in t or "CONSOLIDATED" in t: continue
    if "Target Circle" in t:
        uit = sum(float(x.replace(",", "")) for x in re.findall(r"TOTAL PURCHASES AND OTHER DEBITS FOR THIS PERIOD \$([\d,]+\.\d\d)", t))
        uit += sum(float(x.replace(",", "")) for x in re.findall(r"TOTAL INTEREST FOR THIS PERIOD \$([\d,]+\.\d\d)", t))
        terug = sum(float(x.replace(",", "")) for x in re.findall(r"TOTAL PAYMENTS AND OTHER CREDITS FOR THIS PERIOD -\$([\d,]+\.\d\d)", t))
    else:
        uit = g(t, "Purchases") + g(t, "Cash Advances") + g(t, "Balance Transfers") + g(t, "Fees Charged") + g(t, "Interest Charged")
        terug = g(t, "Payment, Credits")
    ing_uit, ing_terug = -per[f.name][0], per[f.name][1]
    ok = abs(ing_uit - uit) < 0.01 and abs(ing_terug - terug) < 0.01
    print(f"{'OK ' if ok else 'XX '} {f.name}: uitgaven {ing_uit:9.2f} vs {uit:9.2f} | terug {ing_terug:9.2f} vs {terug:9.2f}")
