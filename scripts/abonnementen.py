"""Abonnementen herkennen en hun status bepalen (gebruikt door maak_dashboard_data.py).

Status komt uit de afschriften (laatste betaling) plus wat in Gmail stond over opzeggen en verlengen.
Pas STATUS aan als er iets verandert (opgezegd, nieuw abonnement).
"""
import re

DIENSTEN = [
    ("claude|anthropic", "Claude (Anthropic)"), ("linkedin", "LinkedIn Premium"), ("microsoft", "Microsoft 365"),
    ("netflix", "Netflix (NL)"), ("videoland", "Videoland (NL)"), ("npo", "NPO Start Plus (NL)"),
    ("prime video uk", "Prime Video (NL, via Knab)"), ("amazon prime", "Amazon Prime (VS)"), ("prime video", "Prime Video huur/kanaal"),
    ("podimo", "Podimo (NL)"), ("spotify", "Spotify"), ("storytel", "Storytel (NL)"), ("hbo", "HBO Max"),
    ("disney", "Disney+ / Hulu"), ("nord", "NordVPN"), ("consumentenbond", "Consumentenbond"), ("correspondent", "De Correspondent"),
    ("strava|koen", "Strava (via Koen)"), ("international card|ics", "ICS-creditcard (ChatGPT + jaarbijdrage)"),
    ("apple", "Apple (iCloud e.d.)"), ("canva", "Canva"), ("github", "GitHub"), ("coursera", "Coursera"), ("google", "Google One"),
]

# (dienst, status, bedrag per maand in USD, toelichting). Status: loopt / jaarlijks / gestopt / eenmalig.
STATUS = [
    ("Claude (Anthropic)", "loopt", 103.72, "Sinds 15 sep Max ($104); daarvoor Pro ($21). Soms losse bijbetalingen voor extra gebruik."),
    ("LinkedIn Premium", "loopt", 43.29, "Elke maand op de 4e."),
    ("Coursera", "loopt", 49.00, "Nieuw sinds 28 sep (Agentic AI). Staat nog niet in de afschriften."),
    ("Amazon Prime (VS)", "loopt", 16.23, "Elke maand rond de 9e."),
    ("Spotify", "loopt", 15.00, "Via Knab, rond de 13e. Vanaf oktober €13,99."),
    ("Disney+ / Hulu", "loopt", 13.80, "Sinds 28 juli, via Apple Pay."),
    ("Netflix (NL)", "loopt", 11.60, "Via Knab, €9,99 per maand."),
    ("Podimo (NL)", "loopt", 11.60, "Via Knab, €9,99 per maand."),
    ("Microsoft 365", "loopt", 10.81, "Elke maand op de 20e."),
    ("Videoland (NL)", "loopt", 7.95, "Via Knab, rond de 26e."),
    ("Prime Video (NL, via Knab)", "loopt", 6.80, "Prime Video UK, €5,99 per maand."),
    ("NPO Start Plus (NL)", "loopt", 4.01, "Via Knab, €3,45 per maand."),
    ("Apple (iCloud e.d.)", "loopt", 2.99, "Elke maand rond de 28e."),
    ("NordVPN", "jaarlijks", 87.87 / 24, "Twee jaar betaald in januari 2026 ($87,87). Verlengt in januari 2028 voor $150."),
    ("Strava (via Koen)", "jaarlijks", 69.23 / 12, "Jaarabonnement, in maart aan Koen betaald."),
    ("De Correspondent", "jaarlijks", 29.56 / 12, "Jaarlid, betaald in juni."),
    ("Google One", "jaarlijks", 19.99 * 1.17 / 12, "€19,99 per jaar via PayPal, verlengt 30 sep 2027."),
    ("ICS-creditcard (ChatGPT + jaarbijdrage)", "jaarlijks", 28 * 1.17 / 12, "ChatGPT liep tot en met maart (gestopt); alleen de jaarbijdrage van €28 blijft."),
    ("Storytel (NL)", "gestopt", 0, "Opgezegd in januari."),
    ("HBO Max", "gestopt", 0, "Opgezegd op 2 juni."),
    ("Consumentenbond", "gestopt", 0, "Opgezegd op 9 juni."),
    ("GitHub", "eenmalig", 0, "Eén betaling in april."),
    ("Canva", "eenmalig", 0, "Eén betaling in augustus."),
    ("Prime Video huur/kanaal", "eenmalig", 0, "Losse huur in augustus."),
]

BINNENKORT = [
    {"wanneer": "vóór 21 okt", "wat": "Travel + Leisure (tijdschrift) verlengt automatisch voor $44 + belasting. Opzeggen als je het niet meer wilt."},
    {"wanneer": "24 dec", "wat": "DashPass is gratis via Chase tot 24 december; daarna $9,99 per maand als je het niet stopt."},
]


def dienst(omschrijving, schoon):
    for patroon, naam in DIENSTEN:
        if re.search(patroon, omschrijving, re.I):
            return naam
    return schoon(omschrijving)


def maak_lijst(t, schoon):
    ab = t[(t.categorie == "Abonnementen") & (t.soort == "uitgave")].copy()
    ab["naam"] = ab["omschrijving"].map(lambda s: dienst(s, schoon))
    per = ab.sort_values("datum").groupby("naam").agg(laatst=("datum", "last"), bedrag=("bedrag_usd", "last"),
                                                       keer=("bedrag_usd", "size"), totaal=("bedrag_usd", "sum"))

    def uit_data(naam):
        if naam in per.index:
            r = per.loc[naam]
            return {"laatst": r["laatst"], "laatste_bedrag": round(-r["bedrag"], 2), "keer": int(r["keer"]), "totaal": round(-r["totaal"], 2)}
        return {"laatst": None, "laatste_bedrag": None, "keer": 0, "totaal": 0.0}

    lijst = [{"naam": n, "status": s, "per_maand": round(pm, 2), "noot": noot, **uit_data(n)} for n, s, pm, noot in STATUS]
    bekend = {a["naam"] for a in lijst}
    for n in per.index:  # staat in de afschriften maar nog niet in STATUS: tonen als 'controleren'
        if n not in bekend:
            lijst.append({"naam": n, "status": "controleren", "per_maand": 0, "noot": "Nog niet beoordeeld.", **uit_data(n)})
    return lijst
