from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT = (
    "Baca struk belanja ini. Keluarkan semua teks yang terlihat, "
    "apa adanya, urut dari atas ke bawah. "
    "Jangan menambah, menyimpulkan, atau merapikan apa pun. "
    "Kalau ada bagian yang tidak terbaca, tulis [tidak terbaca]."
)


def extract_text_from_image(image_bytes: bytes, mime_type: str) -> tuple[str, dict]:
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            PROMPT,
        ],
    )
    um = resp.usage_metadata
    usage = {
        "input_tokens": um.prompt_token_count,
        "output_tokens": um.candidates_token_count,
        "thoughts_tokens": um.thoughts_token_count or 0,
        "total_tokens": um.total_token_count,
    }
    return resp.text, usage