import fitz  # PyMuPDF
from pathlib import Path
import sys

output_dir = Path("data/editions")
pdf_files = sorted(list(output_dir.glob("*.pdf")), key=lambda p: p.stat().st_mtime, reverse=True)

if not pdf_files:
    print("No PDF files found in data/editions!")
    sys.exit(1)

latest_pdf = pdf_files[0]
print(f"Opening latest PDF: {latest_pdf}")

doc = fitz.open(latest_pdf)
print(f"Total PDF Pages: {len(doc)}")

for idx, page in enumerate(doc, 1):
    pix = page.get_pixmap(dpi=150)
    out_img = output_dir / f"pdf_page_{idx}.png"
    pix.save(out_img)
    print(f"Rendered Page {idx} -> {out_img}")
