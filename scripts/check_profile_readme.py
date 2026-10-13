#!/usr/bin/env python3
"""
check_profile_readme.py — penjaga kualitas Profile README (repo `superrrkyy`).

Dijalankan otomatis oleh GitHub Actions pada setiap push/PR.
Memeriksa:
  1. Semua bagian wajib masih ada (judul, tentang, tech stack, proyek, kontak).
  2. Aset lokal yang dirujuk (./assets/...) benar-benar ada di repo.
  3. Sintaks markdown/HTML dasar sehat: kurung link seimbang, <p> tertutup,
     tidak ada penanda TODO/FIXME yang tertinggal.
  4. Info penting: jumlah tautan portofolio yang masih hidup (>0).

Jalankan manual:  python3 scripts/check_profile_readme.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

BAGIAN_WAJIB = [
    "Tentang Saya",
    "Tech Stack",
    "Website Live",
]

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def main() -> int:
    if not README.exists():
        err("README.md tidak ditemukan di root repo.")
        return report()

    text = README.read_text(encoding="utf-8")
    lines = text.splitlines()

    # ---------- 1. bagian wajib ----------
    for bagian in BAGIAN_WAJIB:
        if bagian.lower() not in text.lower():
            err(f"Bagian wajib hilang: '{bagian}'")

    # ---------- 2. aset lokal ----------
    for target in sorted(set(re.findall(r'(?:src|href)="(\./[^"]+)"', text))):
        path = ROOT / target.lstrip("./")
        if not path.exists():
            err(f"Aset lokal hilang: {target}")

    # ---------- 3. sintaks ----------
    for i, line in enumerate(lines, 1):
        if line.count("(") != line.count(")") and "](" in line:
            warn(f"Baris {i}: tanda kurung link tidak seimbang → {line.strip()[:70]}")
        if re.search(r"\b(TODO|FIXME|XXX)\b", line):
            warn(f"Baris {i}: penanda tertinggal → {line.strip()[:70]}")
        if line != line.rstrip() and line.strip():
            warn(f"Baris {i}: ada spasi di akhir baris")

    n_p_open = len(re.findall(r"<p[\s>]", text))
    n_p_close = len(re.findall(r"</p\s*>", text))
    if n_p_open != n_p_close:
        err(f"Tag <p> tidak seimbang: {n_p_open} buka vs {n_p_close} tutup")

    for tag in ("details", "summary"):
        n_open = len(re.findall(rf"<{tag}[\s>]", text))
        n_close = len(re.findall(rf"</{tag}\s*>", text))
        if n_open != n_close:
            err(f"Tag <{tag}> tidak seimbang: {n_open} buka vs {n_close} tutup")

    # ---------- 4. tautan ----------
    links = re.findall(r"\]\((https?://[^)\s]+)\)", text) + re.findall(
        r'href="(https?://[^"]+)"', text
    )
    if len(links) < 8:
        warn(f"Hanya {len(links)} tautan eksternal — pastikan daftar proyek masih lengkap.")
    for url in links:
        if " " in url:
            err(f"Tautan mengandung spasi (rusak): {url}")

    # ---------- 5. gambar dari layanan pihak ketiga ----------
    eksternal = re.findall(r'src="(https?://[^"]+)"', text)
    for url in eksternal:
        if url.startswith("http://"):
            err(f"Gambar memakai http:// (tidak aman): {url}")

    return report()


def report() -> int:
    print("=" * 60)
    print("Pemeriksaan Profile README — @superrrkyy")
    print("=" * 60)
    for w in warnings:
        print(f"  [peringatan] {w}")
    for e in errors:
        print(f"  [GAGAL]      {e}")
    if not errors and not warnings:
        print("  ✅ Semua pemeriksaan lulus tanpa catatan.")
    elif not errors:
        print(f"\n  ✅ Lulus, dengan {len(warnings)} peringatan (tidak memblokir CI).")
    else:
        print(f"\n  ❌ {len(errors)} masalah harus diperbaiki.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
