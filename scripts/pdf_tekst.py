import sys, pdfplumber
for f in sys.argv[1:]:
    with pdfplumber.open(f) as pdf:
        print(f"===== {f} ({len(pdf.pages)} p)")
        for i, p in enumerate(pdf.pages):
            print(f"--- pagina {i+1}")
            print(p.extract_text() or "")
