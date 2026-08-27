from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    nama: str = Field(description="Nama item apa adanya seperti tercetak di struk")
    qty: float = Field(description="Jumlah item, boleh desimal untuk barang timbangan")
    harga_satuan: int | None = Field(
        default=None,
        description="Harga per satuan kalau tercetak terpisah, kalau tidak ada isi null",
    )
    harga_total: int = Field(description="Nilai rupiah yang tercetak di ujung kanan baris item")


class Receipt(BaseModel):
    merchant: str | None = Field(
        default=None, description="Nama toko atau restoran, null kalau tidak terbaca"
    )
    tanggal: str | None = Field(
        default=None, description="Tanggal transaksi, format YYYY-MM-DD, null kalau tidak terbaca"
    )
    items: list[ReceiptItem] = Field(
        default_factory=list, description="Semua baris item yang dibeli"
    )
    subtotal: int | None = Field(
        default=None, description="Subtotal sebelum pajak, null kalau tidak tercetak"
    )
    pajak: int | None = Field(
        default=None, description="Nilai pajak atau PPN, null kalau struk tidak punya baris pajak"
    )
    total: int | None = Field(
        default=None, description="Total akhir yang dibayar, null kalau tidak terbaca"
    )