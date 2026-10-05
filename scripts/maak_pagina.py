"""Zet data/verwerkt/dashboard.json in het sjabloon en schrijft dashboard/overzicht.html (niet in Git: bevat jullie cijfers)."""
import json, pathlib
d = json.loads(pathlib.Path("data/verwerkt/dashboard.json").read_text(encoding="utf-8"))
sjabloon = pathlib.Path("dashboard/sjabloon.html").read_text(encoding="utf-8")
data = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
pathlib.Path("dashboard/overzicht.html").write_text(sjabloon.replace("/*__DATA__*/null", data), encoding="utf-8")
print("dashboard/overzicht.html geschreven")
