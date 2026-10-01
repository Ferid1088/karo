"""Erzeugt die synthetischen Proben fuer die CI — ohne ein echtes Blatt.

Echte Schulblaetter kommen nie in dieses Repository. Fuer die CI reicht ein
Rauchtest: geht ein Foto, ein PDF mit Textebene und ein gescanntes PDF
ueberhaupt durch den Weg? Die *Qualitaet* misst `make ocr-report` lokal an
echten Blaettern — eine synthetische Trefferquote waere eine Zahl ueber nichts.
"""
from __future__ import annotations

from pathlib import Path

HIER = Path(__file__).resolve().parent

TEXT = [
    "Bruchrechnung",
    "",
    "Regel: Ungleichnamige Brueche erst gleichnamig machen.",
    "",
    "Beispiel: 1/2 + 1/3 = 3/6 + 2/6 = 5/6",
    "",
    "Aufgabe 1: Rechne 1/4 + 1/6.",
]


def foto(ziel: Path = HIER / "blatt-foto.png") -> Path:
    """Ein gerendertes 'Foto': schwarzer Text auf weiss, gross genug fuer OCR."""
    from PIL import Image, ImageDraw, ImageFont

    bild = Image.new("RGB", (1240, 900), "white")
    zeichne = ImageDraw.Draw(bild)
    try:
        schrift = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    except OSError:
        try:
            schrift = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 34)
        except OSError:
            schrift = ImageFont.load_default()
    y = 60
    for zeile in TEXT:
        zeichne.text((70, y), zeile, fill="black", font=schrift)
        y += 56
    bild.save(ziel)
    return ziel


def _pdf_mit_text(ziel: Path) -> Path:
    """Ein winziges PDF mit echter Textebene — von Hand, ohne Bibliothek."""
    inhalt = "BT /F1 18 Tf 60 760 Td 14 TL\n" + "".join(
        f"({z.replace('(', '').replace(')', '')}) Tj T*\n" for z in TEXT) + "ET"
    objekte = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(inhalt)} >>\nstream\n{inhalt}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    teile, versatz = ["%PDF-1.4\n"], []
    stelle = len(teile[0])
    for i, o in enumerate(objekte, start=1):
        stueck = f"{i} 0 obj\n{o}\nendobj\n"
        versatz.append(stelle)
        teile.append(stueck)
        stelle += len(stueck)
    tabelle = f"xref\n0 {len(objekte) + 1}\n0000000000 65535 f \n" + "".join(
        f"{v:010d} 00000 n \n" for v in versatz)
    teile.append(tabelle)
    teile.append(f"trailer\n<< /Size {len(objekte) + 1} /Root 1 0 R >>\nstartxref\n{stelle}\n%%EOF\n")
    ziel.write_bytes("".join(teile).encode("latin-1"))
    return ziel


def pdf_mit_textebene(ziel: Path = HIER / "blatt-text.pdf") -> Path:
    return _pdf_mit_text(ziel)


def pdf_gescannt(ziel: Path = HIER / "blatt-scan.pdf") -> Path:
    """Ein PDF ohne Textebene: das Foto von oben als einzige Seite."""
    from PIL import Image

    bild = Image.open(foto(ziel.parent / "_tmp-scan.png")).convert("RGB")
    bild.save(ziel, "PDF", resolution=150)
    (ziel.parent / "_tmp-scan.png").unlink(missing_ok=True)
    return ziel


def alle() -> dict[str, Path]:
    return {"foto": foto(), "pdf-text": pdf_mit_textebene(), "pdf-scan": pdf_gescannt()}


if __name__ == "__main__":
    for art, pfad in alle().items():
        print(f"{art:<10} {pfad.name}  {pfad.stat().st_size // 1024} KB")
