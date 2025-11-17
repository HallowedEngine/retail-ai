import os
from PIL import Image
import pytesseract
import cv2
import numpy as np

TESSERACT_PATH = os.getenv("TESSERACT_PATH")
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def _preprocess(img_path: str):
    # OpenCV ile okunur, gri ton + kontrast + threshold
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if img is None:
        return Image.open(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # hafif blur + adaptive threshold (kıvrımlı fişlerde iyi çalışır)
    gray = cv2.bilateralFilter(gray, 7, 50, 50)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 35, 11)
    # büyüt (OCR daha iyi okur)
    thr = cv2.resize(thr, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    return Image.fromarray(thr)

def run_tesseract(img_path: str) -> dict:
    pil_img = _preprocess(img_path)
    # Türkçe + İngilizce, LSTM engine, satır düzenli mizanpaj için PSM=6
    cfg = r'--oem 1 --psm 6'
    text = pytesseract.image_to_string(pil_img, lang="tur+eng", config=cfg)
    return {"engine": "tesseract", "text": text, "conf": 0.8}

def run_vision_fallback(img_path: str) -> dict:
    # Şimdilik tesseract’ı tekrar çağırıyoruz (Vision bağlayana kadar)
    return run_tesseract(img_path)

def best_merge(primary: dict, secondary: dict) -> dict:
    if (primary or {}).get("text") and len(primary["text"]) >= len((secondary or {}).get("text","")):
        return primary
    return secondary
