"""Zet alle Chase-pdf's om naar tekstbestanden in data/tekst/ (om de opmaak te bekijken)."""
import pathlib, pdfplumber
bron = pathlib.Path("data/afschriften"); doel = pathlib.Path("data/tekst"); doel.mkdir(exist_ok=True)
for f in sorted(bron.glob("*.pdf")):
    with pdfplumber.open(f) as pdf:
        tekst = "\n".join(f"--- pagina {i+1}\n" + (p.extract_text() or "") for i, p in enumerate(pdf.pages))
    (doel / (f.stem + ".txt")).write_text(tekst, encoding="utf-8")
    eerste = [l for l in tekst.splitlines() if l.strip()][:6]
    print(f.name, "|", len(pdf.pages), "p |", " / ".join(eerste)[:220])
