import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.schemas import Receipt, ReceiptItem  # noqa: E402

TRUTH = ROOT / "eval" / "truth"
OUTPUTS = ROOT / "eval" / "outputs"
ITEMS_FIELD = "items"
EPS = 1e-6

SCALARS = [f for f in Receipt.model_fields if f != ITEMS_FIELD]
ITEM_FIELDS = list(ReceiptItem.model_fields)


def load(path: Path) -> dict:
    return Receipt.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    ).model_dump(mode="json")


def norm(v):
    if isinstance(v, str):
        return " ".join(unicodedata.normalize("NFKC", v).casefold().split())
    return v


def same(a, b) -> bool:
    a, b = norm(a), norm(b)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < EPS
    return a == b


def main() -> None:
    pairs = []
    for t in sorted(TRUTH.glob("*.json")):
        o = OUTPUTS / t.name
        if o.exists():
            pairs.append((t, o))
        else:
            print(f"LEWAT  {t.name} tidak ada outputnya")

    hit, total, trivial = Counter(), Counter(), Counter()
    item_hit, item_total = Counter(), Counter()
    count_ok = 0
    problems = []

    for tf, of in pairs:
        truth = load(tf)
        out = load(of)

        for f in SCALARS:
            tv, ov = truth.get(f), out.get(f)
            total[f] += 1
            if same(tv, ov):
                hit[f] += 1
                if tv is None:
                    trivial[f] += 1
            else:
                problems.append(f"{tf.stem:12} {f:14} truth={tv!r}  model={ov!r}")

        ti = truth.get(ITEMS_FIELD) or []
        oi = out.get(ITEMS_FIELD) or []

        if len(ti) != len(oi):
            problems.append(
                f"{tf.stem:12} jumlah item    truth={len(ti)}  model={len(oi)}"
                "  (item tidak dibandingkan)"
            )
            continue

        count_ok += 1
        for i in range(len(ti)):
            for f in ITEM_FIELDS:
                tv, ov = ti[i].get(f), oi[i].get(f)
                item_total[f] += 1
                if same(tv, ov):
                    item_hit[f] += 1
                else:
                    problems.append(
                        f"{tf.stem:12} item[{i}].{f:10} truth={tv!r}  model={ov!r}"
                    )

    n = len(pairs)
    print(f"\n=== FIELD STRUK  (n={n}) ===")
    for f in SCALARS:
        note = f"   ({trivial[f]} sama-sama null)" if trivial[f] else ""
        print(f"{f:14} {hit[f]}/{total[f]}{note}")
    print(f"{'jumlah item':14} {count_ok}/{n}")

    lines = max(item_total.values()) if item_total else 0
    print(f"\n=== FIELD ITEM  ({count_ok}/{n} struk, {lines} baris) ===")
    for f in ITEM_FIELDS:
        print(f"{f:14} {item_hit[f]}/{item_total[f]}")

    print(f"\n=== SELISIH ({len(problems)}) ===")
    for p in problems:
        print(p)


main()