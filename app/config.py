import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY belum diisi di .env")
if not GEMINI_MODEL:
    raise RuntimeError("GEMINI_MODEL belum diisi di .env")

def _require(name: str) -> str:
    raw = os.getenv(name)
    if not raw:
        raise RuntimeError(f"{name} belum diisi di .env")
    return raw

def _require_float(name: str) -> float:
    raw = os.getenv(name)
    if not raw:
        raise RuntimeError(f"{name} belum diisi di .env")
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} harus angka, dapat: {raw!r}") from exc


PRICE_INPUT_PER_1M = _require_float("PRICE_INPUT_PER_1M")
PRICE_OUTPUT_PER_1M = _require_float("PRICE_OUTPUT_PER_1M")
PRICE_SOURCE_DATE = _require("PRICE_SOURCE_DATE")