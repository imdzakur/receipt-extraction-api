from app.schemas import Receipt

TOLERANCE = 1


def check_arithmetic(receipt: Receipt) -> dict:
    issues: list[str] = []
    skipped: list[str] = []

    items_sum = sum(item.harga_total for item in receipt.items)
    if not receipt.items:
        skipped.append("Tidak ada item yang terbaca")

    subtotal_diff = None
    if receipt.subtotal is None:
        skipped.append("Subtotal tidak tercetak, cek jumlah item dilewati")
    else:
        subtotal_diff = receipt.subtotal - items_sum
        if abs(subtotal_diff) > TOLERANCE:
            issues.append(
                f"Jumlah item {items_sum} tidak sama dengan subtotal "
                f"{receipt.subtotal}, selisih {subtotal_diff}"
            )

    total_diff = None
    if receipt.total is None:
        skipped.append("Total tidak tercetak, cek total dilewati")
    else:
        base = items_sum if receipt.subtotal is None else receipt.subtotal
        expected = base + (receipt.pajak or 0)
        total_diff = receipt.total - expected
        if abs(total_diff) > TOLERANCE:
            issues.append(
                f"Subtotal plus pajak {expected} tidak sama dengan total "
                f"{receipt.total}, selisih {total_diff}"
            )

    return {
        "ok": not issues,
        "items_sum": items_sum,
        "subtotal_diff": subtotal_diff,
        "total_diff": total_diff,
        "issues": issues,
        "skipped": skipped,
    }