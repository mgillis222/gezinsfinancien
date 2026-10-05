"""Maakt data/verwerkt/dashboard.json voor de overzichtspagina (dashboard/overzicht.html).

Gebruikt: data/verwerkt/alle_transacties.csv (bouw_overzicht.py) en de bestelbestanden in data/bestellingen/.
Volledige maanden: jan t/m aug 2026 (van alle rekeningen zijn afschriften). September is deels binnen.
"""
import json, re
import pandas as pd

VOLLEDIG = [f"2026-{m:02d}" for m in range(1, 9)]
N = len(VOLLEDIG)

t = pd.read_csv("data/verwerkt/alle_transacties.csv")
t = t[t["datum"] >= "2026-01-01"].copy()
t["omschrijving"] = t["omschrijving"].fillna("")
vol = t[t["periode"].isin(VOLLEDIG)]

def schoon(s):
    s = re.sub(r"^Knab: ", "", s)
    s = re.sub(r"\s*\|.*$", "", s) if "|" in s else s
    s = re.sub(r"(Card Purchase( With Pin)?|Recurring Card Purchase)\s+(\d\d/\d\d\s+)?", "", s, flags=re.I)
    s = re.sub(r"(\s(Card|Transaction#|Jpm|PPD ID|Ref:)\b.*$)|\s\d{5,}.*$|\s+[A-Z]{2}$", "", s)
    return re.sub(r"\s+", " ", s).strip()[:60]

# ---------- maanden ----------
maanden = []
for p in sorted(t["periode"].unique()):
    m = t[t["periode"] == p]
    maanden.append({
        "periode": p, "volledig": p in VOLLEDIG,
        "inkomen": round(m[m.soort == "inkomen"]["bedrag_usd"].sum(), 2),
        "uitgaven": round(-m[m.soort == "uitgave"]["bedrag_usd"].sum(), 2),
        "sparen": round(-m[m.soort == "sparen"]["bedrag_usd"].sum(), 2),
        "per_categorie": {k: round(-v, 2) for k, v in m[m.soort == "uitgave"].groupby("categorie")["bedrag_usd"].sum().items()},
        "inkomen_per_bron": {k: round(v, 2) for k, v in m[m.soort == "inkomen"].groupby("subcategorie")["bedrag_usd"].sum().items()},
    })

# ---------- categorieën met subcategorie, tegenpartij en transacties ----------
cats = []
u = t[t.soort == "uitgave"]
for cat, g in u.groupby("categorie"):
    gv = g[g["periode"].isin(VOLLEDIG)]
    subs = []
    for sub, gs in g.groupby("subcategorie"):
        gs = gs.assign(naam=gs["omschrijving"].map(schoon))
        top = gs.groupby("naam")["bedrag_usd"].agg(["sum", "count"]).sort_values("sum").head(12)
        subs.append({"naam": sub, "totaal": round(-gs["bedrag_usd"].sum(), 2),
                     "per_maand_gem": round(-gs[gs["periode"].isin(VOLLEDIG)]["bedrag_usd"].sum() / N, 2),
                     "tegenpartijen": [{"naam": k, "totaal": round(-r["sum"], 2), "aantal": int(r["count"])} for k, r in top.iterrows()]})
    trans = [{"d": r.datum, "o": schoon(r.omschrijving), "b": round(-r.bedrag_usd, 2), "s": r.subcategorie,
              "v": r.valuta, "bo": round(-r.bedrag_orig, 2), "r": f"{r.bank} {r.rekening}"} for r in g.sort_values("datum", ascending=False).itertuples()]
    cats.append({"naam": cat, "totaal": round(-g["bedrag_usd"].sum(), 2), "per_maand_gem": round(-gv["bedrag_usd"].sum() / N, 2),
                 "subcategorieen": sorted(subs, key=lambda s: -s["totaal"]), "transacties": trans})
cats.sort(key=lambda c: -c["totaal"])

inkomen = []
for sub, g in t[t.soort == "inkomen"].groupby("subcategorie"):
    inkomen.append({"naam": sub, "totaal": round(g["bedrag_usd"].sum(), 2),
                    "per_maand_gem": round(g[g["periode"].isin(VOLLEDIG)]["bedrag_usd"].sum() / N, 2),
                    "transacties": [{"d": r.datum, "o": schoon(r.omschrijving), "b": round(r.bedrag_usd, 2), "v": r.valuta, "bo": round(r.bedrag_orig, 2)} for r in g.sort_values("datum", ascending=False).itertuples()]})
inkomen.sort(key=lambda c: -c["totaal"])
sparen = [{"d": r.datum, "o": r.subcategorie, "b": round(-r.bedrag_usd, 2)} for r in t[t.soort == "sparen"].sort_values("datum").itertuples()]

# ---------- artikelen (Amazon, Target en overige webshops) ----------
from artikelen import amazon_artikelen
ao, aa = amazon_artikelen()
TARGET_CAT = {"boodschappen": "Boodschappen", "drogisterij-verzorging": "Verzorging & gezondheid", "huishouden-schoonmaak": "Huishouden & schoonmaak",
              "speelgoed": "Kinderen & speelgoed", "huis-tuin": "Huis & keuken", "baby-luiers-voeding": "Baby & zwangerschap", "kleding": "Kleding & overig",
              "elektronica": "Elektronica", "cadeaus": "Cadeaus, boeken & kaarten", "restaurant-bezorging": "Uit eten & bezorging", "maaltijdbox": "Maaltijdbox"}
ga = pd.read_csv("data/bestellingen/gmail_target_eten_artikelen.csv")
ga["regeltotaal"] = pd.to_numeric(ga["regeltotaal"], errors="coerce")
ga["cat"] = ga["categorie_voorstel"].map(TARGET_CAT).fillna("Overig")
ga["winkelgroep"] = ga["winkel"].map(lambda w: "Target" if str(w).startswith("Target") else ("DoorDash" if "DoorDash" in str(w) else str(w)))
go = pd.read_csv("data/bestellingen/gmail_target_eten_orders.csv")
go["totaal"] = pd.to_numeric(go["totaal"], errors="coerce"); go["fooi"] = pd.to_numeric(go["bezorgkosten_fooi"], errors="coerce").fillna(0)
tg = go[(go["winkel"] == "Target") & (go["status"] != "geannuleerd")]

def winkel_blok(naam, art, ordertotaal, aantal_orders, extra=None):
    per = art.groupby("cat")["regeltotaal"].sum().sort_values(ascending=False)
    top = art.assign(n=art["artikel"].str.slice(0, 90)).groupby("n").agg(totaal=("regeltotaal", "sum"), keer=("regeltotaal", "size")).sort_values("totaal", ascending=False).head(25)
    return {"winkel": naam, "ordertotaal": round(ordertotaal, 2), "orders": int(aantal_orders), "artikelregels": int(len(art)),
            "met_prijs": int(art["regeltotaal"].notna().sum()),
            "per_categorie": [{"naam": k, "totaal": round(v, 2)} for k, v in per.items()],
            "top_artikelen": [{"naam": k, "totaal": round(r["totaal"], 2), "keer": int(r["keer"])} for k, r in top.iterrows()],
            "alle_artikelen": [{"d": r.datum, "a": str(r.artikel)[:110], "n": None if pd.isna(r.aantal) else r.aantal,
                                "b": None if pd.isna(r.regeltotaal) else round(r.regeltotaal, 2), "c": r.cat} for r in art.sort_values("datum", ascending=False).itertuples()],
            **(extra or {})}

winkels = [
    winkel_blok("Amazon", aa, ao[ao["geannuleerd"] == "nee"]["totaal"].sum(), (ao["geannuleerd"] == "nee").sum(),
                {"noot": "Volledig per artikel (uitgelezen van amazon.com). Bij 5 orders deels met cadeaukaart betaald."}),
    winkel_blok("Target", ga[ga["winkelgroep"] == "Target"], tg["totaal"].sum(), (tg["soort"] != "retour").sum(),
                {"noot": "Uit Gmail. Bij Drive Up/afhalen staan geen prijzen per artikel in de mail; die regels tellen niet mee in de categorieverdeling.",
                 "bezorgorders": int((tg["soort"] == "bezorging").sum()), "fooien": round(tg["fooi"].sum(), 2)}),
    winkel_blok("DoorDash", ga[ga["winkelgroep"] == "DoorDash"], go[go["winkel"].str.startswith("DoorDash")]["totaal"].sum(),
                go["winkel"].str.startswith("DoorDash").sum(), {"noot": "Uit Gmail. Alleen 'final receipts' hebben artikelen."}),
]

# ---------- FSA ----------
fsa = {"dc": {"per_salaris": 288.46, "jaar": 7500, "ingelegd": round(t[(t.bank == "HealthEquity") & (t.rekening == "Dependent Care") & (t.soort == "inkomen")]["bedrag_usd"].sum(), 2),
              "uitbetaald": 4900.0, "einde_claimen": "2027-03-15"},
       "hc": {"jaar": 3400, "uitgegeven": round(-t[(t.bank == "HealthEquity") & (t.rekening == "Healthcare") & (t.soort == "uitgave")]["bedrag_usd"].sum(), 2),
              "einde": "2026-12-31"},
       "opvang_betaald_2026": round(-t[t.subcategorie == "Primrose (Lily & Bill)"]["bedrag_usd"].sum(), 2)}

# ---------- abonnementen (laatste bekende maandbedrag per dienst) ----------
from abonnementen import maak_lijst, BINNENKORT
abonnementen = maak_lijst(t, schoon)

# ---------- twijfelgevallen ----------
tw = t[(t["twijfel"]) | (t["categorie"] == "Nog indelen")]
twijfel = [{"d": r.datum, "o": schoon(r.omschrijving), "b": round(r.bedrag_usd, 2), "s": r.subcategorie, "r": f"{r.bank} {r.rekening}"} for r in tw.sort_values("bedrag_usd").itertuples()]

# ---------- kleine lekjes ----------
def som(mask): return round(-t[mask]["bedrag_usd"].sum(), 2)
lekjes = {
    "buitenlandkosten": som(t.omschrijving.str.contains("FOREIGN TRANSACTION FEE", case=False)),
    "rente_target": som(t.omschrijving.str.contains("Interest Charge", case=False)),
    "knab_kosten": som(t.omschrijving.str.startswith("Knab: Knab")),
    "nl_streaming": som((t.bank == "Knab") & t.omschrijving.str.contains("NETFLIX|VIDEOLAND|NPO|Prime Video|Podimo|Spotify|Storytel|hbomax", case=False)),
    "bezorging_doordash": round(go[go["winkel"].str.startswith("DoorDash")]["totaal"].sum(), 2),
}

# ---------- vooruitblik: een gewone maand vanaf oktober 2026 ----------
from eenmalig import markeer
vol = markeer(vol)
struct = ~vol["eenmalig"] & ~vol["grote_vakantie"]          # structurele maand: zonder eenmalige posten en grote vakanties
def gem(mask): return round(-vol[mask & struct]["bedrag_usd"].sum() / N, 0)
GROTE_VAK_JAAR = round(-vol[vol["grote_vakantie"]]["bedrag_usd"].sum(), 0)   # grote vakantie(s) jan-aug ~ één per jaar
EENMALIG_LIJST = vol[vol["eenmalig"]].groupby("subcategorie")["bedrag_usd"].sum().mul(-1).round(0).sort_values(ascending=False)
koers = float(t[t.valuta == "EUR"].sort_values("datum")["eur_usd"].dropna().iloc[-1])
VB = {
    "koers": round(koers, 4),
    "inkomen": [
        {"id": "salaris", "naam": "Salaris Jef (netto, 26× per jaar $4.340)", "bedrag": round(4340.34 * 26 / 12)},
        {"id": "dcfsa", "naam": "Dependent Care FSA terug (eigen inleg $288 per salaris)", "bedrag": round(288.46 * 26 / 12)},
        {"id": "huurnl", "naam": "Huur woning NL (€2.495)", "bedrag": round(2495 * koers)},
        {"id": "freelance", "naam": "Freelance Myrthe", "bedrag": 0},
        {"id": "ouders", "naam": "Bijdrage ouders selfcare (€60)", "bedrag": round(60 * koers)},
    ],
    "vast": [
        {"id": "huur", "naam": "Huur Cottondale Ct", "bedrag": 3100},
        {"id": "woningnl", "naam": "Woning NL: hypotheekrente, VvE, belastingen", "bedrag": round(-vol[(vol.categorie == "Woning NL") & (vol.periode >= "2026-02")]["bedrag_usd"].sum() / 7)},
        {"id": "aflos", "naam": "Aflossing hypotheek NL (€1.214, vermogensopbouw)", "bedrag": round(1214.28 * koers), "sparen": True},
        {"id": "opvang", "naam": "Primrose: Lily + Bill ($630 per week)", "bedrag": round(630 * 52 / 12)},
        {"id": "schoonmoeder", "naam": "Ondersteuning schoonmoeder (€800)", "bedrag": round(800 * koers)},
        {"id": "schoonmaak", "naam": "Schoonmaak (Nancy)", "bedrag": gem(vol.subcategorie == "Schoonmaak (Nancy)")},
        {"id": "oppas", "naam": "Oppas", "bedrag": gem(vol.subcategorie == "Oppas")},
        {"id": "tuin", "naam": "Tuinman (Avertano)", "bedrag": gem(vol.subcategorie == "Tuinman (Avertano)")},
        {"id": "nuts", "naam": "Water, stroom, gas", "bedrag": gem(vol.categorie == "Nutsvoorzieningen")},
        {"id": "tel", "naam": "Telefoon & internet", "bedrag": gem(vol.categorie == "Telefoon & internet")},
        {"id": "verz", "naam": "Verzekeringen (auto, leven, reis)", "bedrag": gem(vol.categorie == "Verzekeringen")},
        {"id": "abo", "naam": "Abonnementen die nu lopen (incl. jaarlijkse, per maand)", "bedrag": round(sum(a["per_maand"] for a in abonnementen if a["status"] in ("loopt", "jaarlijks")))},
    ],
    "variabel": [
        {"id": "boodschappen", "naam": "Boodschappen (incl. Target)", "bedrag": gem(vol.categorie == "Boodschappen")},
        # Maaltijdboxen zijn gestopt (HelloFresh aug, Green Chef 1 okt 2026) en tellen niet meer mee.
        {"id": "eten", "naam": "Eten & drinken: uit eten, koffie, lunch Jef (maaltijdboxen gestopt)", "bedrag": gem((vol.categorie == "Eten & drinken") & (vol.subcategorie != "Maaltijdboxen"))},
        {"id": "reizen", "naam": "Uitjes, tickets en eten onderweg", "bedrag": gem((vol.categorie == "Reizen & uitjes") & (vol.subcategorie != "Reizen, hotels, vluchten"))},
        # Tot Myrthe werk heeft geen vakanties of weekendjes weg (5 okt 2026). Historisch gemiddelde staat in de naam.
        {"id": "weekendjes", "naam": f"Weekendjes weg: hotels, campings (voorheen gem. ${gem((vol.categorie == 'Reizen & uitjes') & (vol.subcategorie == 'Reizen, hotels, vluchten')):.0f}; nu niet gepland)", "bedrag": 0},
        # Komende maanden geen grote vakantie die geld kost (Myrthe, 5 okt 2026): Florida (dec) en skiën (mrt) betalen
        # de ouders van Myrthe, Parijs (feb) is al betaald. Ter vergelijking: deze zomer ±GROTE_VAK_JAAR.
        {"id": "grotevak", "naam": "Grote vakantie (niets gepland: Florida en skiën betaald door ouders, Parijs al betaald)", "bedrag": 0},
        {"id": "vervoer", "naam": "Vervoer (benzine, tol, Uber, auto)", "bedrag": gem(vol.categorie == "Vervoer")},
        {"id": "kleding", "naam": "Kleding & persoonlijk", "bedrag": gem(vol.categorie == "Kleding & persoonlijk")},
        {"id": "kinderen", "naam": "Kinderen (activiteiten, spullen)", "bedrag": gem((vol.categorie == "Kinderen") & (vol.subcategorie != "Geboortekaartjes Bill"))},
        {"id": "zorg", "naam": "Zorg (eigen betalingen, buiten FSA)", "bedrag": gem((vol.categorie == "Zorg") & (vol.bank != "HealthEquity"))},
        {"id": "huis", "naam": "Huis, sport, hobby, elektronica", "bedrag": gem(vol.categorie.isin(["Huis & inrichting", "Sport & hobby", "Elektronica"]))},
        {"id": "overig", "naam": "Overig (giften, documenten, bank, contant)", "bedrag": gem(vol.categorie.isin(["Giften", "Overheid & documenten", "Bankkosten", "Contant geld", "Huishouden"]) & ~vol.subcategorie.isin(["Schoonmaak (Nancy)", "Tuinman (Avertano)"]))},
    ],
}
# Besparingsplan (opnieuw bekeken met Myrthe, 5 okt 2026). Niet voorstellen: boodschappen, bezorgen, uit eten,
# Claude Max (blijft), LinkedIn Premium (helpt bij het zoeken naar werk). Bedragen per maand.
def b(id, naam, bedrag, uitleg, soort):
    return {"id": id, "naam": naam, "bedrag": round(bedrag), "uitleg": uitleg, "soort": soort}
VB["besparen"] = [
    b("abo", "Abonnementen: Coursera, NL-streaming en Disney+ stoppen", 49 + 42 + 14,
      "Coursera $49 (na de cursus), Netflix NL, Videoland, Podimo, Prime Video NL en NPO samen ±$42, Disney+ $14. Claude Max en LinkedIn blijven.", "makkelijk"),
    b("tel", "Telefoon: goedkopere aanbieder op hetzelfde netwerk", 45,
      "Twee AT&T-lijnen kosten nu ±$90 per maand. Mint of Visible: ±$15–25 per lijn.", "makkelijk"),
    b("verz", "Autoverzekering vergelijken bij verlenging (half december)", 45,
      "GEICO kostte $1.870 voor een half jaar. Vraag een paar offertes op voordat hij verlengt.", "makkelijk"),
    b("knab", "Knab: minder rekeningen", 7, "Pakketkosten €6 per maand; met minder rekeningen wordt dat lager.", "makkelijk"),
    b("kleding", "Kleding & persoonlijk: van $341 naar $200", 140,
      "Vooral Patagonia, Hanna Andersson en Showroomprivé. Tweedehands (Kid to Kid, Poshmark, Sellpy) doen jullie al voor de kinderen.", "keuze"),
    b("huis", "Huis, sport, hobby, elektronica: van $252 naar $150", 100, "Grotere aankopen eerst 48 uur op een verlanglijst.", "keuze"),
    b("schoonmaak", "Schoonmaak één keer per vier weken zolang jij thuis bent", 145, "Nu elke twee weken $170 bij Nancy.", "keuze"),
    b("ctc", "Child Tax Credit voor Bill (via de aangifte)", 183, "$2.200 per jaar. Lily heeft geen SSN en telt daarom niet mee. Laat het meenemen in de aangifte.", "inkomen"),
    b("opvang", "Opvang: één dag minder voor beide kinderen zolang jij thuis bent", 550,
      "Schatting: $630 per week voor vijf dagen. Vraag Primrose naar de deeltijdtarieven. Nadeel: minder tijd om te solliciteren, mogelijk plek kwijt.", "groot"),
]

uit = {"bijgewerkt": pd.Timestamp.today().strftime("%Y-%m-%d"), "volledige_maanden": VOLLEDIG, "maanden": maanden,
       "categorieen": cats, "inkomen": inkomen, "sparen": sparen, "winkels": winkels, "fsa": fsa,
       "abonnementen": abonnementen, "abo_binnenkort": BINNENKORT, "twijfel": twijfel, "lekjes": lekjes, "vooruitblik": VB, "eenmalig": [{"naam": k, "bedrag": v} for k, v in EENMALIG_LIJST.items()], "grote_vakantie_jaar": GROTE_VAK_JAAR,
       "reserve": {"schenking_eur": 90000, "noot": "Schenking ouders, staat op Belgische spaarrekening op naam van de ouders; op te vragen."},
       "vermogen": [{"naam": "Overwaarde woning NL (geschatte waarde €655.000 − schuld €429.994, okt 2026; bandbreedte €195k–€260k)", "eur": 225006.41},
                    {"naam": "Chase CD (deposito, t/m 30-07-2026)", "usd": 10000},
                    {"naam": "Beleggingsrekening VS (4 okt)", "usd": 5877},
                    {"naam": "Kinderrekening Brand New Day (4 okt)", "eur": 5559.62}]}
with open("data/verwerkt/dashboard.json", "w", encoding="utf-8") as f:
    json.dump(uit, f, ensure_ascii=False, separators=(",", ":"))
print("dashboard.json:", round(len(json.dumps(uit)) / 1024), "KB")
for c in cats[:8]: print(f"  {c['naam']:24s} {c['per_maand_gem']:9.0f}/mnd")
print("Amazon per categorie:", [(x['naam'], x['totaal']) for x in winkels[0]['per_categorie']])
print("Target:", winkels[1]['ordertotaal'], winkels[1]['orders'], "bezorg", winkels[1]['bezorgorders'], "fooi", winkels[1]['fooien'])
print("FSA:", fsa); print("Lekjes:", lekjes)
print("Abonnementen:", [(a['naam'], a['status'], a['per_maand']) for a in abonnementen])
