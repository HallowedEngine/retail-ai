# app/match.py
from typing import Optional, Dict, List, Tuple

# RapidFuzz varsa kullan, yoksa difflib'e düş
_USE_RAPID = True
try:
    from rapidfuzz import process, fuzz
except Exception:
    _USE_RAPID = False
    import difflib

def build_product_name_map(products: List[Dict]) -> Dict[str, int]:
    """
    [{"id":1,"name":"1L Süt"}, ...] -> {"1L Süt": 1, ...}
    """
    out: Dict[str, int] = {}
    for p in products:
        name = (p.get("name") or "").strip()
        pid = p.get("id")
        if name and pid is not None:
            out[name] = pid
    return out

def fuzzy_match_product(
    name_raw: str,
    product_map: Dict[str, int],
    score_cutoff: int = 80
) -> Tuple[Optional[int], float]:
    """
    name_raw'ı product_map anahtarlarına eşle.
    RapidFuzz varsa WRatio, yoksa difflib yakın eşleşme kullanır.
    Dönen: (product_id | None, skor)
    """
    if not name_raw or not product_map:
        return None, 0.0

    choices = list(product_map.keys())

    if _USE_RAPID:
        best = process.extractOne(name_raw, choices, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
        if not best:
            return None, 0.0
        matched_name, score, _ = best
        return product_map.get(matched_name), float(score)

    # difflib: cutoff 0..1 arası; score_cutoff %’ünü normalize et
    cutoff = max(0.0, min(1.0, score_cutoff / 100.0))
    match = difflib.get_close_matches(name_raw, choices, n=1, cutoff=cutoff)
    if not match:
        return None, 0.0
    # difflib skor bırakmadığı için basitçe 100 veriyoruz (eşik mantığı için yeterli)
    return product_map.get(match[0]), 100.0
