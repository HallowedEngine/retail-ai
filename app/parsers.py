import re
from typing import List, Dict

TR_LETTERS = "A-Za-zÇĞİÖŞÜçğıöşü"

def _final_name_clean(s: str) -> str:
    # sonda kalan noktalama ve çift boşlukları düzelt
    s = re.sub(r"\s*[,.;:)\]]+\s*$", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = s.replace("..", ".")
    return s.strip()

def _clean_name(s: str) -> str:
    s = s.strip()
    # Harf/sayı/boşluk ve +-.,/() karakterlerini koru; diğer gürültüyü at
    s = re.sub(rf"[^0-9{TR_LETTERS}\-.,/()+ ]+", "", s)
    s = " ".join(s.split())
    return s

def _postfix_name(s: str) -> str:
    """Sık OCR hataları için hızlı düzeltmeler."""
    s0 = s
    s = s.upper()
    fixes = {
        "FCE": "ECE",
        "PLS.": "PLS.",
        "TOLU": "10LU",
        "PMHOUSE": "EMHOUSE",
        "SAKI MA": "SAKLAMA",
        "KARI": "KABI",
        "DIKD": "DIKD.",           # bırak
        "PR20B/": "PR20B ",
        "KIE TIE": "KİLİTLİ",
        "BU20": "BUZD",
        "POST TI": "POŞETİ",
        "DELLA": "BELLA",
        " AT 0": "",               # sonda kalan gürültüler
        " BQS9GU E": "",
        # İsteğe bağlı küçük okunurluk düzeltmeleri
        " HIN.": " HİND.",
        " BIT.": " BİT.",
        " 6 LI": " 6LI",
        " 10 LU": " 10LU",
    }
    for k, v in fixes.items():
        s = s.replace(k, v)
    s = _clean_name(s)
    return s if len(s) >= 3 else _clean_name(s0)

NUM = r"\d+(?:[.,]\d+)?"

def _to_float(s: str) -> float:
    s = s.strip()
    s = s.replace("TL", "").replace("₺", "").replace(" ", "")
    s = s.replace(",", ".")
    s = re.sub(r"[^0-9.]", "", s)
    try:
        return float(s)
    except:
        return 0.0

def _normalize_qty(x: float) -> float:
    # "1,000 AD" gibi OCR çıktılarında 1.0'a yuvarla
    if 0.9 <= x <= 1.1:
        return 1.0
    return x

def _looks_like_name(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if len(s) < 3:
        return False
    # Tamamen sayı (barkod) ise isim değildir
    if re.fullmatch(r"\d{8,}", s):
        return False
    letters = sum(ch.isalpha() for ch in s)
    return letters >= max(3, int(len(s) * 0.4))

def parse_invoice_lines(ocr_text: str) -> List[Dict]:
    """
    Barkod satırı + alt satırda ürün adı bulunan fişleri hedefler.
    Ör:
      8682971085011  1,000 AD   47,50   20   .00   47,03
      D. IÇIM SÜT 1/1 TAM YAĞLI
    Kurallar:
      - Barkod (12-14 hane) ile başlarsa: qty, unit, fiyatları çek.
      - Soldaki ilk para: birim fiyat; en sağdaki: satır toplamı *olabilir*.
      - qty≈1 ve sağdaki, soldakinin %60’ından küçükse toplam değildir (KDV/iskonto); yok say.
      - Bir alt satır isimse name_raw olarak onu al; temizle + düzelt.
      - Yedek: 'AD xQTY @PRICE' ve '... QTY PRICE' kalıpları.
    """
    lines_out: List[Dict] = []
    if not ocr_text:
        return lines_out

    raw_lines = [" ".join(l.split()) for l in ocr_text.splitlines()]
    i, n = 0, len(raw_lines)

    while i < n:
        row = raw_lines[i]
        i_next_used = False

        # --- Özet/vergisel satırları dışla (KDV, TOPLAM, FATURA, VISA, NAKİT vs.)
        upper = row.upper()
        # OCR varyantlarını normalize et (DVS/KDVE -> KDV)
        upper = (upper
                 .replace(" DVS", " KDV")
                 .replace(" KDVE", " KDV")
                 .replace("KDVE", "KDV")
                 .replace("KDV%", "KDV "))
        SKIP_KEYS = ("KDV", "TOPLAMI", "TOPLAM", "FATURA", "VISA", "NAKIT", "NAKİT", "GENEL")
        if any(k in upper for k in SKIP_KEYS):
            i += 1
            continue

        # --- 1) Barkod ile başlayan satır
        m = re.match(
            rf'(?P<barcode>\d{{12,14}})\s+(?P<qty>{NUM})\s*(?P<unit>AD|Ad|ad|KG|Kg|kg|KOLI|PAKET)?\s+(?P<rest>.+)$',
            row
        )
        if m:
            qty = _normalize_qty(_to_float(m.group("qty")))
            unit = (m.group("unit") or "adet").lower()
            rest = m.group("rest")

            # Fiyat adaylarını topla
            money_tokens = re.findall(rf"{NUM}", rest)
            money_vals = [_to_float(tok) for tok in money_tokens if _to_float(tok) > 0]

            line_total = 0.0
            unit_price = 0.0
            if money_vals:
                # Heuristik: ilk sayı birim fiyat, son sayı satır toplamı olabilir
                left = money_vals[0]
                right = money_vals[-1]
                unit_price = left
                line_total = right

                # qty≈1 ve sağdaki çok küçükse toplam değildir → yok say
                if qty >= 0.95 and right < left * 0.6:
                    line_total = 0.0

                # Birim fiyat saçma/0 ise toplam/qty ile doldur
                if (unit_price <= 0 or unit_price > 100000) and line_total > 0 and qty > 0:
                    unit_price = line_total / qty

            # Ürün adı: alt satır uygunsa onu al; değilse mevcut satırı kullan. Temizle + düzelt.
            name_guess = row
            if i + 1 < n and _looks_like_name(raw_lines[i + 1]):
                name_guess = raw_lines[i + 1]
                i_next_used = True
            name_guess = _postfix_name(_clean_name(name_guess))
            name_guess = _final_name_clean(name_guess)

            # Mantık filtresi ve ekleme (barcode'u da ekle)
            if qty > 0 and 0 < unit_price < 10000:
                lines_out.append({
                    "barcode": m.group("barcode"),
                    "name_raw": name_guess,
                    "qty": qty,
                    "unit": "adet" if unit.startswith("ad") else unit,
                    "unit_price": round(unit_price, 2)
                })
            i += 2 if i_next_used else 1
            continue

        # --- 2) "AD xQTY @PRICE"
        m = re.search(rf"(.+?)\s+x({NUM})\s+@({NUM})", row, flags=re.IGNORECASE)
        if m:
            name = _postfix_name(_clean_name(m.group(1)))
            qty = _normalize_qty(_to_float(m.group(2)))
            price = _to_float(m.group(3))
            if qty > 0 and price > 0:
                lines_out.append({"name_raw": name, "qty": qty, "unit": "adet", "unit_price": round(price, 2)})
            i += 1
            continue

        # --- 3) '...  QTY  PRICE' (satır sonunda iki sayı)
        m = re.search(rf"(.+?)\s+({NUM})\s+({NUM})\s*$", row)
        if m:
            name = _postfix_name(_clean_name(m.group(1)))
            qty = _normalize_qty(_to_float(m.group(2)))
            price = _to_float(m.group(3))
            if qty > 0 and price > 0:
                lines_out.append({"name_raw": name, "qty": qty, "unit": "adet", "unit_price": round(price, 2)})
            i += 1
            continue

        i += 1

    return lines_out[:200]
