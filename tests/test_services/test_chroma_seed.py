from pathlib import Path

import pytest

import src.services.chroma_seed as chroma_seed
from src.services.chroma_seed import ensure_seeded


def test_chep_khi_thu_muc_dich_rong(tmp_path: Path):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "chroma.sqlite3").write_bytes("giả".encode())
    target = tmp_path / "chroma"

    assert ensure_seeded(str(target), str(seed)) is True
    assert (target / "chroma.sqlite3").read_bytes() == "giả".encode()


def test_khong_de_len_du_lieu_da_co(tmp_path: Path):
    """Chép đè lên volume đang có dữ liệu sẽ XOÁ tài liệu BQL vừa nạp."""
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "chroma.sqlite3").write_bytes("giống".encode())
    target = tmp_path / "chroma"
    target.mkdir()
    (target / "chroma.sqlite3").write_bytes("thật".encode())

    assert ensure_seeded(str(target), str(seed)) is False
    assert (target / "chroma.sqlite3").read_bytes() == "thật".encode()


def test_khong_co_seed_thi_khong_no(tmp_path: Path):
    assert ensure_seeded(str(tmp_path / "chroma"), str(tmp_path / "khong-ton-tai")) is False


def test_chep_dang_do_thi_don_sach_va_nem_loi(tmp_path: Path, monkeypatch):
    """Chép dở dang (hết đĩa, lỗi quyền, container bị kill) không được để lại
    thư mục nửa vời trông giống "đã seed" — nếu không, lần khởi động sau sẽ
    coi mảnh vỡ đó là dữ liệu thật và không bao giờ thử lại."""
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "chroma.sqlite3").write_bytes("giả".encode())
    target = tmp_path / "chroma"

    def raise_copytree(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(chroma_seed.shutil, "copytree", raise_copytree)

    with pytest.raises(OSError):
        ensure_seeded(str(target), str(seed))

    assert not target.exists() or not any(target.iterdir())
