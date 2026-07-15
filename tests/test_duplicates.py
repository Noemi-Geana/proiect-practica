"""Teste pentru organizer.duplicates"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from proiect.duplicates import DuplicateDetector


def test_compute_hash_consistency(tmp_path):
    f = tmp_path / "fisier.txt"
    f.write_text("continut identic")
    hash1 = DuplicateDetector.compute_hash(str(f))
    hash2 = DuplicateDetector.compute_hash(str(f))
    assert hash1 == hash2


def test_find_duplicate_detects_identical_content(tmp_path):
    f1 = tmp_path / "original.txt"
    f2 = tmp_path / "copie.txt"
    f1.write_text("continut identic pentru test")
    f2.write_text("continut identic pentru test")

    detector = DuplicateDetector(None)
    assert detector.find_duplicate(str(f1)) is None
    result = detector.find_duplicate(str(f2))
    assert result == str(f1)


def test_find_duplicate_different_content(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("continut A")
    f2.write_text("continut complet diferit B")

    detector = DuplicateDetector(None)
    detector.find_duplicate(str(f1))
    assert detector.find_duplicate(str(f2)) is None


def test_build_index_from_directory(tmp_path):
    media_dir = tmp_path / "Media"
    media_dir.mkdir()
    (media_dir / "existent.txt").write_text("continut existent")

    detector = DuplicateDetector(None)
    detector.build_index(str(media_dir))

    new_file = tmp_path / "nou.txt"
    new_file.write_text("continut existent")

    result = detector.find_duplicate(str(new_file))
    assert result is not None
    assert "existent.txt" in result
