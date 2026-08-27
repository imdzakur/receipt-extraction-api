from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.schemas import Receipt

client = genai.Client(api_key=GEMINI_API_KEY)

MAX_OUTPUT_TOKENS = 8192

PROMPT = (
    "Baca struk belanja ini. Keluarkan semua teks yang terlihat, "
    "apa adanya, urut dari atas ke bawah. "
    "Jangan menambah, menyimpulkan, atau merapikan apa pun. "
    "Kalau ada bagian yang tidak terbaca, tulis [tidak terbaca]."
)

RECEIPT_PROMPT = (
    "Ekstrak data dari struk belanja ini sesuai schema yang diberikan. "
    "Ambil angka apa adanya seperti tercetak, jangan menghitung sendiri "
    "dan jangan memperbaiki angka yang terlihat tidak konsisten. "
    "Hilangkan pemisah ribuan, tulis 43500 bukan 43,500. "
    "Kalau sebuah nilai tidak tercetak di struk, isi null, jangan menebak."
)


def _build_usage(resp) -> dict:
    um = resp.usage_metadata
    return {
        "input_tokens": um.prompt_token_count or 0,
        "output_tokens": um.candidates_token_count or 0,
        "thoughts_tokens": um.thoughts_token_count or 0,
        "total_tokens": um.total_token_count or 0,
    }

def _guard(resp) -> None:
    if not resp.candidates:
        blocked = getattr(resp.prompt_feedback, "block_reason", None)
        raise RuntimeError(f"Gemini tidak balikin kandidat, block_reason={blocked}")

    finish = resp.candidates[0].finish_reason
    reason = getattr(finish, "name", str(finish))
    if reason != "STOP":
        raise RuntimeError(f"Gemini berhenti tidak normal: {reason}")


def extract_text_from_image(image_bytes: bytes, mime_type: str) -> tuple[str, dict]:
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )

    if not resp.candidates:
        blocked = getattr(resp.prompt_feedback, "block_reason", None)
        raise RuntimeError(f"Gemini tidak balikin kandidat, block_reason={blocked}")

    finish = resp.candidates[0].finish_reason
    reason = getattr(finish, "name", str(finish))
    if reason != "STOP":
        raise RuntimeError(f"Gemini berhenti tidak normal: {reason}")

    text = resp.text
    if not text or not text.strip():
        raise RuntimeError("Gemini balikin teks kosong")

    return text, _build_usage(resp)

def extract_receipt(image_bytes: bytes, mime_type: str) -> tuple[Receipt, dict]:
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            RECEIPT_PROMPT,
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
            response_schema=Receipt,
        ),
    )

    _guard(resp)

    receipt = resp.parsed
    if receipt is None:
        raise RuntimeError(f"Gagal parsing JSON dari Gemini: {resp.text!r}")

    return receipt, _build_usage(resp)