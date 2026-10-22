"""Pensioen van Myrthe en Jef: wat er straks is, en wat 4 jaar VS oplevert tegenover 4 jaar Nederland
(gebruikt door maak_dashboard_data.py).

Alle bedragen bruto per jaar vanaf ±68 jaar, in koopkracht van nu (groei = rendement boven inflatie).
Myrthe: echte cijfers uit mijnpensioenoverzicht.nl en het UPO van a.s.r. (data/pensioen/).
Jef: SCHATTING (geen overzicht): altijd in NL gewerkt, Fugro NL bij Pensioenfonds PGB, laatste salaris ±€95.000.
Schattingen; geen pensioen- of belastingadvies.
"""
from spaarplan import KOERS, JEF, MYRTHE_401K_PCT, SCENARIO_BRUTO

GROEI = 0.03                 # rendement 401(k)/premiepensioen boven inflatie
ONTTREKKING = 0.04           # 401(k): elk jaar 4% opnemen
OMZETTING = 0.0484           # premiepensioen → uitkering (UPO a.s.r.: €611.100 → €29.600)
AOW_PER_JAAR = 3_206 / 14.8  # ±€217 per jaar wonen in NL (Myrthe: €3.206 voor ±14,8 jaar sinds haar 17e)
VS_JAREN = (2026, 2029)      # verwachte jaren in de VS (±4 jaar, vertrek dec 2025)
SS_KORTING = 0.20            # mogelijke korting Social Security als het fonds rond 2033–2034 leeg is

# Social Security 2026: bend points van de formule (PIA) en maximaal belast loon
BEND1, BEND2, SS_MAX = 1_286, 7_749, 184_500

PERSONEN = {
    "Myrthe": {
        "aow_tot_nu": 3_206, "aow_jaren_terug": 2061 - 2030,       # AOW-leeftijd 67j3m = feb 2061
        "nl_pensioen": {"KLM Grondfonds": 5_967, "a.s.r. Doenpensioen (oud)": 3_001,
                        "a.s.r. Doenpensioen Picnic (tot eind 2025)": 1_400},
        "vs_loon": [17_600] + [SCENARIO_BRUTO[0]] * 3,             # 2026 freelance Picnic, daarna Babylist ($140k)
        "k401": [0] + [SCENARIO_BRUTO[0] * MYRTHE_401K_PCT] * 3,    # eigen inleg 4%; Babylist-match nog onbekend
        "pensioen68": 2061,
        # 4 jaar NL: Picnic-regeling bleef lopen (6,6% boven franchise €18.475 van €79.000)
        "nl_premie": 0.066 * (79_000 - 18_475), "nl_db": 0,
        "schatting": False,
    },
    "Jef": {
        "aow_tot_nu": AOW_PER_JAAR * 10, "aow_jaren_terug": 2059.5 - 2030,  # aanname: in NL sinds 2016; AOW jul 2059
        # PGB-middelloon: 1,75% per jaar over salaris min franchise; 2016–2025, salaris van €45k naar €95k
        "nl_pensioen": {"Fugro NL via PGB (schatting)": round(sum(
            0.0175 * ((45_000 + (95_000 - 45_000) * i / 9) - (15_000 + 3_500 * i / 9)) for i in range(10)))},
        "vs_loon": [JEF["bruto"]] * 4,
        "k401": [JEF["bruto"] * 0.11] * 4,                          # 6% zelf + 5% Fugro
        "pensioen68": 2060,
        "nl_premie": 0, "nl_db": 0.0175 * (95_000 - 18_958),        # 4 jaar extra PGB-opbouw
        "schatting": True,
    },
}


def social_security(lonen):
    """Totalization-uitkering per jaar in USD: theoretische PIA × (VS-kwartalen / 140 kwartalen loopbaan)."""
    aime = sum(min(l, SS_MAX) for l in lonen) / len(lonen) / 12
    pia = 0.9 * min(aime, BEND1) + 0.32 * max(0, min(aime, BEND2) - BEND1) + 0.15 * max(0, aime - BEND2)
    kwartalen = 4 * sum(1 for l in lonen if l > 7_560)   # 2026: $1.890 per kwartaal, max 4 per jaar
    return pia * 12 * kwartalen / 140


def k401_uitkering(inleg, pensioenjaar):
    eind = sum(b * (1 + GROEI) ** (pensioenjaar - (VS_JAREN[0] + i) - 0.5) for i, b in enumerate(inleg))
    return eind, eind * ONTTREKKING


def persoon(naam, p):
    ss = social_security(p["vs_loon"]) / KOERS
    kapitaal, k401 = k401_uitkering(p["k401"], p["pensioen68"])
    k401 /= KOERS
    aow_vs = p["aow_tot_nu"] + AOW_PER_JAAR * p["aow_jaren_terug"]
    nl_vier = AOW_PER_JAAR * 4 + p["nl_db"] * 4 + sum(
        p["nl_premie"] * (1 + GROEI) ** (p["pensioen68"] - (VS_JAREN[0] + i) - 0.5) for i in range(4)) * OMZETTING
    vs_vier = ss + k401
    nl_tot = sum(p["nl_pensioen"].values())
    return {
        "naam": naam, "schatting": p["schatting"],
        "regels": [{"wat": "AOW (tot nu)", "bedrag": round(p["aow_tot_nu"])},
                   {"wat": "AOW (na terugkeer in 2030)", "bedrag": round(AOW_PER_JAAR * p["aow_jaren_terug"])}] +
                  [{"wat": k, "bedrag": v} for k, v in p["nl_pensioen"].items()] +
                  [{"wat": "Social Security (4 jaar VS)", "bedrag": round(ss)},
                   {"wat": "401(k) (4% per jaar opnemen)", "bedrag": round(k401)}],
        "totaal": round(aow_vs + nl_tot + ss + k401),
        "totaal_ss_korting": round(aow_vs + nl_tot + ss * (1 - SS_KORTING) + k401),
        "k401_kapitaal_eur": round(kapitaal / KOERS),
        "vier_jaar_vs": round(vs_vier), "vier_jaar_vs_korting": round(ss * (1 - SS_KORTING) + k401),
        "vier_jaar_nl": round(nl_vier),
    }


def maak():
    return {"personen": [persoon(n, p) for n, p in PERSONEN.items()],
            "aannames": {"groei": GROEI, "onttrekking": ONTTREKKING, "ss_korting": SS_KORTING,
                         "aow_per_jaar": round(AOW_PER_JAAR), "myrthe_401k_pct": MYRTHE_401K_PCT}}


if __name__ == "__main__":
    for x in maak()["personen"]:
        print(x)
