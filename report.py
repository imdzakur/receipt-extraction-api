import json
import statistics

rows = []
with open("logs/requests.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

ok = [r for r in rows if r["status"] == 200]
fail = [r for r in rows if r["status"] != 200]

total = [r["latency_ms_total"] for r in ok]
llm = [r["latency_ms_llm"] for r in ok]
cost = [r["cost_usd"] for r in ok]
thoughts = [r["thoughts_tokens"] for r in ok]
out = [r["output_tokens"] for r in ok]

print("total baris:", len(rows))
print("status:", [r["status"] for r in rows])
print("n sukses:", len(ok))
print()
print("latensi total ms, median:", statistics.median(total))
print("latensi total ms, rentang:", min(total), "-", max(total))
print("latensi llm ms, median:", statistics.median(llm))
print("overhead kode ms:", [round(a - b, 2) for a, b in zip(total, llm)])
print()
print("biaya per 1000 req, median:", round(statistics.median(cost) * 1000, 4))
print("biaya per 1000 req, rentang:", round(min(cost) * 1000, 4), "-", round(max(cost) * 1000, 4))
print("thoughts, rentang:", min(thoughts), "-", max(thoughts))
print("porsi thoughts dari output:", [round(t / (t + o) * 100) for t, o in zip(thoughts, out)])
print()
for r in fail:
    print("gagal", r["status"],
          "| latensi", r["latency_ms_total"],
          "| cost_usd ada:", "cost_usd" in r,
          "| latency_ms_llm ada:", "latency_ms_llm" in r)