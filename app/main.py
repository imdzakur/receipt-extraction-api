from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.llm import extract_receipt
from app.observability import log_request
from app.pricing import estimate_cost
from app.validation import check_arithmetic

ALLOWED_MIME = {"image/jpeg", "image/png"}
MAX_FILE_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Receipt Extraction API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract")
async def extract(
    response: Response,
    file: UploadFile = File(...),
) -> dict[str, object]:
    request_id = uuid4().hex[:12]
    t0 = perf_counter()
    record: dict[str, object] = {
        "request_id": request_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "endpoint": "/extract",
        "status": 500,
    }

    try:
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(
                status_code=415,
                detail=f"Format {file.content_type} tidak didukung. Gunakan jpg atau png.",
            )

        record["mime"] = file.content_type

        contents = await file.read()
        record["size_bytes"] = len(contents)

        if len(contents) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File {len(contents)} byte melebihi batas {MAX_FILE_BYTES} byte.",
            )

        t_llm = perf_counter()
        try:
            receipt, usage = await run_in_threadpool(
                extract_receipt, contents, file.content_type
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Gagal ekstraksi: {exc}") from exc
        finally:
            record["latency_ms_llm"] = round((perf_counter() - t_llm) * 1000, 1)

        record.update(usage)
        cost = estimate_cost(usage)
        record["cost_usd"] = cost["usd"]

        validation = check_arithmetic(receipt)
        record["issue_count"] = len(validation["issues"])
        record["skipped_count"] = len(validation["skipped"])

        record["status"] = 200
        response.headers["X-Request-ID"] = request_id

        return {
            "request_id": request_id,
            "data": receipt,
            "validation": validation,
            "usage": usage,
            "cost": cost,
            "latency_ms": {
                "total": round((perf_counter() - t0) * 1000, 1),
                "llm": record["latency_ms_llm"],
            },
        }

    except HTTPException as exc:
        record["status"] = exc.status_code
        record["error"] = str(exc.detail)
        raise

    finally:
        record["latency_ms_total"] = round((perf_counter() - t0) * 1000, 1)
        log_request(**record)