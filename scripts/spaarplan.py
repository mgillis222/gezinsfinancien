"""Spaarplan: wat het salaris van Myrthe (Babylist) netto oplevert en hoe het verdeeld wordt.

Uitgangspunten (Myrthe, 19 okt 2026, zie CLAUDE.md):
- Het salaris van Jef plus huur NL en bijdrage ouders dekt precies de maandbegroting (BUDGET hieronder).
- Het hele nettosalaris van Myrthe gaat naar vakanties ($20.000 per jaar) en sparen/beleggen.
- 401(k) en aflossing NL-huis tellen niet mee in het spaardoel van €100.000.

Belasting: federale regels 2026, gezamenlijke aangifte (married filing jointly), Texas zonder staatsbelasting.
Haar nettoloon = haar bruto min wat er door haar salaris extra aan belasting en premies bij komt
(gezamenlijke belasting mét haar min gezamenlijke belasting zonder haar). Schattingen; geen belastingadvies.
"""
import json
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent
KOERS = 1.1225  # USD per EUR, zelfde als in het overzicht

# --- Belastingregels 2026 (federaal, married filing jointly) ---
STANDAARDAFTREK = 32_200
SCHIJVEN = [(24_800, 0.10), (100_800, 0.12), (211_400, 0.22), (403_550, 0.24), (512_450, 0.32), (768_700, 0.35), (float("inf"), 0.37)]
SS_TARIEF, SS_GRENS = 0.062, 184_500          # Social Security, per persoon
MEDICARE, EXTRA_MEDICARE, EXTRA_MEDICARE_GRENS = 0.0145, 0.009, 250_000
CTC_PER_KIND = 2_200                           # Child Tax Credit (kind met SSN)
ODC_PER_KIND = 500                             # Credit for Other Dependents (kind met ITIN)
LIMIET_401K = 24_500
HSA_GEZIN = 8_750

# --- Jef (offer letter + FSA-inleg; zorgpremie geschat tot de loonstrook er is) ---
JEF = {
    "bruto": 166_500,
    "k401_pct": 0.04,          # "minimum voor de volle Fugro-bijdrage"; controleren op loonstrook
    "dcfsa": 7_500,            # Dependent Care FSA (gezinsmaximum)
    "hcfsa": 3_400,            # Health Care FSA
    "zorgpremie": 6_000,       # SCHATTING gezinsverzekering Fugro per jaar (vóór belasting)
}

# --- Myrthe: Babylist ---
SCENARIO_BRUTO = [140_000, 155_000, 170_000]
MYRTHE_401K_PCT = 0.04         # aanname tot de match-formule van Babylist bekend is
VAKANTIE_PER_JAAR = 20_000
DOEL_EUR = 100_000

# --- Kinderen ---
BILL_SSN = True                # Child Tax Credit
LILY_ITIN = False              # zonder ITIN geen $500; aanvragen loont

# --- Maandbegroting zoals Myrthe die in het overzicht instelde (19 okt 2026) ---
BUDGET = {
    "inkomen": {"Salaris Jef (netto)": 9404, "Dependent Care FSA terug": 625, "Huur woning NL (€2.495)": 2801,
                "Bijdrage ouders": 67},
    "vast": {"Huur Cottondale Ct": 3100, "Woning NL: rente, VvE, belastingen": 1040, "Aflossing hypotheek NL": 1363,
             "Primrose (Lily + Bill)": 2730, "Ondersteuning schoonmoeder": 898, "Schoonmaak": 289, "Oppas": 30,
             "Tuinman": 57, "Water, stroom, gas": 232, "Sportschool YMCA": 132, "Telefoon & internet": 97,
             "Verzekeringen": 259, "Abonnementen (zonder Disney+ en Coursera)": 256},
    "variabel": {"Boodschappen": 1400, "Eten & drinken": 200, "Uitjes, tickets, eten onderweg": 200,
                 "Weekendjes weg": 50, "Grote vakantie": 0, "Vervoer": 160, "Kleding & persoonlijk": 100,
                 "Kinderen": 150, "Zorg (eigen betalingen)": 200, "Huis, sport, hobby": 250, "Overig": 50},
}


def inkomstenbelasting(belastbaar):
    belasting, onder = 0.0, 0
    for boven, tarief in SCHIJVEN:
        if belastbaar > onder:
            belasting += (min(belastbaar, boven) - onder) * tarief
        onder = boven
    return belasting


def gezin(myrthe_bruto, myrthe_401k_pct=MYRTHE_401K_PCT):
    """Jaarlijkse belasting en premies voor het hele gezin."""
    j, m = JEF, myrthe_bruto
    j401, m401 = min(j["bruto"] * j["k401_pct"], LIMIET_401K), min(m * myrthe_401k_pct, LIMIET_401K)
    sec125_j = j["dcfsa"] + j["hcfsa"] + j["zorgpremie"]       # gaat ook van de premiegrondslag af
    loon_j = j["bruto"] - j401 - sec125_j
    loon_m = m - m401
    belastbaar = max(0, loon_j + loon_m - STANDAARDAFTREK)
    bruto_belasting = inkomstenbelasting(belastbaar)
    kortingen = (CTC_PER_KIND if BILL_SSN else 0) + (ODC_PER_KIND if LILY_ITIN else 0)
    fed = max(0, bruto_belasting - kortingen)
    medicare_loon = (j["bruto"] - sec125_j) + m
    fica = (SS_TARIEF * min(j["bruto"] - sec125_j, SS_GRENS) + SS_TARIEF * min(m, SS_GRENS)
            + MEDICARE * medicare_loon + EXTRA_MEDICARE * max(0, medicare_loon - EXTRA_MEDICARE_GRENS))
    return {"belastbaar": belastbaar, "federaal": fed, "fica": fica, "kortingen": kortingen,
            "j401": j401, "m401": m401, "bruto": j["bruto"] + m}


def budget_saldo():
    return sum(BUDGET["inkomen"].values()) - sum(BUDGET["vast"].values()) - sum(BUDGET["variabel"].values())


def scenario(bruto):
    zonder, met = gezin(0), gezin(bruto)
    tekort = min(0, budget_saldo()) * 12   # wat het leefgeld per jaar tekortkomt, gaat eerst van haar salaris af
    extra_fed = met["federaal"] - zonder["federaal"]
    extra_fica = met["fica"] - zonder["fica"]
    netto = bruto - met["m401"] - extra_fed - extra_fica
    sparen = netto - VAKANTIE_PER_JAAR + tekort
    tarief_marge = (inkomstenbelasting(met["belastbaar"] + 1000) - inkomstenbelasting(met["belastbaar"])) / 1000
    return {
        "bruto": bruto, "k401_pct": MYRTHE_401K_PCT, "k401": round(met["m401"]),
        "federaal": round(extra_fed), "fica": round(extra_fica), "netto": round(netto),
        "netto_maand": round(netto / 12), "netto_salaris": round(netto / 26),
        "tekort_leefgeld": round(tekort), "vakantie": VAKANTIE_PER_JAAR, "vakantie_salaris": round(VAKANTIE_PER_JAAR / 26),
        "sparen": round(sparen), "sparen_eur": round(sparen / KOERS), "sparen_maand": round(sparen / 12),
        "sparen_salaris": round(sparen / 26), "doel_pct": round(sparen / KOERS / DOEL_EUR * 100),
        "marge_tarief": round(tarief_marge * 100), "gezin_federaal": round(met["federaal"]),
        "gezin_fica": round(met["fica"]), "gezin_tarief": round((met["federaal"] + met["fica"]) / met["bruto"] * 100, 1),
        "zonder_401k_netto": round(bruto - (gezin(bruto, 0)["federaal"] - zonder["federaal"]) - (gezin(bruto, 0)["fica"] - zonder["fica"])),
    }


def maak():
    inkomen = sum(BUDGET["inkomen"].values())
    uitgaven = sum(BUDGET["vast"].values()) + sum(BUDGET["variabel"].values())
    return {
        "budget": BUDGET, "budget_inkomen": inkomen, "budget_uitgaven": uitgaven, "budget_saldo": inkomen - uitgaven,
        "scenarios": [scenario(b) for b in SCENARIO_BRUTO],
        "koers": KOERS, "doel_eur": DOEL_EUR, "vakantie": VAKANTIE_PER_JAAR,
        "aannames": {
            "jef_401k_pct": JEF["k401_pct"], "jef_zorgpremie": JEF["zorgpremie"], "myrthe_401k_pct": MYRTHE_401K_PCT,
            "bill_ctc": CTC_PER_KIND if BILL_SSN else 0, "lily_itin": LILY_ITIN, "odc": ODC_PER_KIND,
        },
    }


if __name__ == "__main__":
    d = maak()
    print(f"Begroting: inkomen {d['budget_inkomen']}, uitgaven {d['budget_uitgaven']}, saldo {d['budget_saldo']}")
    for s in d["scenarios"]:
        print(s)
    (MAP / "data" / "verwerkt" / "spaarplan.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
