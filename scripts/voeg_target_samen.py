"""Voegt de Target-, DoorDash- en eten-deelbestanden samen tot twee bestanden en ontdubbelt op order_id+soort+totaal."""
import pandas as pd, glob
D = "data/bestellingen/delen/"
def lees(patroon):
    fs = sorted(glob.glob(D + patroon, recursive=True))
    return pd.concat([pd.read_csv(f, dtype=str).assign(deelbestand=f.split("/")[-1]) for f in fs], ignore_index=True), fs
o, fo = lees("**/*_orders.csv"); a, fa = lees("**/*_artikelen.csv")
print("orderbestanden:", len(fo), "artikelbestanden:", len(fa))
o["totaal_num"] = pd.to_numeric(o["totaal"], errors="coerce")
voor = len(o)
o = o.drop_duplicates(subset=["winkel", "order_id", "soort", "totaal"])
print(f"orders {voor} -> {len(o)} na ontdubbelen")
dub = o[o.duplicated(subset=["order_id", "soort"], keep=False) & o["order_id"].notna()]
if len(dub): print("LET OP, zelfde order_id+soort met ander bedrag:\n", dub[["deelbestand","datum","winkel","order_id","soort","totaal","status"]])
a = a.drop_duplicates(subset=[c for c in a.columns if c != "deelbestand"])
o.drop(columns="totaal_num").to_csv("data/bestellingen/gmail_target_eten_orders.csv", index=False)
a.to_csv("data/bestellingen/gmail_target_eten_artikelen.csv", index=False)
print(o.groupby("winkel")["totaal_num"].agg(["count","sum"]).sort_values("sum", ascending=False).head(25))
print("artikelen:", len(a))
