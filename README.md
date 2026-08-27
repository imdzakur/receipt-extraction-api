# Receipt Extraction API

Ekstraksi data terstruktur dari foto struk Indonesia memakai vision LLM, dengan biaya per request, pengukuran latensi, validasi aritmatika, dan eval berlabel manual.

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

Respon lengkap `200`:

```json
{
  "request_id": "18a86277c504",
  "data": {
    "merchant": "BreadTalk",
    "tanggal": "2019-05-10",
    "items": [
      {
        "nama": "Bread Butter Pudding",
        "qty": 1,
        "harga_satuan": null,
        "harga_total": 11500
      },
      {
        "nama": "Cream Bruille",
        "qty": 1,
        "harga_satuan": null,
        "harga_total": 14000
      }
    ],
    "subtotal": 25500,
    "pajak": null,
    "total": 25500
  },
  "validation": {
    "ok": true,
    "items_sum": 25500,
    "subtotal_diff": 0,
    "total_diff": 0,
    "issues": [],
    "skipped": ["pajak"]
  },
  "usage": {
    "input_tokens": 1142,
    "output_tokens": 154,
    "thoughts_tokens": 771,
    "total_tokens": 2067
  },
  "cost": {
    "usd": 0.00432525,
    "usd_per_1000_req": 4.3253,
    "billable_output_tokens": 925,
    "rate_date": "2026-08-27"
  },
  "latency_ms": {
    "total": 6199.6,
    "llm": 6199.5
  }
}
```

`harga_satuan` bernilai `null` karena struk ini tidak mencetaknya. `pajak` masuk `skipped`, bukan `issues`, karena cek tidak bisa jalan, bukan gagal.

Nama field berbahasa Indonesia karena deskripsi tiap field dikirim ke model sebagai instruksi ekstraksi.

## Design Decisions

- **Skema sebagai instruksi.** Model Pydantic dikirim sebagai `response_schema`, tiap `Field(description=...)` jadi instruksi ekstraksi. Terukur lebih murah daripada teks bebas, pada gambar yang sama total token turun 2529 ke 1974 dan token reasoning turun 1161 ke 678
- **Hanya `nama`, `qty`, dan `harga_total` yang wajib.** Struk asli sering buram dan terpotong. Skema yang mewajibkan subtotal akan gagal pada struk yang memang tidak mencetaknya
- **Validasi menandai, tidak menolak.** Struk yang aritmatikanya meleset tetap `200` dengan selisihnya dilampirkan. Struk adalah sumber kebenaran, jadi angka yang tidak cocok itu fakta tentang struknya, bukan kesalahan request
- **Selisih angka, bukan boolean.** `total_diff` -1 dan -48000 dua situasi berbeda. `issues` berarti cek berjalan dan menemukan selisih, `skipped` berarti cek tidak bisa jalan
- **Log JSONL tanpa isi struk.** Cuma metadata, token, dan waktu. Tidak ada merchant, item, atau nominal, karena domainnya fintech. Record disusun sebelum blok `try` dan ditulis di `finally`, jadi request yang ditolak tetap tercatat

### Token reasoning ditagih tarif output

```
cost = input_tokens * input_rate + (output_tokens + thoughts_tokens) * output_rate
```

Salah menempatkannya bukan selisih pembulatan. Pada request 1116 input, 258 output, 1789 reasoning, biaya benarnya `$0.00851325`. Kalau reasoning keliru ditagih tarif input, hasilnya `$0.00314625`, meleset 2.7 kali.

Dari tiga request terukur, reasoning menyumbang 83 sampai 97 persen billable output token. Request dengan output paling sedikit justru paling mahal, 77 token output dengan 2281 token reasoning.

## Evaluation

10 struk berlabel manual, dilabeli sebelum output model dilihat. Ditulis sebagai pecahan, bukan persen, karena n=10 terlalu kecil untuk persen.

| Field struk | Cocok |
|---|---|
| merchant | 10 dari 10 |
| tanggal | 10 dari 10 |
| subtotal | 10 dari 10 |
| pajak | 10 dari 10 (2 di antaranya sama-sama `null`) |
| total | 10 dari 10 |
| jumlah item | 8 dari 10 |

| Field item | Cocok |
|---|---|
| nama | 30 dari 30 |
| qty | 30 dari 30 |
| harga_satuan | 30 dari 30 |
| harga_total | 30 dari 30 |

Catatan metode, tanpa ini angka di atas tidak bisa dibaca:

- Skor item dihitung dari 8 struk saja. Pada 2 struk jumlah barisnya bergeser, dan item sengaja tidak dibandingkan sama sekali. Salah memisahkan baris dan salah membaca isi baris adalah dua kegagalan berbeda, jadi dipisah supaya pergeseran satu baris tidak menenggelamkan skor bacaan
- Putaran pertama menghasilkan 17 selisih. Setelah diverifikasi ke foto asli, 14 di antaranya ternyata label yang salah, bukan model. Penyebab terbesarnya `harga_satuan` diisi dari hasil bagi padahal struknya tidak mencetak harga satuan, dan `pajak` diisi `0` padahal baris pajaknya tidak ada
- Karena revisi label itu dilakukan setelah membandingkan, urutan pelabelan tidak sepenuhnya buta. Skor di atas harus dibaca dengan syarat itu
- Pembanding memuat truth dan output lewat skema yang sama sebelum dibandingkan. Sebelum diperbaiki, truth berisi `"70000"` dan output berisi `70000`, dan seluruh field angka keluar 0 dari 10 padahal modelnya benar. Pydantic diam-diam mengubah string jadi int saat validasi, jadi lolos validasi belum menjamin cocok saat dibandingkan mentah
- Satu pelabel, yaitu pengembang sendiri, tanpa pelabel pembanding

Dua selisih yang tersisa punya satu penyebab yang sama, dijelaskan di Known Limitations.

## Measured Performance

Biaya diukur dari 10 request eval. Latensi diukur dari 3 request lewat HTTP, karena eval memanggil fungsi ekstraksi langsung tanpa melewati FastAPI.

| Metrik | Nilai |
|---|---|
| Biaya per request (n=10) | $0.003530 sampai $0.016876 |
| Biaya per 1000 request (n=10) | $3.53 sampai $16.88 |
| Latensi total (n=3, lewat HTTP) | 6199.6 sampai 15561.5 ms |
| Overhead aplikasi (n=3) | 0.1 ms |

- Request termahal 4.8 kali termurah, dan token reasoning berubah bahkan pada input yang sama. Biaya wajib dihitung per request, bukan diestimasi dari satu sampel. Pada n=3 sebarannya cuma 2.24 kali, jadi sebaran ini kemungkinan masih melebar di sampel yang lebih besar
- Ukuran gambar bukan penentu biaya. Gambar terbesar (3472x4624) menghabiskan $0.006054, sementara gambar terkecil dan paling buram (387x516) justru paling mahal, $0.016876. Yang mahal adalah gambar yang sulit dibaca, bukan gambar yang besar
- Overhead aplikasi 0.1 ms melawan panggilan model 6 sampai 15 detik. Optimasi di sisi kode tidak berguna, tuas yang berarti cuma ukuran gambar, ukuran skema, dan budget reasoning
- Request yang ditolak selesai di bawah 1 ms tanpa biaya, karena model tidak pernah dipanggil

## Known Limitations

- Model memasukkan baris voucher dan diskon sebagai item dengan harga negatif, sehingga semua item sesudahnya bergeser satu posisi. Ini penyebab tunggal dari 2 dari 10 struk yang jumlah itemnya salah. Akarnya spesifikasi field yang kurang tegas, bukan kegagalan membaca, dan perbaikannya ada di `Field(description=...)`, bukan di kode
- Korpus eval baru 10 struk. 9 di antaranya di bawah 1000 px pada sisi pendek, dan ekstensinya campur `png`, `jpg`, `jpeg`, jadi kemungkinan besar hasil unduhan, bukan foto kamera. Dua gambar berukuran identik 387x516 dan dicurigai duplikat. Angka eval di atas berlaku untuk korpus ini, bukan untuk struk kamera sungguhan
- `TOLERANCE = 1` dipilih dari sebaran 10 struk dan perlu divalidasi pada sampel yang lebih besar
- Free tier Gemini mengizinkan Google memakai data untuk melatih model, jadi konfigurasi ini tidak layak untuk struk pelanggan sungguhan
- Biaya yang dilaporkan simulasi tarif berbayar, tagihan sebenarnya nol. Tarif `$0.75` dan `$3.75` per 1 juta token adalah harga perkenalan dan naik jadi `$1.50` dan `$7.50` pada 1 Januari 2027
- Struk Indonesia sering mencetak harga item tanpa pajak, hasil bagi harga bruto dengan 1.1. Sisa pembulatannya menumpuk, satu struk uji sudah meleset `total_diff` -1 hanya dengan tiga item
- `validation.ok` bernilai `true` walaupun semua cek dilewati, artinya tidak ada yang gagal, bukan sudah terverifikasi. Kalau `subtotal` kosong, validator memakai jumlah item sebagai basis, dan itu asumsi
- Latensi pada batch eval jauh lebih tinggi daripada latensi lewat HTTP, 14.3 sampai 149.3 detik. Penyebabnya diduga retry rate limit free tier, tapi belum diverifikasi ke `thoughts_tokens`, jadi angka itu sengaja tidak dipakai sebagai angka performa
- Pesan exception internal bocor lewat `HTTPException.detail`, `X-Request-ID` cuma dikirim pada respon `200`, dan MIME yang ditolak belum jadi field terstruktur di log

## Not In Scope

Frontend, autentikasi, database, containerisasi, test suite, RAG, vector store, agent, deployment, dan input PDF. Tidak satu pun membuat model biaya, logika validasi, atau eval di sini jadi lebih baik, dan tiga hal itulah inti project ini.