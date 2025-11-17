import re
from datetime import datetime
from typing import Optional, Tuple

# GS1-128 Application Identifiers
# (17) = Expiry date YYMMDD
# (10) = Batch/Lot
# Metinden SKT yakalama için TR/EN anahtar kelimeler de var.

def parse_gs1_from_text(s: str) -> Tuple[Optional[datetime], Optional[str]]:
    """
    GS1 string içinden (17)YYYYMMDD ve (10)LotCode ayrıştırır.
    Örnek: "(01)08690000000012(17)260912(10)LOT123"
    """
    if not s:
        return None, None
    # AI (17) -> YYMMDD
    m_exp = re.search(r"\(17\)\s*(\d{6})", s)
    expiry = None
    if m_exp:
        yy, mm, dd = m_exp.group(1)[0:2], m_exp.group(1)[2:4], m_exp.group(1)[4:6]
        # 20xx varsayımı
        year = 2000 + int(yy)
        expiry = datetime(year, int(mm), int(dd))
    # AI (10) -> LOT (değişken uzunluk, sonraki parantez veya EOL'e kadar)
    m_lot = re.search(r"\(10\)\s*([A-Za-z0-9\-_.]+)", s)
    lot = m_lot.group(1) if m_lot else None
    return expiry, lot

def parse_expiry_from_free_text(s: str) -> Optional[datetime]:
    """
    Serbest metinden SKT/TETT tarihi yakalar: 12.03.2026, 12/03/26, 2026-03-12 gibi.
    """
    if not s:
        return None
    # Ortak tarih formatları
    #  DD.MM.YYYY | DD/MM/YYYY | YYYY-MM-DD | DD-MM-YYYY | DD.MM.YY | DD/MM/YY
    pats = [
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})",
        r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})",
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{2})",
    ]
    s_norm = s.strip()
    # Anahtar kelime ipucuları: SKT, TETT, EXP, Use by, Son kullanma
    if re.search(r"\b(SKT|TETT|EXP|Use\s*by|Son\s*kullanma)\b", s_norm, re.IGNORECASE):
        pass
    for p in pats:
        m = re.search(p, s_norm)
        if not m:
            continue
        g = m.groups()
        if len(g) == 3:
            # yıl başta ise
            if len(g[0]) == 4:
                y, mth, d = int(g[0]), int(g[1]), int(g[2])
            else:
                d, mth, y = int(g[0]), int(g[1]), int(g[2])
                if y < 100:  # YY ise 20YY kabulü
                    y = 2000 + y
            try:
                return datetime(y, mth, d)
            except ValueError:
                continue
    return None
