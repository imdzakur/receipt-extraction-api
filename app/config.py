import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY belum diisi di .env")
if not GEMINI_MODEL:
    raise RuntimeError("GEMINI_MODEL belum diisi di .env")