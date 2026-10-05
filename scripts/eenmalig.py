"""Eenmalige uitgaven en grote vakanties herkennen, zodat de vooruitblik met een 'structurele maand' rekent.

Eenmalig = komt niet terug: camper, babyuitzet rond de geboorte van Bill, inrichting na de verhuizing.
Grote vakanties = de jaarlijkse grote reis; die telt in de vooruitblik als jaarbudget gedeeld door 12.
Pas de regels hier aan als iets toch wel (of juist niet) terugkomt.
"""
import pandas as pd

EENMALIG_SUB = {
    "Pop-up camper", "Camper & kampeerspullen (Amazon)", "Klussen (Amazon)",
    "Baby & zwangerschap (Amazon)", "Geboortekaartjes Bill", "Paspoort Bill", "Ziekenhuis (bevalling)",
    "Bijdrage ouders boodschappen (bezoek mei)",   # eenmalige meevaller, verlaagt de boodschappen niet structureel
}
EENMALIG_TEKST = r"GANDER RV|CAMPING WORLD|BABYLIST|BUGABOO|ARTIPOPPE|TX BIRTH DEATH|CONSULATE GEN BELGIUM|PRACTICE WITH BELL"
GROTE_VAKANTIE_TEKST = r"KLM|VRBO|TRANSAVIA|NS INTERNATIONAAL|BOOKING"


def markeer(t):
    """Voegt kolommen 'eenmalig' en 'grote_vakantie' toe (True/False)."""
    oms = t["omschrijving"].fillna("")
    datum = pd.to_datetime(t["datum"])
    inrichting = (t["categorie"] == "Huis & inrichting") & (datum < "2026-03-01")   # eerste weken na de verhuizing
    eenmalig = t["subcategorie"].isin(EENMALIG_SUB) | oms.str.contains(EENMALIG_TEKST, case=False, regex=True) | inrichting
    europa = (t["subcategorie"] == "Pinnen tijdens vakantie Europa") | \
        ((t["bank"] == "Knab") & ((t["bedrag_orig"] + 2711.77).abs() < 0.01))   # Oostduinkerke via PayPal
    groot = (t["categorie"] == "Reizen & uitjes") & (oms.str.contains(GROTE_VAKANTIE_TEKST, case=False, regex=True) | europa)
    t = t.copy()
    t["eenmalig"] = eenmalig & (t["soort"] == "uitgave")
    t["grote_vakantie"] = groot & ~t["eenmalig"]
    return t
