"""Vaste boodschappen (essentials) uit alle winkels samenvoegen.

Leest de Kroger-bonnen (uit de browser) en de Target/H-E-B/ALDI/Sprouts-artikelen
(uit Gmail), deelt elk artikel in een productgroep in en berekent per groep:
hoe vaak gekocht, hoeveel uitgegeven, en de prijs per eenheid per winkel.
Schrijft data/verwerkt/boodschappen_artikelen.csv en boodschappen_groepen.csv.
"""
import re
from pathlib import Path

import pandas as pd

MAP = Path(__file__).resolve().parent.parent
B = MAP / "data" / "bestellingen"
UIT = MAP / "data" / "verwerkt"

# (groep, afdeling, regex op artikelnaam, eenheid voor prijsvergelijking)
GROEPEN = [
    # Drinken
    ("Cola Zero cafeïnevrij", "Drinken", r"coca.?cola|coke", "floz"),
    ("Bruiswater (Polar, Sparkling Ice)", "Drinken", r"sparkling|seltzer|polar|la croix|bubly|topo chico", "floz"),
    ("Alcoholvrij bier", "Drinken", r"non.?alcoholic|athletic brewing|na beer", "floz"),
    ("Sap / limonade / drinkmix", "Drinken", r"juice|crystal light|lemonade|electrolyte|pedialyte|zarbee", "floz"),
    ("Koffiemachine (eenmalig)", "Overig", r"coffee.*machine|espresso machine", "stuk"),
    ("Nespresso-capsules", "Drinken", r"nespresso|vertuo", "stuk"),
    ("Koffie / thee", "Drinken", r"coffee|latte|tea bags|herbal tea|\btea\b", "stuk"),
    # Huishouden en verzorging
    ("Luiers / babydoekjes", "Baby & verzorging", r"diaper|baby wipes|huggies|pampers|wipes", "stuk"),
    ("Huishoudpapier / folie", "Huishouden", r"paper towel|toilet paper|plastic wrap|foil|zip|storage bag|trash bag|parchment|napkins", "stuk"),
    ("Schoonmaak / afwas", "Huishouden", r"dish|detergent|cleaning|clorox|wipes(?!.*baby)|sponge|scotch-brite|cascade|tide|lysol|hand soap|dobie", "stuk"),
    ("Vitamines / medicijnen", "Baby & verzorging", r"vitamin|gummies|magnesium|theraflu|mucinex|imodium|afrin|cold medicine|olly|omeprazole|tylenol|motrin|ibuprofen|bandage|band-aid|saline", "stuk"),
    ("Verzorging", "Baby & verzorging", r"shampoo|conditioner|toothpaste|deodorant|lotion|body wash|soap", "stuk"),
    # Zuivel en eieren
    ("Eieren", "Zuivel & eieren", r"\beggs?\b", "stuk"),
    ("Havermelk barista", "Zuivel & eieren", r"oat ?milk.*barista|barista.*oat ?milk|oatly", "floz"),
    ("Havermelk origineel", "Zuivel & eieren", r"planet oat|oat ?milk", "floz"),
    ("Griekse yoghurt", "Zuivel & eieren", r"greek.*yogurt|fage|siggi|chobani|ratio", "oz"),
    ("Yoghurt (gewoon, kind)", "Zuivel & eieren", r"yogurt|activia|yoplait", "oz"),
    ("Cottage cheese", "Zuivel & eieren", r"cottage cheese", "oz"),
    ("Roomkaas", "Zuivel & eieren", r"cream cheese|philadelphia|boursin", "oz"),
    ("Zure room", "Zuivel & eieren", r"sour cream", "oz"),
    ("Boter", "Zuivel & eieren", r"\bbutter\b(?!.*peanut)", "oz"),
    ("Halloumi", "Kaas", r"halloumi", "oz"),
    ("Burrata / mozzarella vers", "Kaas", r"burrata|mozzarella (pearls|balls|sliced|ball)|fresh mozzarella", "oz"),
    ("Geraspte kaas", "Kaas", r"shredded.*cheese|cheese.*shredded|shredded mozzarella|parmesan", "oz"),
    ("Plakjes kaas", "Kaas", r"sliced cheese|cheese.*slices|provolone|gouda", "oz"),
    ("Feta / gorgonzola", "Kaas", r"feta|gorgonzola", "oz"),
    ("Ricotta", "Kaas", r"ricotta", "oz"),
    ("Kaassnacks", "Kaas", r"quick bites|balanced breaks|babybel|string cheese|cheese.*snack", "stuk"),
    # Groente
    ("Aubergine", "Groente", r"eggplant", "stuk"),
    ("Paprika", "Groente", r"bell pepper", "stuk"),
    ("Snoeptomaatjes", "Groente", r"snacking tomato|grape tomato|cherry tomato|medley tomato|glorys|cherubs|constellation", "oz"),
    ("Roma/trostomaten", "Groente", r"roma tomato|tomatoes by the bunch|vine.*tomato", "lb"),
    ("Komkommer", "Groente", r"cucumber", "stuk"),
    ("Spinazie / sla", "Groente", r"spinach(?!.*frozen)|arugula|salad kit|romaine|spring mix", "oz"),
    ("Avocado", "Groente", r"avocado(?!.*ranch)", "stuk"),
    ("Guacamole", "Groente", r"guacamole", "oz"),
    ("Courgette / squash", "Groente", r"zucchini|squash yellow|chayote", "lb"),
    ("Zoete aardappel", "Groente", r"sweet potato(?!.*fries)", "lb"),
    ("Aardappelen", "Groente", r"potatoes\b(?!.*skins)", "lb"),
    ("Uien / prei / knoflook", "Groente", r"\bonions?\b(?!.*fried)|leeks|garlic(?!.*cubes)", "stuk"),
    ("Wortels", "Groente", r"carrots", "oz"),
    ("Broccoli / bloemkool", "Groente", r"broccoli|cauliflower", "lb"),
    ("Champignons", "Groente", r"mushroom", "oz"),
    ("Overige groente", "Groente", r"radish|celery|kale|cabbage|asparagus|green beans|corn on|lettuce", "stuk"),
    # Fruit
    ("Bananen", "Fruit", r"banana(?!.*blueberry)", "lb"),
    ("Mango", "Fruit", r"mango(?!.*juice)", "stuk"),
    ("Watermeloen / meloen", "Fruit", r"watermelon(?!.*sparkling|.*starburst)|cantaloupe|melon bowl|honeydew", "stuk"),
    ("Blauwe bessen vers", "Fruit", r"blueberries(?!.*frozen)", "oz"),
    ("Aardbeien / frambozen", "Fruit", r"strawberries|raspberries|blackberries", "oz"),
    ("Appels", "Fruit", r"apples\b|gala apple|pink lady", "lb"),
    ("Peren", "Fruit", r"\bpears?\b", "lb"),
    ("Mandarijnen / citrus", "Fruit", r"clementine|mandarin|cuties|lemon - each|\blemons?\b(?!ade)|\blimes?\b", "stuk"),
    ("Overig fruit", "Fruit", r"kiwi|grapes\b|pineapple(?!.*sparkling)|peach(?!.*tea|.*sparkling)", "stuk"),
    ("Rozijnen / gedroogd fruit", "Fruit", r"raisins|dried fruit|dates", "oz"),
    # Diepvries
    ("Wilde blauwe bessen diepvries", "Diepvries", r"frozen.*blueberries|wild blueberries", "oz"),
    ("Diepvriesgroente", "Diepvries", r"frozen.*(peas|butternut|spinach|broccoli|onion|garlic|corn|vegetable|edamame)|edamame|steam.?in.?bag", "oz"),
    ("Vleesvervanger gehakt/burger", "Diepvries", r"plant.?based|impossible|beyond|gardein|morningstar|lightlife|meat free|vegan bacon", "oz"),
    ("Dumplings / potstickers", "Diepvries", r"dumpling|potsticker|wonton", "oz"),
    ("Diepvriessnacks / pizza", "Diepvries", r"farm rich|pizza(?!.*flour)|shark bites|fries|puff pastry|crescent|lean cuisine", "stuk"),
    ("IJs", "Diepvries", r"ice cream|drumstick|yasso|haagen|sundae|blue bell|frozen greek yogurt|acai", "stuk"),
    # Brood en ontbijt
    ("Tortilla's / wraps", "Brood & ontbijt", r"tortilla(?!.*chips)", "stuk"),
    ("Brood", "Brood & ontbijt", r"\bbread\b|baguette|sourdough|bagel|buns\b", "oz"),
    ("Havermout", "Brood & ontbijt", r"\boats\b|oatmeal", "oz"),
    ("Granola / mueslirepen", "Brood & ontbijt", r"granola|nature valley|breakfast bar|kind bar|clif", "stuk"),
    ("Chiazaad / noten", "Brood & ontbijt", r"chia|pistachio|trail mix|mixed nuts|almonds|cashews|walnuts", "oz"),
    ("Pindakaas", "Brood & ontbijt", r"peanut butter", "oz"),
    ("Babyhapjes / knijpzakjes", "Brood & ontbijt", r"applesauce|pouch|puffs|baby food|gerber|happy baby|once upon", "stuk"),
    # Voorraadkast
    ("Pasta", "Voorraadkast", r"penne|rotini|spaghetti|lasagna|pasta(?!.*sauce)|ravioli|fusilli|farfalle", "oz"),
    ("Bloem", "Voorraadkast", r"flour(?!.*tortilla)", "oz"),
    ("Tomaten in blik", "Voorraadkast", r"diced tomatoes|crushed tomatoes|peeled tomatoes|tomato sauce|tomato paste|marinara", "oz"),
    ("Bonen / kikkererwten", "Voorraadkast", r"chickpea|garbanzo|black beans|kidney|cannellini|lentil(?!.*crisps)|beans\b(?!.*green)", "oz"),
    ("Kokosmelk", "Voorraadkast", r"coconut milk(?!.*yogurt)", "floz"),
    ("Mais in blik / soep", "Voorraadkast", r"whole kernel corn|soup|bouillon|broth", "oz"),
    ("Olijven / pesto / sauzen", "Voorraadkast", r"olives|pesto|mayo|ketchup|sriracha|wasabi|soy sauce|mustard|dressing|salsa", "oz"),
    ("Kruiden / olie / azijn", "Voorraadkast", r"curry|salt grinder|pepper grinder|seasoning|olive oil|vinegar(?!.*chips)|spice|cinnamon|paprika powder", "stuk"),
    ("Rijst / couscous / tofu", "Voorraadkast", r"\brice\b|couscous|quinoa|tofu", "oz"),
    ("Tonijn", "Voorraadkast", r"tuna", "oz"),
    # Snacks
    ("Chips", "Snacks", r"chips|doritos|harvest snaps|crisps|kettle|lay's|pringles|popcorn|pretzels", "oz"),
    ("Koek / snoep / gebak", "Snacks", r"cookie|haribo|candy|chocolate(?!.*yogurt)|marshmallow|cheesecake|sticky buns|muffin|cake", "stuk"),
    ("Crackers", "Snacks", r"cracker|triscuit|goldfish|wheat thins", "oz"),
]
GROEP_RE = [(g, a, re.compile(r, re.I), e) for g, a, r, e in GROEPEN]

# Winkels die geen boodschappen zijn (maaltijdboxen, restaurants, abonnementen)
GEEN_BOODSCHAPPEN = r"taco bell|fadi|aga's|home chef|green chef|hellofresh|dashpass|instacart\+|too good"


def groep_van(naam):
    for g, a, r, e in GROEP_RE:
        if r.search(naam):
            return g, a, e
    return "Overig", "Overig", "stuk"


MAAT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(fl\.? ?oz|fluid ounces|oz|onz|lbs?|pound|ct|count|pk|pack|each)\b", re.I)
PAK_RE = re.compile(r"(\d+)\s*(?:pk|ct|pack|count)\s*/\s*(\d+(?:\.\d+)?)\s*(fl oz|oz)", re.I)


def inhoud(tekst, eenheid):
    """Hoeveelheid per verpakking in de gevraagde eenheid (oz, floz, lb, stuk)."""
    t = str(tekst)
    m = PAK_RE.search(t)
    if m and eenheid in ("oz", "floz"):
        return float(m.group(1)) * float(m.group(2))
    vonden = {}
    for getal, soort in MAAT_RE.findall(t):
        s = soort.lower().replace(".", "").replace(" ", "")
        s = {"onz": "oz", "fluidounces": "floz", "lbs": "lb", "pound": "lb",
             "count": "ct", "pack": "ct", "pk": "ct", "each": "ct"}.get(s, s)
        vonden.setdefault(s, float(getal))
    if eenheid == "floz":
        if "floz" in vonden:
            return vonden["floz"]
        if "oz" in vonden:
            return vonden["oz"]
    if eenheid == "oz":
        if "oz" in vonden:
            return vonden["oz"]
        if "floz" in vonden:
            return vonden["floz"]
        if "lb" in vonden:
            return vonden["lb"] * 16
    if eenheid == "lb":
        if "lb" in vonden:
            return vonden["lb"]
        if "oz" in vonden:
            return vonden["oz"] / 16
    if eenheid == "stuk":
        if "ct" in vonden:
            return vonden["ct"]
        return 1.0
    return None


def lees_kroger():
    k = pd.read_csv(B / "kroger_artikelen_2026.csv")
    k["winkel"] = "Kroger"
    k["aantal_txt"] = k.ontvangen.astype(str)
    gewicht = k.aantal_txt.str.extract(r"([\d.]+)\s*lbs", expand=False).astype(float)
    k["lb"] = gewicht
    k["aantal"] = pd.to_numeric(k.aantal_txt.str.extract(r"^(\d+)", expand=False), errors="coerce")
    k.loc[k.lb.notna(), "aantal"] = 1
    k["bedrag"] = k.betaald
    k["normaal"] = k.normaalprijs
    k["korting"] = (k.normaal - k.bedrag).clip(lower=0).round(2)
    k["aanbieding"] = (k.korting > 0.05) & (k.bedrag > 0)
    k["elp"] = k.everyday_low_price.eq("ja")
    return k[["datum", "winkel", "artikel", "maat", "aantal", "lb", "bedrag", "normaal",
              "korting", "aanbieding", "elp", "actie"]]


def lees_gmail():
    t = pd.read_csv(B / "gmail_target_eten_artikelen.csv")
    t = t[~t.winkel.str.contains(GEEN_BOODSCHAPPEN, case=False)]
    t["winkel"] = t.winkel.str.replace(r"^DoorDash - ", "", regex=True) \
        .str.replace(r" \(via Instacart\)| Farmers Market", "", regex=True) \
        .str.replace("Sprouts Farmers Market", "Sprouts")
    t["artikel"] = t.artikel.str.replace(r"^[^:]{3,40}: ", "", regex=True)
    t["maat"] = ""
    t["lb"] = None
    t["bedrag"] = pd.to_numeric(t.regeltotaal, errors="coerce")
    # Kortingen op de hele bestelling (Circle-acties, coupons, Circle Card 5%)
    # naar rato over de artikelen verdelen, maar alleen als de artikelprijzen
    # nog vóór korting zijn (artikelen tellen op tot het subtotaal).
    o = pd.read_csv(B / "gmail_target_eten_orders.csv")
    o = o[o.soort != "retour"].drop_duplicates("order_id")
    som = t.groupby("order_id").bedrag.sum()
    o["som"] = o.order_id.map(som)
    o["factor"] = 1.0
    voor_korting = (o.som - o.subtotaal).abs() <= 1
    o.loc[voor_korting & (o.korting > 0), "factor"] = 1 - o.korting / o.subtotaal
    t["factor"] = t.order_id.map(o.set_index("order_id").factor).fillna(1.0)
    t["normaal"] = t.bedrag
    t["bedrag"] = (t.bedrag * t.factor).round(2)
    t["korting"] = (t.normaal - t.bedrag).round(2)
    t["aanbieding"] = t.factor < 0.99
    t["elp"] = False
    t["actie"] = ""
    return t[["datum", "winkel", "artikel", "maat", "aantal", "lb", "bedrag", "normaal",
              "korting", "aanbieding", "elp", "actie"]]


def bouw():
    a = pd.concat([lees_kroger(), lees_gmail()], ignore_index=True)
    a = a[a.bedrag.fillna(0) >= 0]
    gi = a.artikel.map(groep_van)
    a["groep"] = gi.str[0]
    a["afdeling"] = gi.str[1]
    a["eenheid"] = gi.str[2]

    def per_eenheid(r):
        aantal = r.aantal if pd.notna(r.aantal) and r.aantal > 0 else 1
        if r.eenheid == "lb" and pd.notna(r.lb):
            hoeveel = r.lb
        else:
            stuk = inhoud(f"{r.maat} {r.artikel}", r.eenheid)
            if stuk is None:
                return None
            hoeveel = stuk * aantal
        # gratis artikelen (Buy 1 Get 1) tellen mee via het betaalde artikel; los niet meenemen
        if r.bedrag == 0:
            return None
        prijs = r.bedrag
        return round(prijs / hoeveel, 4) if hoeveel else None

    a["prijs_per_eenheid"] = a.apply(per_eenheid, axis=1)
    a["normaal_per_eenheid"] = a.apply(
        lambda r: round(r.prijs_per_eenheid * r.normaal / r.bedrag, 4)
        if pd.notna(r.prijs_per_eenheid) and pd.notna(r.normaal) and r.bedrag > 0 else None, axis=1)
    a.to_csv(UIT / "boodschappen_artikelen.csv", index=False)

    maanden = (pd.to_datetime(a.datum).max() - pd.to_datetime(a.datum).min()).days / 30.4
    g = a.groupby(["afdeling", "groep", "eenheid"]).agg(
        keer=("datum", "nunique"), totaal=("bedrag", "sum"), korting=("korting", "sum")).reset_index()
    g["per_maand"] = (g.totaal / maanden).round(1)
    for w in ["Kroger", "Target", "H-E-B", "ALDI", "Sprouts"]:
        s = a[a.winkel == w].groupby("groep").prijs_per_eenheid.median()
        g[f"{w}_p_eenh"] = g.groep.map(s).round(3)
    ka = a[a.winkel == "Kroger"].groupby("groep").agg(
        kroger_keer=("datum", "count"), kroger_aanbieding=("aanbieding", "mean"))
    g = g.merge(ka, left_on="groep", right_index=True, how="left")
    g["kroger_aanbieding"] = (g.kroger_aanbieding * 100).round(0)
    g = g.sort_values("totaal", ascending=False)
    g.to_csv(UIT / "boodschappen_groepen.csv", index=False)
    return a, g, maanden


if __name__ == "__main__":
    a, g, maanden = bouw()
    pd.set_option("display.width", 250)
    print(f"{len(a)} regels, {maanden:.1f} maanden, totaal ${a.bedrag.sum():,.0f}")
    print(a.groupby("winkel").bedrag.sum().round(0).sort_values(ascending=False).to_string())
    print(g.to_string(index=False))
    ov = a[a.groep == "Overig"].groupby("artikel").bedrag.sum().sort_values(ascending=False)
    print(f"\nOverig: ${ov.sum():,.0f} in {len(ov)} artikelen")
    print(ov.head(60).to_string())
