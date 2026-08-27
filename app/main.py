from fastapi import FastAPI

app = FastAPI(title="Receipt Extraction API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}