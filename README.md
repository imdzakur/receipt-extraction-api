# Receipt Extraction API

Ekstraksi data terstruktur dari foto struk Indonesia memakai vision LLM, dengan biaya per request, pengukuran latensi, dan validasi aritmatika.

Portfolio LLM application engineering untuk domain fintech. Fokusnya bukan memanggil API model, tapi rekayasa di sekitarnya.

## Stack

Python 3.14, FastAPI, uvicorn, Pydantic, Gemini 3.6 Flash lewat `google-genai`.

## Setup

```bash
git clone <REPO_URL>
cd receipt-extraction-api

python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Salin `.env.example` jadi `.env`, isi `GEMINI_API_KEY` dan tarif harga. `app/config.py` gagal cepat saat startup kalau ada yang kosong.

```bash
python -m uvicorn app.main:app --reload
```

Dokumentasi interaktif di `http://127.0.0.1:8000/docs`.

## API

`GET /health` mengembalikan `{"status": "ok"}`.

`POST /extract` menerima `multipart/form-data` dengan satu field `file`.

| Status | Kondisi |
|---|---|
| `200` | Berhasil |
| `415` | MIME di luar `image/jpeg` dan `image/png` |
| `413` | File lebih dari 10 MB |
| `502` | Panggilan model gagal |

MIME dicek sebelum file dibaca ke memori, jadi PDF 20 MB ditolak tanpa pernah dibuffer.

```json
{
  "request_id": "18a86277c504",
  "data": {
    "merchant": "BreadTalk",
    "tanggal": "2019-05-10",
    "items": [
      { "nama": "Bread Butter Pudding", "qty": 1, "harga_satuan": null, "harga_total": 11500 },
      { "nama": "Cream Bruille", "qty": 1, "harga_satuan": null, "harga_total": 14000 }
    ],
    "subtotal": 43500, "pajak": null, "total": 43500
  },
  "validation": { "ok": true, "items_sum": 43500, "subtotal_diff": 0, "total_diff": 0, "issues": [], "skipped": [] },
  "usage": { "input_tokens": 1142, "output_tokens": 154, "thoughts_tokens": 771, "total_tokens": 2067 },
  "cost": { "usd": 0.00432525, "usd_per_1000_req": 4.3253, "billable_output_tokens": 925, "rate_date": "2026-08-27" },
  "latency_ms": { "total": 6199.6, "llm": 6199.5 }
}
```

Nama field berbahasa Indonesia karena deskripsi tiap field dikirim ke model sebagai instruksi ekstraksi.

## Design Decisions

- **Skema sebagai instruksi.** Model Pydantic dikirim sebagai `response_schema`, tiap `Field(description=...)` jadi instruksi ekstraksi. Terukur lebih murah daripada teks bebas: pada gambar yang sama total token turun 2529 ke 1974, token reasoning turun 1161 ke 678
- **Hanya `nama`, `qty`, dan `harga_total` yang wajib.** Struk asli sering buram dan terpotong. Skema yang mewajibkan subtotal akan gagal pada struk yang memang tidak mencetaknya
- **Validasi menandai, tidak menolak.** Struk yang aritmatikanya meleset tetap 200 dengan selisihnya dilampirkan. Struk adalah sumber kebenaran, jadi angka yang tidak cocok itu fakta tentang struknya, bukan kesalahan request
- **Selisih angka, bukan boolean.** `total_diff` -1 dan -48000 dua situasi berbeda. `issues` berarti cek berjalan dan menemukan selisih, `skipped` berarti cek tidak bisa jalan
- **Log JSONL tanpa isi struk.** Cuma metadata, token, dan waktu. Tidak ada merchant, item, atau nominal, karena domainnya fintech. Record disusun sebelum blok `try` dan ditulis di `finally`, jadi request yang ditolak tetap tercatat

### Token reasoning ditagih tarif output

```
cost = input_tokens * input_rate + (output_tokens + thoughts_tokens) * output_rate
```

Salah menempatkannya bukan selisih pembulatan. Pada request 1116 input, 258 output, 1789 reasoning, biaya benarnya `$0.00851325`. Kalau reasoning keliru ditagih tarif input, hasilnya `$0.00314625`, meleset 2.7 kali.

Dari tiga request terukur, reasoning menyumbang 83 sampai 97 persen billable output token. Request dengan output paling sedikit justru paling mahal: 77 token output, 2281 token reasoning.

## Measured Performance

Sampel 3 request sukses. Ditampilkan sebagai rentang, karena sebaran 6.2 sampai 15.6 detik dari tiga titik tidak layak diringkas jadi satu angka.

| Metrik | Median | Rentang |
|---|---|---|
| Latensi total | 12480.8 ms | 6199.6 sampai 15561.5 ms |
| Latensi model | 12480.7 ms | |
| Overhead aplikasi | 0.1 ms | 0.1 sampai 0.1 ms |
| Biaya per 1000 request | $4.4947 | $4.3253 sampai $9.7073 |
| Token reasoning | | 771 sampai 2281 |

- Overhead aplikasi 0.1 ms melawan panggilan model 6 sampai 15 detik. Optimasi di sisi kode tidak berguna, tuas yang berarti cuma ukuran gambar, ukuran skema, dan budget reasoning
- Request termahal 2.24 kali termurah, dan token reasoning berubah bahkan pada input yang sama. Biaya wajib dihitung per request, bukan diestimasi
- Request yang ditolak selesai di bawah 1 ms tanpa biaya, karena model tidak pernah dipanggil

## Known Limitations

- Free tier Gemini mengizinkan Google memakai data untuk melatih model, jadi konfigurasi ini tidak layak untuk struk pelanggan sungguhan
- Biaya yang dilaporkan simulasi tarif berbayar, tagihan sebenarnya nol. Tarif `$0.75` dan `$3.75` per 1 juta token adalah harga perkenalan dan naik jadi `$1.50` dan `$7.50` pada 1 Januari 2027
- `TOLERANCE = 1` disetel dari dua sampel. Nilai finalnya menunggu eval 30 struk berlabel manual, dan semua angka di README ini harus dihasilkan ulang dari situ
- Struk Indonesia sering mencetak harga item tanpa pajak, hasil bagi harga bruto dengan 1.1. Sisa pembulatannya menumpuk, satu struk uji sudah meleset `total_diff` -1 hanya dengan tiga item
- `validation.ok` bernilai `true` walaupun semua cek dilewati, artinya tidak ada yang gagal, bukan sudah terverifikasi. Kalau `subtotal` kosong, validator memakai jumlah item sebagai basis, dan itu asumsi
- Satu struk uji mengembalikan dua baris `HAND TOWEL` identik, belum dikonfirmasi apakah struk fisiknya memang begitu
- Korpus uji baru tiga struk, semuanya sekitar 143 KB. Resolusi belum dikontrol, dan itu penyebab paling mungkin field footer hilang
- Pesan exception internal bocor lewat `HTTPException.detail`, `X-Request-ID` cuma dikirim pada respon 200, dan MIME yang ditolak belum jadi field terstruktur

## Not In Scope

Frontend, autentikasi, database, containerisasi, test suite, RAG, vector store, agent, deployment, dan input PDF. Tidak satu pun membuat model biaya atau logika validasi di sini jadi lebih baik, dan dua hal itulah inti project ini.