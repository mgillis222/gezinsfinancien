import pandas as pd, glob
dfs = []
for f in glob.glob("data/afschriften/Knab*.csv"):
    d = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8")
    dfs.append(d)
k = pd.concat(dfs)
k["bedrag"] = k["Bedrag"].str.replace(",", ".").astype(float) * k["CreditDebet"].map({"Bijschrijvingen": 1, "Afschrijvingen": -1})
k["rek"] = k["Rekeningnummer"].str[-4:]
print(k.groupby("rek")["bedrag"].agg(["count", "sum"]))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60); pd.set_option("display.max_rows", 200)
g = k.groupby(["rek", "Tegenrekeninghouder"])["bedrag"].agg(["count", "sum"]).sort_values("sum")
print(g)
