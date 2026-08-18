from pathlib import Path

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
