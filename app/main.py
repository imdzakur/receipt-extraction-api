from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.llm import extract_receipt
from app.validation import check_arithmetic

ALLOWED_MIME = {"image/jpeg", "image/png"}
MAX_FILE_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Receipt Extraction API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)) -> dict[str, object]:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Format {file.content_type} tidak didukung. Gunakan jpg atau png.",
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File {len(contents)} byte melebihi batas {MAX_FILE_BYTES} byte.",
        )

    try:
        receipt, usage = await run_in_threadpool(
            extract_receipt, contents, file.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal ekstraksi: {e}")

    return {
        "data": receipt,
        "validation": check_arithmetic(receipt),
        "usage": usage,
    }