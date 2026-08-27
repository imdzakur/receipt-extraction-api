# Receipt Extraction API

Ekstraksi data terstruktur dari foto struk belanja Indonesia menggunakan vision LLM, lengkap dengan perhitungan biaya per request, pengukuran latensi, dan validasi aritmatika.

Dibangun sebagai portfolio LLM application engineering untuk domain fintech. Fokusnya bukan sekadar memanggil API model, melainkan rekayasa di sekitarnya: validasi input, output yang dibatasi skema, atribusi biaya, observability, dan pelaporan jujur soal apa yang belum bisa dilakukan sistem ini.

## What It Does

`POST /extract` menerima foto struk dan mengembalikan:

- `data`, berisi merchant, tanggal, daftar item, subtotal, pajak, dan total sebagai model Pydantic tervalidasi
- `validation`, hasil cek silang aritmatika antara item, subtotal, dan total
- `usage`, jumlah token input, output, dan reasoning
- `cost`, estimasi biaya dolar untuk request tersebut
- `latency_ms`, waktu total dan waktu murni pemanggilan model

Semua request, termasuk yang ditolak, dicatat ke log JSONL untuk dianalisis kemudian.

## Example Response

```json
{
  "request_id": "18a86277c504",
  "data": {
    "merchant": "BreadTalk",
    "tanggal": "2019-05-10",
    "items": [
      { "nama": "Bread Butter Pudding", "qty": 1, "harga_satuan": null, "harga_total": 11500 },
      { "nama": "Cream Bruille", "qty": 1, "harga_satuan": null, "harga_total": 14000 },
      { "nama": "Choco Croissant", "qty": 1, "harga_satuan": null, "harga_total": 10500 },
      { "nama": "Bank Of Chocolat", "qty": 1, "harga_satuan": null, "harga_total": 7500 }
    ],
    "subtotal": 43500,
    "pajak": null,
    "total": 43500
  },
  "validation": {
    "ok": true,
    "items_sum": 43500,
    "subtotal_diff": 0,
    "total_diff": 0,
    "issues": [],
    "skipped": []
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
  "latency_ms": { "total": 6199.6, "llm": 6199.5 }
}
```

Nama field di `data` sengaja berbahasa Indonesia. Dokumen yang diproses adalah struk Indonesia, dan deskripsi tiap field dikirim ke model sebagai instruksi ekstraksi, sehingga lebih akurat dalam bahasa asli dokumennya.

## Stack

Python 3.14, FastAPI, uvicorn, Pydantic, dan Google Gemini 3.6 Flash lewat `google-genai`.

Tanpa database, tanpa autentikasi, tanpa container. Semua itu memang dikeluarkan dari scope, lihat bagian Not In Scope.

## Setup

```bash
git clone <REPO_URL>
cd receipt-extraction-api

python -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell
# source .venv/bin/activate       # bash

python -m pip install -r requirements.txt
```

Salin `.env.example` menjadi `.env`, lalu isi:

```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
PRICE_INPUT_PER_1M=0.75
PRICE_OUTPUT_PER_1M=3.75
PRICE_SOURCE_DATE=2026-08-27
```

`app/config.py` gagal cepat saat startup kalau ada variabel yang kosong. Konfigurasi yang salah tidak boleh sampai melayani request pertama.

Jalankan:

```bash
python -m uvicorn app.main:app --reload
```

Dokumentasi interaktif ada di `http://127.0.0.1:8000/docs`.

## API Reference

`GET /health` mengembalikan `{"status": "ok"}` dengan status 200.

`POST /extract` menerima `multipart/form-data` dengan satu field bernama `file`.

| Status | Kondisi |
|---|---|
| `200` | Ekstraksi berhasil |
| `415` | Tipe MIME di luar `image/jpeg` dan `image/png` |
| `413` | Ukuran file lebih dari 10 MB |
| `502` | Panggilan ke model gagal |

Urutan validasinya disengaja. Tipe MIME dicek sebelum isi file dibaca ke memori, sehingga PDF 20 MB ditolak tanpa pernah dibuffer. Ukuran baru dicek setelah pembacaan, karena jumlah byte yang sebenarnya adalah satu-satunya angka yang layak dipercaya.

Respon 200 menyertakan header `X-Request-ID` yang sama dengan `request_id` di body.

## Design Decisions

### Schema-Constrained Output

Skema ekstraksi ada di `app/schemas.py` sebagai model Pydantic, lalu dikirim ke model sebagai `response_schema` bersama `response_mime_type="application/json"`. Setiap field punya `Field(description=...)` yang sekaligus menjadi instruksi ekstraksi untuk field itu.

Efek samping yang terukur: output terstruktur ternyata lebih murah daripada ekstraksi teks bebas. Pada gambar yang sama, total token turun dari 2529 ke 1974, dan token reasoning turun dari 1161 ke 678. Model tidak perlu memikirkan format keluarannya sendiri.

Hanya `nama`, `qty`, dan `harga_total` yang wajib. Sisanya opsional, karena struk asli memang sering buram, terpotong, dan tidak konsisten. Skema yang mewajibkan subtotal akan gagal pada struk yang memang tidak mencetak subtotal.

Nominal memakai `int` karena rupiah tidak punya sen dalam praktik ritel, dan float mengundang penyimpangan pembulatan. `qty` memakai `float` karena ada barang yang dijual per timbangan.

### Validation Flags, Never Rejects

`app/validation.py` mencocokkan jumlah item dengan subtotal dan total, dan tidak pernah melempar exception. Struk yang aritmatikanya tidak cocok tetap dikembalikan dengan status 200, dengan selisihnya dilampirkan.

Ini perilaku yang benar untuk layanan ingest dokumen. Struk adalah sumber kebenaran. Kalau angka di struk memang tidak cocok, itu fakta tentang struknya, bukan kesalahan request. Menolaknya justru membuang satu-satunya salinan data dan tidak memberi tahu apa pun kepada pemanggil.

Respon memisahkan dua hal yang berbeda. `issues` berarti pengecekan berjalan dan menemukan selisih. `skipped` berarti pengecekan tidak bisa dijalankan karena field sumbernya tidak ada.

Yang dikembalikan adalah selisih angka, bukan boolean. `total_diff` bernilai -1 dan -48000 adalah dua situasi yang sangat berbeda, dan boolean menghapus perbedaan itu.

### Reasoning Tokens Drive Cost

Gemini 3.6 Flash adalah model reasoning. Token reasoning dihitung terpisah, ditagih dengan tarif output, dan porsinya dominan.

```
cost = input_tokens * input_rate + (output_tokens + thoughts_tokens) * output_rate
```

Salah di sini bukan sekadar selisih pembulatan. Pada request dengan 1116 token input, 258 output, dan 1789 reasoning, biaya yang benar adalah `$0.00851325`. Kalau token reasoning keliru ditagih dengan tarif input, hasilnya `$0.00314625`, meleset 2.7 kali lipat.

Dari tiga request sukses yang diukur, token reasoning menyumbang 83 sampai 97 persen dari billable output token, dan 67 sampai 88 persen dari total biaya dolar. Request yang output-nya paling sedikit justru yang paling mahal: 77 token output, 2281 token reasoning.

Biaya dibulatkan ke 8 desimal, bukan 2. Satu request harganya sekitar setengah sen, jadi pembulatan ke sen membuat semua baris log bernilai `0.01` dan datanya kehilangan makna.

### Observability

`app/observability.py` menulis satu objek JSON per baris ke stdout dan ke `logs/requests.jsonl`. Tanpa formatter, supaya tiap baris tetap JSON murni yang bisa di-parse. `propagate` diset `False` supaya baris tidak dobel dengan handler milik uvicorn.

Handler di `app/main.py` menyusun record log sebelum blok `try`, dengan status default 500, lalu menulisnya di `finally`. Karena itu request yang ditolak tetap tercatat dengan status aslinya. Blok pemanggilan model punya `finally` sendiri, sehingga latensi model tetap tercatat walaupun panggilannya gagal.

Pengukuran waktu memakai `perf_counter`, bukan `time.time`, karena jam dinding bisa mundur.

Log sengaja tidak menyimpan isi struk. Tidak ada nama merchant, nama item, maupun nominal. Hanya metadata, jumlah token, dan waktu. Domainnya fintech, dan file log adalah tempat yang salah untuk data transaksi.

`report.py` membaca log lalu mencetak median, rentang, biaya per 1000 request, dan porsi token reasoning.

## Measured Performance

Sampelnya 3 request sukses dan 2 request ditolak. Angka di bawah ini bukan median yang stabil, dan sengaja ditampilkan sebagai rentang, karena sampel tiga titik yang menyebar dari 6.2 sampai 15.6 detik tidak layak diringkas jadi satu angka tunggal.

| Metrik | Median | Rentang |
|---|---|---|
| Latensi total | 12480.8 ms | 6199.6 sampai 15561.5 ms |
| Latensi model | 12480.7 ms | tidak berlaku |
| Overhead aplikasi | 0.1 ms | 0.1 sampai 0.1 ms |
| Biaya per 1000 request | $4.4947 | $4.3253 sampai $9.7073 |
| Token reasoning | tidak berlaku | 771 sampai 2281 |
| Porsi reasoning dari billable output | tidak berlaku | 83 sampai 97 persen |

Request yang ditolak, baik 415 maupun 413, selesai di bawah 1 ms dan tidak memakan biaya sama sekali, karena model tidak pernah dipanggil.

Tiga kesimpulan yang bisa ditarik:

- Optimasi latensi di sisi aplikasi tidak ada gunanya. Overhead-nya 0.1 ms melawan panggilan model 6 sampai 15 detik, dan konsisten di ketiga request. Satu-satunya tuas yang berarti adalah ukuran gambar, ukuran skema, dan budget reasoning
- Biaya tidak bisa diestimasi dari satu sampel. Request termahal harganya 2.24 kali request termurah. Jumlah token reasoning juga berubah pada input yang sama, jadi biaya wajib dihitung per request
- Budget reasoning adalah tuas biaya terbesar yang tersisa, dan belum disetel sama sekali

## Known Limitations

Ditulis lengkap, karena portfolio yang menyembunyikan mode kegagalannya tidak menunjukkan pertimbangan rekayasa apa pun.

Soal data dan privasi:

- Free tier Gemini mengizinkan Google memakai data yang dikirim untuk melatih model. Dengan konfigurasi ini, layanan tersebut tidak layak dipakai untuk struk pelanggan sungguhan
- Biaya yang dilaporkan adalah simulasi terhadap tarif berbayar. Tagihan sebenarnya nol, karena project ini berjalan di free tier. Angkanya untuk perencanaan kapasitas, bukan untuk pembukuan
- Tarif yang dipakai, $0.75 dan $3.75 per 1 juta token, adalah harga perkenalan Gemini 3.6 Flash dan naik menjadi $1.50 dan $7.50 pada 1 Januari 2027. `PRICE_SOURCE_DATE` ikut dikembalikan di setiap respon supaya angka yang basi bisa dikenali sendiri

Soal ketepatan:

- `TOLERANCE = 1` pada pengecekan aritmatika masih sementara. Nilainya disetel dari dua sampel dan belum bisa dipertahankan sebelum eval 30 struk dijalankan
- Struk Indonesia sering mencetak harga item tanpa pajak, hasil membagi harga bruto yang sudah bulat dengan 1,1. Sisa pembulatannya menumpuk antar item. Satu struk uji menghasilkan `total_diff` -1 hanya dengan tiga item, dan selisihnya diperkirakan membesar seiring jumlah item. Inilah alasan validasi menandai, bukan menolak
- Kalau `subtotal` tidak ada, validator memakai jumlah item sebagai basis. Itu asumsi, bukan angka terverifikasi, dan artinya pengecekan subtotal jadi membandingkan item dengan dirinya sendiri
- `validation.ok` bernilai `true` walaupun semua pengecekan dilewati. Artinya tidak ada yang gagal, bukan sudah terverifikasi. Pemanggil harus membaca `skipped` sebelum mempercayai `ok`
- Satu struk uji mengembalikan dua baris `HAND TOWEL` yang identik. Apakah struk fisiknya memang mencetak dua baris belum dikonfirmasi. Duplikasi hasil halusinasi adalah mode kegagalan yang masuk akal, dan justru itu yang harus ditangkap oleh eval
- Korpus uji sejauh ini hanya tiga struk, semuanya berukuran sekitar 143 KB. Resolusi gambar belum dikontrol, dan resolusi rendah adalah penyebab paling mungkin dari field footer yang hilang

Soal antarmuka:

- Pesan exception internal bocor ke klien lewat `HTTPException.detail`. Bisa diterima untuk demo, tidak untuk produksi
- `X-Request-ID` hanya dikirim pada respon 200. Respon error dibuat oleh exception handler FastAPI yang tidak melihat objek `Response` milik handler. ID-nya tetap tercatat di log, jadi request gagal masih bisa ditelusuri dari sisi server
- Pada jalur 415, tipe MIME yang ditolak hanya ada di dalam string `error` yang ditujukan untuk manusia, bukan sebagai field terstruktur. Mengambilnya sekarang berarti harus mem-parsing kalimat

## Roadmap

- Eval 30 struk dengan label manual, menghasilkan akurasi per field dan nilai `TOLERANCE` yang bisa dipertanggungjawabkan. Semua angka latensi dan biaya di README ini harus dihasilkan ulang dari eval tersebut
- Penyetelan budget reasoning, yang sudah teridentifikasi sebagai tuas biaya paling besar
- Menaikkan `mime` menjadi field terstruktur pada jalur 415

## Not In Scope

Sengaja dikeluarkan supaya project ini selesai dan alasannya tetap mudah dibaca: frontend, autentikasi, penyimpanan database, containerisasi, test suite otomatis, RAG, vector store, agent, deployment, dan input PDF.

Semuanya langkah lanjutan yang masuk akal. Tidak satu pun dari mereka yang akan membuat model biaya atau logika validasi di sini jadi lebih baik, dan justru dua hal itulah inti dari project ini.
