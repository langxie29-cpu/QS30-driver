import io
import json
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from zipfile import ZipFile

CODES = ("sbvm552b", "slum488", "slum521", "slvmbx6", "slum712", "slum178")
OUT = Path(__import__("os").environ["TEMP"]) / "nxt-r7-vendor"
OUT.mkdir(exist_ok=True)


def fetch(code):
    url = f"https://www.ti.com/lit/zip/{code}"
    dest = OUT / code
    dest.mkdir(exist_ok=True)
    item = dict(code=code, url=url, checked_utc=datetime.now(timezone.utc).isoformat())
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=18) as response:
            data = response.read()
            item["resolved_url"] = response.url
        item["zip_sha256"] = hashlib.sha256(data).hexdigest()
        with ZipFile(io.BytesIO(data)) as archive:
            files = {}
            for name in archive.namelist():
                if Path(name).suffix.lower() in (".lib", ".cir", ".mod", ".sub", ".txt"):
                    model = archive.read(name)
                    (dest / Path(name).name).write_bytes(model)
                    files[name] = dict(sha256=hashlib.sha256(model).hexdigest(),
                                       encrypted=any(marker in model for marker in (b"$CDNENCSTART", b"$CDNENCFORMAT", b"<Encrypted Library>")))
        item["files"] = files
    except (OSError, ValueError) as error:
        item["error"] = str(error)
    return item


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, CODES))
    target = Path(__file__).resolve().parents[1] / "evidence" / "ti_model_sources.json"
    target.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for entry in results:
        print(entry["code"], entry.get("files", entry.get("error")))
