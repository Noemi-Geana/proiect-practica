import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from proiect.classifier import FileCategory, FileClassifier
from proiect.config_loader import Config


@pytest.fixture
def classifier(tmp_path):
    config_content = """
paths:
  downloads: "{tmp}/Downloads"
  media_root: "{tmp}/Media"
  documents: "{tmp}/Media/Documents"
  executables: "{tmp}/Media/Executables"
  pictures: "{tmp}/Media/Pictures"
  duplicates: "{tmp}/Media/Duplicates"
  unsorted: "{tmp}/Media/Unsorted"
subfolders:
  movies: "Movies"
  series: "Series"
  music: "Music"
extensions:
  video: [".mp4", ".mkv"]
  audio: [".mp3"]
  documents: [".pdf", ".txt"]
  executables: [".sh"]
  archives: [".zip"]
  subtitles: [".srt"]
  pictures: [".jpg"]
  incomplete: [".part", ".crdownload"]
api:
  omdb_key: "test"
  omdb_url: "http://test"
logging:
  log_file: "{tmp}/test.log"
history:
  history_file: "{tmp}/history.json"
behavior:
  dry_run: true
""".format(tmp=tmp_path)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    config = Config(str(config_path))
    return FileClassifier(config)


def test_classify_video_by_extension(classifier, tmp_path):
    f = tmp_path / "film.mp4"
    f.write_text("continut")
    assert classifier.classify(str(f)) == FileCategory.VIDEO


def test_classify_document_by_extension(classifier, tmp_path):
    f = tmp_path / "document.pdf"
    f.write_text("continut")
    assert classifier.classify(str(f)) == FileCategory.DOCUMENT


def test_classify_incomplete_file(classifier, tmp_path):
    f = tmp_path / "download.crdownload"
    f.write_text("")
    assert classifier.classify(str(f)) == FileCategory.INCOMPLETE


def test_classify_unknown_extension(classifier, tmp_path):
    f = tmp_path / "fisier_ciudat.xyz123"
    f.write_text("continut necunoscut")
    result = classifier.classify(str(f))
    assert result in (FileCategory.UNKNOWN, FileCategory.DOCUMENT)