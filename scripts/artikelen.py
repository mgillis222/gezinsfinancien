"""Artikelen indelen en Amazon-afschrijvingen verdelen over de echte categorieën.

"Online winkelen" is geen categorie maar een manier van kopen. Een Amazon-afschrijving op de bank zegt niet wat
er gekocht is, maar de bestelgeschiedenis wel. Daarom wordt elke Amazon-afschrijving verdeeld volgens de
artikelen die die maand bij Amazon zijn besteld.
"""
import re
import pandas as pd

AMAZON_REGELS = [
    (r"baby|infant|toddler|crib|nipple|breast|lactation|nursing|postpartum|swaddle|pacifier|bottle brush|bath tub|frida|momcozy|lansinoh|medela|colostrum|flange|stroller|car seat|booster|registry|tripp trapp|high chair", "Baby & zwangerschap"),
    (r"kids|toy|puzzle|game|sticker|coloring|crayon|bath bomb|beach toys|bubble|pop tubes|monster truck|spidey|little people|matching memory|bluey|keyboard|casio", "Kinderen & speelgoed"),
    (r"saline|nasal|scar|sunscreen|repellent|shampoo|supplement|lecithin|vitamin|nail clipper|toothbrush|hair dryer|mirror|makeup|waist tightener|underwear", "Verzorging & gezondheid"),
    (r"banana|cheese|oatmilk|cranberry|juice|olive oil|pear|pita|muffin|onion|crystal light|coca-cola|impossible|figs|brie|boursin|cottage|coffee", "Boodschappen"),
    (r"rv |camper|trailer|fuse|leveling|dinette|fluid film|breakaway|canopy tent|solar shower|carabiner|refrigerator vent|camping|door latch", "Camper & kamperen"),
    (r"paint|primer|polycrylic|sandpaper|roller|drop cloth|tack cloth|heat gun|painters tape|contact paper|countertop|window covering|vinyl wrap", "Klussen (verf, camper/huis)"),
    (r"curtain|sheet|mattress|bed frame|duvet|comforter|doormat|mat |hooks|ice cube|mason jar|pizza stone|egg|air fryer|bread bags|melon baller|squeegee|faucet cover|zipper pouch|storage|insect trap|humidifier|fan", "Huis & keuken"),
    (r"bike|tire|cleat|shimano|camelbak|pilates|exercise ball|yoga|swim goggles|cycling", "Sport & fietsen"),
    (r"yarn|crochet|stuffing|fiberfill|sewing|velcro|beads|journal|notebook|pens", "Hobby & schrijven"),
    (r"charger|power bank|battery|cable|headphones|earbuds|shokz", "Elektronica"),
    (r"gift card|thank you cards|valentine|welcome to texas|book|cards", "Cadeaus, boeken & kaarten"),
    (r"shirt|carhartt|socks|mailer", "Kleding & overig"),
]

# Artikelcategorie -> (hoofdcategorie, subcategorie) in het overzicht.
NAAR_HOOFD = {
    "Baby & zwangerschap": ("Kinderen", "Baby & zwangerschap (Amazon)"),
    "Kinderen & speelgoed": ("Kinderen", "Speelgoed & kinderspullen (Amazon)"),
    "Verzorging & gezondheid": ("Zorg", "Drogisterij & verzorging (Amazon)"),
    "Boodschappen": ("Boodschappen", "Amazon Fresh & boodschappen"),
    "Camper & kamperen": ("Reizen & uitjes", "Camper & kampeerspullen (Amazon)"),
    "Klussen (verf, camper/huis)": ("Huis & inrichting", "Klussen (Amazon)"),
    "Huis & keuken": ("Huis & inrichting", "Huis & keuken (Amazon)"),
    "Sport & fietsen": ("Sport & hobby", "Sport & fietsen (Amazon)"),
    "Hobby & schrijven": ("Sport & hobby", "Hobby (Amazon)"),
    "Elektronica": ("Elektronica", "Elektronica (Amazon)"),
    "Cadeaus, boeken & kaarten": ("Giften", "Cadeaus, boeken & kaarten (Amazon)"),
    "Kleding & overig": ("Kleding & persoonlijk", "Kleding (Amazon)"),
    "Overig": ("Huis & inrichting", "Overig (Amazon)"),
}


def amazon_cat(naam):
    for patroon, cat in AMAZON_REGELS:
        if re.search(patroon, naam, re.I):
            return cat
    return "Overig"


def amazon_artikelen():
    ao = pd.read_csv("data/bestellingen/amazon_bestellingen_2026.csv")
    aa = pd.read_csv("data/bestellingen/amazon_artikelen_2026.csv")
    aa = aa[~aa["order_id"].isin(ao[ao["geannuleerd"] == "ja"]["order_id"])].copy()
    aa["regeltotaal"] = aa["aantal"] * aa["prijs_per_stuk"]
    aa["cat"] = aa["artikel"].map(amazon_cat)
    return ao, aa


def verdeel_amazon(t):
    """Vervangt elke bankregel 'Amazon' door regels per categorie, naar verhouding van wat die maand is besteld."""
    _, aa = amazon_artikelen()
    aa["periode"] = aa["datum"].str.slice(0, 7)
    totaal = aa.groupby("cat")["regeltotaal"].sum()
    aandeel_alles = totaal / totaal.sum()
    per_maand = {p: g.groupby("cat")["regeltotaal"].sum() / g["regeltotaal"].sum() for p, g in aa.groupby("periode")}

    is_amazon = t["subcategorie"] == "Amazon"
    nieuw = []
    for _, r in t[is_amazon].iterrows():
        p = pd.Timestamp(r["datum"]).strftime("%Y-%m")
        aandeel = per_maand.get(p, aandeel_alles)
        rest = round(r["bedrag_usd"], 2)
        items = list(aandeel.items())
        for i, (cat, a) in enumerate(items):
            deel = rest if i == len(items) - 1 else round(r["bedrag_usd"] * a, 2)
            rest = round(rest - deel, 2)
            hoofd, sub = NAAR_HOOFD[cat]
            k = r.copy()
            k["bedrag_usd"] = deel
            k["bedrag_orig"] = deel
            k["categorie"], k["subcategorie"] = hoofd, sub
            k["omschrijving"] = f"{r['omschrijving']} (deel: {cat})"
            nieuw.append(k)
    return pd.concat([t[~is_amazon], pd.DataFrame(nieuw)], ignore_index=True)
