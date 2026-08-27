from app.config import (
    PRICE_INPUT_PER_1M,
    PRICE_OUTPUT_PER_1M,
    PRICE_SOURCE_DATE,
)


def estimate_cost(usage: dict) -> dict:
    """Hitung biaya satu request dari usage token.

    Token thinking ditagih dengan tarif output, bukan tarif input.
    """
    billable_output = usage["output_tokens"] + usage["thoughts_tokens"]

    usd = (
        usage["input_tokens"] * PRICE_INPUT_PER_1M
        + billable_output * PRICE_OUTPUT_PER_1M
    ) / 1_000_000

    return {
        "usd": round(usd, 8),
        "usd_per_1000_req": round(usd * 1000, 4),
        "billable_output_tokens": billable_output,
        "rate_date": PRICE_SOURCE_DATE,
    }