"""Bouwt één tabel met alle geldstromen (Chase + Target-kaart + Knab), in dollars, ingedeeld in categorieën.

Invoer:  data/verwerkt/chase_transacties.csv (lees_chase.py), data/afschriften/Knab*.csv, data/ecb_ruw.csv
Uitvoer: data/verwerkt/alle_transacties.csv  en  data/verwerkt/twijfelgevallen.csv

Soorten:
  uitgave   - echt geld weg (telt mee in het uitgavenoverzicht)
  inkomen   - echt geld binnen
  intern    - tussen eigen rekeningen / creditcard aflossen / EUR->USD wissel (telt nergens mee)
  sparen    - naar spaar- of beleggingsrekening (geen uitgave, wel weg van de betaalrekening)
De regels staan bovenaan, zodat je ze makkelijk kunt aanpassen of aanvullen.
"""
import re, glob
import pandas as pd

# (zoekpatroon, soort, categorie, subcategorie). Eerste match wint. Patronen zijn hoofdletterongevoelig.
REGELS = [
    # --- intern: aflossingen, eigen rekeningen, wissels ---
    (r"payment to chase card|payment thank you|chase credit crd autopay|automatic payment", "intern", "Intern", "Creditcard aflossen"),
    (r"e-pay target\.com|target card srvc payment|auto payment - thanks", "intern", "Intern", "Creditcard aflossen"),
    (r"online transfer (to|from) (sav|chk)", "intern", "Intern", "Eigen rekening Chase"),
    (r"real time transfer recd.*wise|via wise", "intern", "Intern", "Wise EUR→USD (ontvangen)"),
    (r"^knab: wise", "intern", "Intern", "Wise EUR→USD (verstuurd)"),
    (r"^knab: (m\. m\. d\. gillis|myrthe gillis|gillis myrthe)", "intern", "Intern", "Eigen rekening Knab"),
    (r"transfer to cds", "sparen", "Sparen & beleggen", "Chase CD (deposito)"),
    (r"interactive brok", "sparen", "Sparen & beleggen", "Interactive Brokers"),
    (r"brand new day", "sparen", "Sparen & beleggen", "Kinderrekening Brand New Day"),
    # --- inkomen ---
    (r"fusa land disb emp exp", "intern", "Werkreis (vergoed)", "Onkostenvergoeding Fugro (werkreizen)"),
    (r"fusa land disb payroll", "inkomen", "Inkomen", "Salaris Jef"),
    (r"lincoln nationa", "inkomen", "Inkomen", "Uitkering (Lincoln)"),
    (r"irs treas.*tax ref", "inkomen", "Inkomen", "Belastingteruggave VS"),
    (r"^knab: picnic", "inkomen", "Inkomen", "Inkomen Myrthe (freelance)"),
    (r"^knab: hr nj griffin", "inkomen", "Inkomen", "Huur woning NL ontvangen"),
    (r"^knab: fugro", "sparen", "Sparen & beleggen", "Aandelen Fugro (Jef)"),
    (r"^knab: peeters inneke", "uitgave", "Ondersteuning familie", "Schoonmoeder (Inneke)"),
    (r"^knab: bear graphics", "uitgave", "Kinderen", "Geboortekaartjes Bill"),
    (r"zelle payment to nancy herrera", "uitgave", "Huishouden", "Schoonmaak (Nancy)"),
    (r"zelle payment to (avertano rendon|evelyna rozenfeld)", "uitgave", "Kinderopvang", "Oppas"),
    (r"^knab: (jef michielssen|j\. michielssen)", "intern", "Intern", "Van/naar rekening Jef (buiten overzicht)"),
    (r"zelle payment from|^knab: (gillis - reyniers|van den bergh|michielssen|marie michielssen|de h |de hoon|verheye|pauwels|aab inz tikkie|av ferreira|s\.t\. leo|olivia rowaert|bondroit|koen \|)", "inkomen", "Inkomen", "Van familie/vrienden (of terugbetaling)"),
    (r"^knab: taf bv", "uitgave", "Verzekeringen", "Levensverzekering (NL)"),
    (r"^knab: international card services", "uitgave", "Abonnementen", "ICS-creditcard: ChatGPT (t/m mrt) + jaarbijdrage"),
    (r"^knab: paypal", "uitgave", "Nog indelen", "PayPal vanaf Knab (zie Gmail)"),
    (r"^knab: .*\| betaalautomaat", "uitgave", "Reizen & uitjes", "Pinnen tijdens vakantie Europa"),
    # --- wonen ---
    (r"spencerspizzy|zelle payment to spencer moore", "uitgave", "Wonen VS", "Huur Cottondale Ct"),
    (r"^knab: vista hypotheken", "uitgave", "Woning NL", "Hypotheek"),
    (r"^knab: vve", "uitgave", "Woning NL", "VvE-bijdrage"),
    (r"^knab: (gemeente den haag|regionale belasting)", "uitgave", "Woning NL", "Gemeentelijke belastingen"),
    (r"^knab: quooker", "uitgave", "Woning NL", "Onderhoud"),
    (r"^knab: ziggo", "uitgave", "Woning NL", "Ziggo (eindafrekening)"),
    # --- kinderen ---
    (r"primrose school", "uitgave", "Kinderopvang", "Primrose (Lily & Bill)"),
    # FSA-terugbetalingen (naam beheerder nog onbekend): verlagen de nettokosten van de opvang.
    (r"dependent care|dep care|dcfsa|\bfsa\b|healthequity", "intern", "Intern", "FSA-terugbetaling (eigen geld)"),
    (r"ymca houston|little gym|kid to kid|scholastic|sharkeys cuts for kids|mckenna childrens|bugaboo|babylist|hanna|love ?to ?dream|little unicorn|artipoppe", "uitgave", "Kinderen", "Kinderen (activiteiten, kleding, spullen)"),
    # --- vaste lasten VS ---
    (r"cinco mud|gexa energy|centerpoint|cpenergy|utility payment fee", "uitgave", "Nutsvoorzieningen", "Water/stroom/gas"),
    (r"att payment|at&t prepaid|vesta \*at&t", "uitgave", "Telefoon & internet", "AT&T"),
    (r"^knab: kpn", "uitgave", "Telefoon & internet", "KPN (NL)"),
    (r"progressive|geico", "uitgave", "Verzekeringen", "Autoverzekering"),
    (r"travel insured", "uitgave", "Verzekeringen", "Reisverzekering"),
    # --- boodschappen ---
    (r"kroger fuel|costco gas|h-e-b gas|buc-ee|shell|chevron|exxon|sunoco|speedway|marathon|phillips 66|valero|dell valley oil|7-eleven", "uitgave", "Vervoer", "Brandstof"),
    (r"kroger|trader joe|h-e-b|heb |costco whse|aldi|sprouts|randalls|h mart|wal-mart|walmart|wm supercenter|instacart|amazon groce|delhaize|albert heijn|lidl|whole foods|kare market", "uitgave", "Boodschappen", "Supermarkt"),
    (r"target", "uitgave", "Boodschappen", "Target (boodschappen + huishouden)"),
    (r"amazon prime|prime video", "uitgave", "Abonnementen", "Streaming, software, nieuws"),
    (r"amazon|amzn", "uitgave", "Online winkelen", "Amazon"),
    (r"hellofresh|green ?chef|home ?chef|factor", "uitgave", "Eten & drinken", "Maaltijdboxen"),
    # Specifieke uitzonderingen vóór de brede eten-regel (Square/Toast-terminals worden ook door niet-horeca gebruikt).
    (r"aramark methodist|amk hmw cafe", "uitgave", "Zorg", "Ziekenhuis (bevalling)"),
    (r"spacecntrhoustoncafe|armk dp concessions", "uitgave", "Reizen & uitjes", "Uitjes & tickets"),
    (r"wl1 cafe", "uitgave", "Eten & drinken", "Lunch Jef op werk"),
    (r"^dd |doordash", "uitgave", "Boodschappen", "DoorDash/DashMart (deals)"),
    (r"practice with bell|dermatolog", "uitgave", "Zorg", "Zorg & medisch"),
    (r"river forest haven", "uitgave", "Reizen & uitjes", "Reizen, hotels, vluchten"),
    (r"scspacetrader", "uitgave", "Reizen & uitjes", "Uitjes & tickets"),
    (r"github", "uitgave", "Abonnementen", "Streaming, software, nieuws"),
    (r"^knab: npo", "uitgave", "Abonnementen", "Streaming, software, nieuws"),
    (r"too good to go|farmer'?s fridge|lunchdrop|fooda", "uitgave", "Eten & drinken", "Lunch/snacks onderweg"),
    (r"^dd |doordash|uber \*eats|ubereats", "uitgave", "Eten & drinken", "Bezorging (DoorDash/Uber Eats)"),
    (r"nespresso|athletic br|specs|vinatis|vinify", "uitgave", "Eten & drinken", "Koffie & drank"),
    (r"tst\*|sq \*|starbucks|restaurant|grill|cafe|coffee|ramen|sushi|taco|burger|pizza|deli|gelato|donut|dessert|poke|steakhouse|wendy|in-n-out|bbq|barbecue|kitchen|bistro|brew|confection|sweet|dish society|byblos|jinya|delices|icehous|oasis|mexican|thai|chop |lynns table|daily gather|uncles|home run food|eric kayser|zoete|zoet genot|olivier|cabane|more than cake|xavirous|le breton|lescombes|winery|armk|aramark|concession", "uitgave", "Eten & drinken", "Uit eten & koffie"),
    # --- vervoer ---
    (r"hctra|ez tag", "uitgave", "Vervoer", "Tol (EZ TAG)"),
    (r"uber|lyft", "uitgave", "Vervoer", "Uber/taxi"),
    (r"parking|propark|laz parking|garag|stparkeergeld", "uitgave", "Vervoer", "Parkeren"),
    (r"toyota|car ?wash|virtual ?drive|tx dps|camping world|gander rv|good sam", "uitgave", "Vervoer", "Auto (onderhoud, rijbewijs, RV)"),
    # --- zorg ---
    (r"fyzical|methodist|jenkins|obstet|blue fish|labcorp|quest|cvs|walgreens|aeroflow|med\*|phr\*|mychart|ultrasound|childrens hosp|access total care|pt billing|chop", "uitgave", "Zorg", "Zorg & medisch"),
    # --- reizen ---
    (r"vrbo|vacasa|virgin cruises|trip\.com|recreation\.gov|state parks|tex state pks|nm state parks|hipcamp|amtrak|klm|transavia|booking|bkg\*|hotel|hilton|radisson|hyatt|aloft|sleep inn|bluegreen|resort|glamping|houston airports|iah |atl airp|safari|beekse bergen|airbnb|ns internationaal|big bend|wnpa|carlsbad|eilan|river forest|breeze|marleyspoo|sentinel|canada|toronto|mississauga|seaworld", "uitgave", "Reizen & uitjes", "Reizen, hotels, vluchten"),
    (r"space cent|museum|aquarium|symphony|polo club|axs\.com|stubhub|nature cent|varner hogg|special event|texas gun club|land van ooit|monkey town", "uitgave", "Reizen & uitjes", "Uitjes & tickets"),
    # --- persoonlijk & huis ---
    (r"patagonia|tecovas|tommy hilfiger|hollister|poshmark|tjmaxx|uptown cheapskate|backcountry|competitive cyclist|ryzon|sephora|warby parker|showroompriv|veepee|sellhelp|vinted", "uitgave", "Kleding & persoonlijk", "Kleding, schoenen, verzorging"),
    (r"great clips|aurea|salon", "uitgave", "Kleding & persoonlijk", "Kapper"),
    (r"trek|cool cat cycles|4iiii|bass pro|ride magazine", "uitgave", "Sport & hobby", "Fietsen, sport"),
    (r"etsy|el baker art|motiff|yarn", "uitgave", "Sport & hobby", "Hobby (haken, kunst)"),
    (r"ikea|home depot|lowe'?s|harbor freight|wayfair|sur la table|officemax|postnet|ups store|usps|postnl|bpost|pakske", "uitgave", "Huis & inrichting", "Huis, inrichting, post"),
    (r"apple store|bestbuy|best buy", "uitgave", "Elektronica", "Elektronica"),
    (r"groupon", "uitgave", "Reizen & uitjes", "Uitjes & tickets"),                       # SeaWorld, Costco-lidmaatschap
    (r"five below", "uitgave", "Kinderen", "Kinderen (activiteiten, kleding, spullen)"),
    (r"walmart\.com", "uitgave", "Zorg", "Drogisterij & verzorging"),                      # vitamines, oorkappen
    (r"bol\.?com", "uitgave", "Sport & hobby", "Boeken & e-books"),
    (r"fotoproducten|photoaid|passport", "uitgave", "Overheid & documenten", "Paspoorten, aktes, vertalingen"),
    (r"temu", "uitgave", "Huis & inrichting", "Temu (inhoud onbekend)"),
    # --- abonnementen ---
    (r"claude|anthropic|openai|chatgpt", "uitgave", "Abonnementen", "AI (Claude e.d.)"),
    (r"microsoft|linkedin|nord|apple\.com/bill|disney|netflix|spotify|podimo|videoland|npo|prime video|amazon prime|storytel|hbo|consumentenbond|correspondent|coursera|google|amazon media|canvascompa", "uitgave", "Abonnementen", "Streaming, software, nieuws"),
    (r"^knab: knab$|foreign transaction fee|official checks charge|money order|^knab: knab ", "uitgave", "Bankkosten", "Bank- en wisselkosten"),
    (r"milieudefensie|unicef|enthuse|donation", "uitgave", "Giften", "Goede doelen"),
    (r"tx birth death|consulate|he-government|lexicom", "uitgave", "Overheid & documenten", "Paspoorten, aktes, vertalingen"),
    (r"kovasovic|two t'?s|the shack|pullman market|mexology", "uitgave", "Eten & drinken", "Uit eten & koffie"),
    (r"stand for the silent", "uitgave", "Giften", "Goede doelen"),
    (r"zelle payment to", "uitgave", "Nog indelen", "Zelle aan personen"),
    (r"atm withdrawal", "uitgave", "Contant geld", "Pinautomaat"),
    (r"^withdrawal$", "uitgave", "Nog indelen", "Opname aan de balie / cashier's check"),  # 9 jan: zie hieronder (camper)
]
TWIJFEL_SUB = {"Van familie/vrienden (of terugbetaling)", "PayPal vanaf Knab (zie Gmail)"}

def koersen():
    e = pd.read_csv("data/ecb_ruw.csv", usecols=["TIME_PERIOD", "OBS_VALUE"])
    e.columns = ["datum", "eur_usd"]; e["datum"] = pd.to_datetime(e["datum"])
    alle = pd.DataFrame({"datum": pd.date_range("2025-11-25", "2026-10-10")})
    return alle.merge(e, how="left").ffill().bfill()  # weekend = laatste werkdagkoers

def lees_chase():
    c = pd.read_csv("data/verwerkt/chase_transacties.csv")
    c["bank"] = "Chase"; c["valuta"] = "USD"; c["bedrag_orig"] = c["bedrag"]
    c["tegenpartij"] = ""
    return c

def lees_knab():
    dfs = []
    for f in glob.glob("data/afschriften/Knab*.csv"):
        d = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8")
        dfs.append(d)
    k = pd.concat(dfs)
    teken = k["CreditDebet"].map({"Bijschrijvingen": 1, "Afschrijvingen": -1})
    out = pd.DataFrame({
        "datum": pd.to_datetime(k["Transactiedatum"], format="%d-%m-%Y").dt.strftime("%Y-%m-%d"),
        "rekening": k["Rekeningnummer"].str[-4:],
        "soort_rekening": "bank",
        "tegenpartij": k["Tegenrekeninghouder"].fillna(""),
        "omschrijving": "Knab: " + k["Tegenrekeninghouder"].fillna("") + " | " + k["Omschrijving"].fillna("") + " | " + k["Betaalwijze"].fillna(""),
        "bedrag_orig": k["Bedrag"].str.replace(",", ".").astype(float) * teken,
        "afschrift": "Knab",
    })
    out["bank"] = "Knab"; out["valuta"] = "EUR"
    return out

def lees_fsa():
    """HealthEquity-exports (data/fsa/). Inleg via salaris = inkomen (deel van het salaris van Jef);
    zorgbetalingen met de FSA-kaart = uitgave Zorg; 'Pay Me Back' naar Jef = intern (eigen geld terug)."""
    rijen = []
    for f in glob.glob("data/fsa/*.csv*"):
        d = pd.read_csv(f, skiprows=4, encoding="utf-8-sig")
        prog = d["Program"].iloc[0]
        betaaldagen = []
        for _, r in d.iterrows():
            datum = pd.to_datetime(r["Reference Date"]).strftime("%Y-%m-%d")
            b, typ, oms = float(r["Amount"]), r["Transaction Type"], str(r["Description"]).replace("&amp;", "&")
            if typ == "Funding" and "Payroll" in oms:
                betaaldagen.append(datum)
                rijen.append((datum, prog, f"FSA {prog}: inleg via salaris", b, "inkomen", "Inkomen", "Salaris Jef (via FSA-inleg)"))
            elif typ == "Funding":   # Health FSA: jaarbedrag staat op dag 1 klaar; inleg per salaris volgt hieronder
                continue
            elif typ == "Payment":
                rijen.append((datum, prog, f"FSA {prog}: uitbetaald aan {oms}", b, "intern", "Intern", "FSA-terugbetaling (eigen geld)"))
            else:
                rijen.append((datum, prog, f"FSA-kaart: {oms}", b, "uitgave", "Zorg", "Zorg via Health FSA-kaart"))
        if prog == "Healthcare":
            # Inleg $3.400/jaar = $130,77 per salaris; gebruik de salarisdata uit de Dependent Care-export.
            dc = glob.glob("data/fsa/*Dependent*")
            if dc:
                dd = pd.read_csv(dc[0], skiprows=4, encoding="utf-8-sig")
                for x in dd[dd["Description"].str.contains("Payroll", na=False)]["Reference Date"]:
                    rijen.append((pd.to_datetime(x).strftime("%Y-%m-%d"), "Healthcare", "FSA Healthcare: inleg via salaris (3400/26)",
                                  round(3400 / 26, 2), "inkomen", "Inkomen", "Salaris Jef (via FSA-inleg)"))
    out = pd.DataFrame(rijen, columns=["datum", "rekening", "omschrijving", "bedrag_orig", "soort", "categorie", "subcategorie"])
    out["bank"] = "HealthEquity"; out["valuta"] = "USD"; out["soort_rekening"] = "fsa"; out["afschrift"] = "HealthEquity"
    return out

def deel_in(omschr):
    for patroon, soort, cat, sub in REGELS:
        if re.search(patroon, omschr, re.I):
            return soort, cat, sub
    return "uitgave", "Nog indelen", "Onbekend"

def main():
    t = pd.concat([lees_chase(), lees_knab()], ignore_index=True)
    t["datum"] = pd.to_datetime(t["datum"])
    t = t.merge(koersen(), on="datum", how="left")
    t["bedrag_usd"] = t.apply(lambda r: r["bedrag_orig"] * (r["eur_usd"] if r["valuta"] == "EUR" else 1), axis=1).round(2)
    # Knab: tegenpartij vooraan zodat de ^knab:-regels werken; omschrijving in lower voor matchen
    ind = t["omschrijving"].map(lambda s: deel_in(re.sub(r"\s+", " ", str(s)).strip()))
    t[["soort", "categorie", "subcategorie"]] = pd.DataFrame(ind.tolist(), index=t.index)
    # FSA-rekeningen (HealthEquity) zijn al ingedeeld bij het inlezen.
    f = lees_fsa(); f["datum"] = pd.to_datetime(f["datum"]); f["eur_usd"] = None; f["bedrag_usd"] = f["bedrag_orig"]
    t = pd.concat([t, f], ignore_index=True)
    # Geld dat naar familie/vrienden gaat is geen negatief inkomen maar een gift/cadeau.
    gift = (t["subcategorie"] == "Van familie/vrienden (of terugbetaling)") & (t["bedrag_usd"] < 0)
    t.loc[gift, ["soort", "categorie", "subcategorie"]] = ["uitgave", "Giften", "Cadeaus aan familie/vrienden"]
    # Familie/vrienden nader uitsplitsen op basis van de omschrijving.
    fam = t["subcategorie"].isin(["Van familie/vrienden (of terugbetaling)", "Cadeaus aan familie/vrienden"])
    oms = t["omschrijving"].str.lower()
    regels_fam = [
        (oms.str.contains("cruise|vakantie|weekend|rodeo|oostduinkerke|afrekening houston"), ["uitgave", "Reizen & uitjes", "Terugbetaald door reisgenoten"]),
        (oms.str.contains("gillis - reyniers") & oms.str.contains("selfcare"), ["inkomen", "Inkomen", "Bijdrage ouders (selfcare)"]),
        (oms.str.contains("gillis - reyniers") & ~oms.str.contains("selfcare"), ["intern", "Lening ouders", "Lening ouders (geleend / terugbetaald)"]),
        (oms.str.contains("strava"), ["uitgave", "Abonnementen", "Streaming, software, nieuws"]),
        (oms.str.contains("bill|birthday|cadeau jef") & (t["bedrag_usd"] > 0), ["inkomen", "Inkomen", "Cadeaus ontvangen"]),
    ]
    for masker, waarden in regels_fam:
        t.loc[fam & masker, ["soort", "categorie", "subcategorie"]] = waarden
    # Uit eten buiten de regio Katy/Houston = eten tijdens reizen en uitjes (apart van dagelijks uit eten).
    lokaal = t["omschrijving"].str.contains(r"katy|houston|sugar ?land|fulshear|richmond|cypress|spring tx|cinco r|^knab:", case=False, regex=True)
    reis = (t["subcategorie"] == "Uit eten & koffie") & (~lokaal | t["omschrijving"].str.contains(r"\bIAH\b|airport", case=False, regex=True))
    t.loc[reis, ["categorie", "subcategorie"]] = ["Reizen & uitjes", "Eten tijdens reizen & uitjes"]
    # Werkreis Jef naar Toronto (8-16 jan 2026): via het salaris vergoed (bevestigd door Myrthe).
    # De kosten en een even groot deel van het januarisalaris tellen allebei als intern.
    toronto = (t["datum"] >= "2026-01-08") & (t["datum"] <= "2026-01-16") & t["omschrijving"].str.contains(r" ON$|ONTARIO|CANADA|YYZ|\bIAH\b", case=False, regex=True) & (t["bedrag_usd"] < 0)
    t.loc[toronto, ["soort", "categorie", "subcategorie"]] = ["intern", "Werkreis (vergoed)", "Werkreis Toronto Jef"]
    # PayPal-incasso's vanaf Knab koppelen aan de bestelling uit Gmail (zelfde bedrag in euro).
    PAYPAL_EUR = {2375.00: ("Reizen & uitjes", "Reizen, hotels, vluchten"),          # Booking.com Oostduinkerke
                  134.56: ("Reizen & uitjes", "Reizen, hotels, vluchten"),           # KLM
                  120.96: ("Reizen & uitjes", "Reizen, hotels, vluchten"), 80.25: ("Reizen & uitjes", "Reizen, hotels, vluchten"),
                  7.00: ("Reizen & uitjes", "Reizen, hotels, vluchten"),             # Uber Frankrijk (sep)
                  98.60: ("Kleding & persoonlijk", "Kinderkleding tweedehands (Sellpy)"), 16.37: ("Kleding & persoonlijk", "Kinderkleding tweedehands (Sellpy)"),
                  25.81: ("Kleding & persoonlijk", "Kinderkleding tweedehands (Sellpy)"),
                  153.73: ("Kleding & persoonlijk", "Kleding, schoenen, verzorging"), 31.06: ("Kleding & persoonlijk", "Kleding, schoenen, verzorging"),
                  56.29: ("Kleding & persoonlijk", "Kleding, schoenen, verzorging"), 87.88: ("Kleding & persoonlijk", "Kleding, schoenen, verzorging"),
                  19.99: ("Abonnementen", "Streaming, software, nieuws"), 31.34: ("Abonnementen", "Streaming, software, nieuws"),
                  30.00: ("Huis & inrichting", "Huis, inrichting, post")}
    pp = t["subcategorie"] == "PayPal vanaf Knab (zie Gmail)"
    for bedrag, (cat, sub) in PAYPAL_EUR.items():
        m = pp & ((t["bedrag_orig"] + bedrag).abs() < 0.01)
        t.loc[m, ["categorie", "subcategorie"]] = [cat, sub]
    # Apple Store 6 mei 2026 ($1.205,85): voorgeschoten voor de zus van Myrthe (bevestigd door Myrthe).
    zus = t["omschrijving"].str.contains("APPLE STORE #R058", case=False) & (t["datum"] == "2026-05-06")
    t.loc[zus, ["soort", "categorie", "subcategorie"]] = ["intern", "Voorgeschoten", "Voorgeschoten voor zus Myrthe (Apple)"]
    # 'Afrekening houston' (9 mei, €1.875) van Florien (VAN DEN BERGH J + GILLIS F): terugbetaling van wat Myrthe
    # in de VS voor haar voorschoot (o.a. Apple). Bevestigd door Myrthe.
    flo = (t["bank"] == "Knab") & t["omschrijving"].str.contains("afrekening houston", case=False)
    t.loc[flo, ["soort", "categorie", "subcategorie"]] = ["intern", "Voorgeschoten", "Terugbetaald door Florien (afrekening Houston)"]
    # Virgin Voyages-cruise (jan 2027): betaald met Chase, volledig terugbetaald door Florien (bevestigd door Myrthe).
    cruise = t["omschrijving"].str.contains("VIRGIN CRUISES", case=False) | \
        ((t["bank"] == "Knab") & t["omschrijving"].str.contains("GILLIS F", case=False) & t["omschrijving"].str.contains("cruise", case=False))
    t.loc[cruise, ["soort", "categorie", "subcategorie"]] = ["intern", "Voorgeschoten", "Virgin-cruise voor Florien (terugbetaald)"]
    # Beekse Bergen / Safari Resort (13 jul, €791,69): terugbetaald door John (vader Jef), €792 op 8 sep.
    bb_resort = (t["bank"] == "Knab") & t["omschrijving"].str.contains("Safari Resort Exploitatie", case=False)
    bb_terug = (t["bank"] == "Knab") & (t["bedrag_orig"] > 0) & t["omschrijving"].str.contains(r"\| Beekse bergen \|", case=False, regex=True)
    t.loc[bb_resort | bb_terug, ["soort", "categorie", "subcategorie"]] = ["intern", "Voorgeschoten", "Beekse Bergen (betaald door John)"]
    # Tecovas 7 mei 2026 ($681,99): niet voor ons, voorgeschoten (bevestigd door Myrthe).
    tec = t["omschrijving"].str.contains("TECOVAS", case=False) & ((t["bedrag_usd"] + 681.99).abs() < 0.01)
    t.loc[tec, ["soort", "categorie", "subcategorie"]] = ["intern", "Voorgeschoten", "Voorgeschoten: Tecovas (niet voor ons)"]
    # Best Buy april 2026 (reMarkable, $540,17): verjaardagscadeau voor Jef, betaald door ouders/familie via Knab.
    bb = t["omschrijving"].str.contains("BESTBUY|BEST BUY", case=False) & ((t["bedrag_usd"] + 540.17).abs() < 0.01)
    bijdr = (t["bank"] == "Knab") & (t["bedrag_orig"] > 0) & t["datum"].between("2026-04-09", "2026-04-14") & \
        t["omschrijving"].str.contains("cadeau jef|happy birthday", case=False)
    t.loc[bb | bijdr, ["soort", "categorie", "subcategorie"]] = ["intern", "Voorgeschoten", "Cadeau Jef (betaald door familie)"]
    cash = (t["bank"] == "Knab") & ((t["bedrag_orig"] - 296.61).abs() < 0.01) & t["omschrijving"].str.contains("PAYPAL", case=False)
    t.loc[cash, ["soort", "categorie", "subcategorie"]] = ["uitgave", "Huis & inrichting", "Cashback Philips-espressomachine"]
    # Antwoorden Myrthe 5 okt 2026 over binnengekomen bedragen.
    def zet(masker, soort, cat, sub):
        t.loc[masker, ["soort", "categorie", "subcategorie"]] = [soort, cat, sub]
    oms = t["omschrijving"]
    zet(oms.str.contains("Zelle Payment From Jelmer De Winter", case=False), "uitgave", "Sport & hobby", "Padel (terugbetaald)")
    zet(oms.str.contains("Zelle Payment From (Maani Yousefzadeh|Carlos Castro)", case=False, regex=True), "inkomen", "Inkomen", "Verkoop spullen (koffieapparaat)")
    zet((t["bank"] == "Knab") & (t["bedrag_orig"] > 0) & oms.str.contains("MICHIELSSEN JOZEFIEN", case=False), "uitgave", "Boodschappen", "Terugbetaald door Jozefien (Target)")
    zet((t["bank"] == "Knab") & (t["bedrag_orig"] > 0) & oms.str.contains("DE HOON-MICHIELSSEN", case=False), "uitgave", "Reizen & uitjes", "Terugbetaald door reisgenoten")
    zet(oms.str.contains("COUNTRY INN & STES FRE", case=False), "uitgave", "Reizen & uitjes", "Reizen, hotels, vluchten")
    # Amtrak Washington (3 feb, $140) = werkreis Jef; Fugro vergoedde op 19 mrt precies $140.
    zet(oms.str.contains("AMTRAK", case=False) & ((t["bedrag_usd"] + 140).abs() < 0.01), "intern", "Werkreis (vergoed)", "Werkreis Washington Jef")
    # Lening ouders: €5.000 in (4 mei), €3.600 terug (4 jun). De overige €1.400 was hun bijdrage aan de
    # boodschappen tijdens hun bezoek in mei. Dat deel verlaagt de boodschappen.
    inleg = (t["bank"] == "Knab") & (t["bedrag_orig"] == 5000) & (t["subcategorie"] == "Lening ouders (geleend / terugbetaald)")
    if inleg.any():
        i = t[inleg].index[0]
        koers = t.at[i, "eur_usd"]
        t.at[i, "bedrag_orig"], t.at[i, "bedrag_usd"] = 3600.0, round(3600 * koers, 2)
        rij = t.loc[[i]].copy()
        rij[["omschrijving", "bedrag_orig", "bedrag_usd", "soort", "categorie", "subcategorie"]] = [
            "Knab: Gillis - Reyniers | deel lening = bijdrage boodschappen bezoek mei", 1400.0, round(1400 * koers, 2),
            "uitgave", "Boodschappen", "Bijdrage ouders boodschappen (bezoek mei)"]
        t = pd.concat([t, rij], ignore_index=True)
    # Vista-hypotheek (contract 3240894): €1.744,61 per maand = rente €530,33 + aflossing €1.214,28 (stand okt 2026,
    # annuïteit, 1,48% vast tot 2041). Rente is een uitgave; aflossing is vermogensopbouw (sparen).
    hyp = (t["subcategorie"] == "Hypotheek") & ((t["bedrag_orig"] + 1744.61).abs() < 0.01)
    if hyp.any():
        afl = t[hyp].copy()
        t.loc[hyp, "bedrag_orig"] = -530.33
        t.loc[hyp, "bedrag_usd"] = (-530.33 * t.loc[hyp, "eur_usd"]).round(2)
        t.loc[hyp, "subcategorie"] = "Hypotheekrente"
        afl["bedrag_orig"] = -1214.28
        afl["bedrag_usd"] = (-1214.28 * afl["eur_usd"]).round(2)
        afl[["soort", "categorie", "subcategorie"]] = ["sparen", "Sparen & beleggen", "Aflossing hypotheek NL"]
        afl["omschrijving"] = afl["omschrijving"] + " (deel: aflossing)"
        t = pd.concat([t, afl], ignore_index=True)
    # Kleine posten uit 'Nog beoordelen' die zonder twijfel in te delen zijn (5 okt 2026).
    KLEIN = [(r"MCALISTER|MCDONALD|DUNKIN|3LEVY@GRB", "uitgave", "Eten & drinken", "Uit eten & koffie"),
             (r"HOUSTON ZOO|LAKE BASTROP|TEXAN 9|ATLANTA AIRPORT|Conservation Lands", "uitgave", "Reizen & uitjes", "Uitjes & tickets"),
             (r"PMUSA|ON STREET HOUSTON|PSPT Austin", "uitgave", "Vervoer", "Parkeren"),
             (r"CHEEKY MONKEYS", "uitgave", "Kinderen", "Kinderen (activiteiten, kleding, spullen)"),
             (r"WWW COSTCO COM", "uitgave", "Boodschappen", "Supermarkt"),
             (r"MDC\*Magazines", "uitgave", "Abonnementen", "Streaming, software, nieuws"),
             (r"Interest Charge on Purchases", "uitgave", "Bankkosten", "Rente creditcard")]
    for patroon, soort, cat, sub in KLEIN:
        zet(t["omschrijving"].str.contains(patroon, case=False, regex=True) & (t["categorie"] == "Nog indelen"), soort, cat, sub)
    zet((t["bank"] == "Knab") & ((t["bedrag_orig"] + 10.74).abs() < 0.01) & t["omschrijving"].str.contains("PayPal", case=False),
        "uitgave", "Abonnementen", "Streaming, software, nieuws")
    # PayPal met koersopslag: Wayfair $129,88 (jan) en StubHub $156,48 (apr).
    zet((t["bank"] == "Knab") & ((t["bedrag_orig"] + 115.80).abs() < 0.01) & t["omschrijving"].str.contains("PayPal", case=False),
        "uitgave", "Huis & inrichting", "Huis, inrichting, post")
    zet((t["bank"] == "Knab") & ((t["bedrag_orig"] + 139.93).abs() < 0.01) & t["omschrijving"].str.contains("PayPal", case=False),
        "uitgave", "Reizen & uitjes", "Uitjes & tickets")
    # Zelle-betalingen (antwoorden Myrthe 5 okt 2026).
    oms = t["omschrijving"]
    zet(oms.str.contains("Zelle Payment To Karel Dhoore", case=False), "uitgave", "Reizen & uitjes", "Reizen, hotels, vluchten")  # weekend Atlanta
    zet(oms.str.contains("Zelle Payment To (Jelmer De Winter|Sebastiaan VAN Loon)", case=False, regex=True), "uitgave", "Sport & hobby", "Padel")
    zet(oms.str.contains("Zelle Payment To Xander Zonneveld", case=False), "uitgave", "Giften", "Cadeau (voetbaltickets)")
    zet(oms.str.contains("Zelle Payment To 1929683974", case=False), "uitgave", "Reizen & uitjes", "WK-voetbalticket Jef")
    # Tickets (antwoord Myrthe 5 okt): AXS = rodeo; StubHub (PayPal €139,93) = Earth, Wind & Fire, verjaardag Jef.
    zet(t["omschrijving"].str.contains("AXS.COMTICKET", case=False), "uitgave", "Reizen & uitjes", "Rodeo-tickets")
    zet((t["bank"] == "Knab") & ((t["bedrag_orig"] + 139.93).abs() < 0.01) & t["omschrijving"].str.contains("PayPal", case=False),
        "uitgave", "Giften", "Verjaardag Jef: Earth, Wind & Fire")
    # Freelance-inkomen Myrthe (Picnic, uitbetaald 19 en 22 mei) hoort bij werk in februari, maart en april:
    # gelijk verdelen over die maanden (bevestigd door Myrthe 5 okt 2026). Het bedrag blijft gelijk, alleen de maand verschuift.
    fl = t["subcategorie"] == "Inkomen Myrthe (freelance)"
    if fl.any():
        basis = t[fl].iloc[[0]].copy()
        tot_eur, tot_usd = t.loc[fl, "bedrag_orig"].sum(), t.loc[fl, "bedrag_usd"].sum()
        delen = []
        for i, d in enumerate(["2026-02-28", "2026-03-31", "2026-04-30"]):
            r = basis.copy()
            r["datum"] = pd.Timestamp(d)
            r["bedrag_orig"] = round(tot_eur / 3, 2) if i < 2 else round(tot_eur - 2 * round(tot_eur / 3, 2), 2)
            r["bedrag_usd"] = round(tot_usd / 3, 2) if i < 2 else round(tot_usd - 2 * round(tot_usd / 3, 2), 2)
            r["omschrijving"] = f"Freelance Myrthe (uitbetaald in mei), deel {i + 1}/3 voor werk in {['februari', 'maart', 'april'][i]}"
            delen.append(r)
        t = pd.concat([t[~fl]] + delen, ignore_index=True)
    zet((t["bank"] == "Knab") & t["omschrijving"].str.contains("Pauwels Eva", case=False) & (t["bedrag_orig"] > 0),
        "uitgave", "Reizen & uitjes", "Terugbetaald door Eva (Cameron Ranch, Lake Bastrop)")
    # Cashier's check van 9 jan 2026 = pop-up camper (bevestigd door Myrthe).
    camper = (t["omschrijving"] == "Withdrawal") & (t["datum"] == "2026-01-09")
    t.loc[camper, ["soort", "categorie", "subcategorie"]] = ["uitgave", "Eenmalig", "Pop-up camper"]
    # Ontvangen geld bij een persoon-overboeking zonder regel: terugbetaling, twijfel.
    terug = (t["categorie"] == "Nog indelen") & (t["bedrag_usd"] > 0)
    t.loc[terug, ["soort", "categorie", "subcategorie"]] = ["inkomen", "Inkomen", "Ontvangen, nog benoemen"]
    # Interne overboekingen tussen Knab-rekeningen: alleen intern als ze tussen 1133/9994/5171 gaan.
    # Positieve bedragen bij een 'uitgave'-categorie zijn terugbetalingen/refunds: die blijven in de categorie (verlagen de uitgaven).
    from artikelen import verdeel_amazon
    t = verdeel_amazon(t)
    t["periode"] = t["datum"].dt.strftime("%Y-%m")
    t["twijfel"] = t["subcategorie"].isin(TWIJFEL_SUB) | (t["categorie"] == "Nog indelen")
    t = t.sort_values(["datum", "bank", "rekening"])
    kol = ["datum", "periode", "bank", "rekening", "soort_rekening", "omschrijving", "valuta", "bedrag_orig", "eur_usd",
           "bedrag_usd", "soort", "categorie", "subcategorie", "twijfel", "afschrift"]
    t[kol].to_csv("data/verwerkt/alle_transacties.csv", index=False, date_format="%Y-%m-%d")
    t[t["twijfel"]][kol].to_csv("data/verwerkt/twijfelgevallen.csv", index=False, date_format="%Y-%m-%d")

    p = t[(t["datum"] >= "2026-01-01")]
    print("Periode:", p["datum"].min().date(), "t/m", p["datum"].max().date(), "|", len(p), "transacties")
    print("\nPer soort (USD):"); print(p.groupby("soort")["bedrag_usd"].sum().round(0))
    print("\nIntern moet ongeveer 0 zijn (verschil = wisselkosten/timing):", round(p[p.soort == "intern"]["bedrag_usd"].sum()))
    print("\nUitgaven per categorie:")
    print(p[p.soort == "uitgave"].groupby("categorie")["bedrag_usd"].sum().sort_values().round(0).to_string())
    print("\nInkomen per sub:"); print(p[p.soort == "inkomen"].groupby("subcategorie")["bedrag_usd"].sum().round(0).to_string())
    print("\nTwijfelgevallen:", int(p["twijfel"].sum()), "| Nog indelen:", int((p["categorie"] == "Nog indelen").sum()))
    ni = p[p["categorie"] == "Nog indelen"].groupby("omschrijving")["bedrag_usd"].agg(["count", "sum"]).sort_values("sum")
    print(ni.head(60).to_string())

main()
