import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.llm import extract_receipt  # noqa: E402
from app.pricing import estimate_cost  # noqa: E402

IMAGES = ROOT / "eval" / "images"
OUTPUTS = ROOT / "eval" / "outputs"
RUNS = OUTPUTS / "_runs.jsonl"

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
SLEEP_SECONDS = 4


def log(record: dict) -> None:
    with RUNS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    images = sorted(p for p in IMAGES.iterdir() if p.suffix.lower() in MIME)

    for img in images:
        out = OUTPUTS / f"{img.stem}.json"
        if out.exists():
            print(f"SKIP  {img.name}")
            continue

        started = time.perf_counter()
        try:
            receipt, usage = extract_receipt(img.read_bytes(), MIME[img.suffix.lower()])
        except Exception as exc:
            elapsed = (time.perf_counter() - started) * 1000
            print(f"GAGAL {img.name}: {exc}")
            log({"file": img.name, "status": "error", "error": str(exc),
                 "latency_ms": round(elapsed, 1)})
            time.sleep(SLEEP_SECONDS)
            continue

        elapsed = (time.perf_counter() - started) * 1000
        out.write_text(
            json.dumps(receipt.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        cost = estimate_cost(usage)
        log({"file": img.name, "status": "ok", "latency_ms": round(elapsed, 1),
             **usage, "cost_usd": cost["usd"]})
        print(f"OK    {img.name}  {elapsed:.0f} ms  {cost['usd']:.6f} usd")
        time.sleep(SLEEP_SECONDS)


main()