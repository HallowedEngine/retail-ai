from pathlib import Path
import uuid, os
import hashlib

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_upload(file_obj, filename_hint="invoice") -> str:
    ext = Path(file_obj.filename).suffix if hasattr(file_obj, "filename") else ".jpg"
    out = UPLOAD_DIR / f"{filename_hint}_{uuid.uuid4().hex}{ext}"
    with open(out, "wb") as f:
        f.write(file_obj.file.read())
    return str(out)

def file_md5(path: str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
