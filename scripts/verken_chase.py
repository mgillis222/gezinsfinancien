import pandas as pd, re
c = pd.read_csv("data/verwerkt/chase_transacties.csv")
def norm(s):
    s = re.sub(r"\d{2}/\d{2}\s", "", s)
    s = re.sub(r"(Transaction#|Jpm|PPD ID|Ref:|Card \d{4}|#\d+|\*[A-Z0-9]{6,}|\d{5,}).*", "", s)
    return re.sub(r"\s+", " ", s).strip()[:38].upper()
c["m"] = c["omschrijving"].map(norm)
g = c.groupby("m")["bedrag"].agg(["count","sum"]).sort_values("sum")
pd.set_option("display.max_rows", 400); pd.set_option("display.width", 200)
print(g.to_string())
