import os, json, time, hashlib, re, shutil
from typing import Any, Dict, Optional, List

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

_num_re = re.compile(r"(\d+)")

def natural_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in _num_re.split(s)]

def list_images_recursive(root: str) -> List[str]:
    exts = {".jpg",".jpeg",".png",".webp",".tif",".tiff",".bmp"}
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in exts:
                out.append(os.path.join(dirpath, fn))
    out.sort(key=lambda p: natural_key(os.path.basename(p)))
    return out

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
