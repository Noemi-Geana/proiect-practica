import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from proiect.name_parser import (
    clean_title,
    extract_season_episode,
    extract_year,
    parse_movie,
    parse_music,
    parse_series,
)


def test_extract_year():
    assert extract_year("The.Matrix.1999.1080p.mkv") == 1999
    assert extract_year("fisier_fara_an.mkv") is None


def test_extract_season_episode_format_sxxexx():
    assert extract_season_episode("Breaking.Bad.S03E07.mkv") == (3, 7)


def test_extract_season_episode_format_numeric():
    assert extract_season_episode("show.4x02.mkv") == (4, 2)


def test_extract_season_episode_not_found():
    assert extract_season_episode("fisier_fara_tipar.mkv") is None


def test_clean_title_removes_noise():
    title = clean_title("The.Matrix.1999.1080p.BluRay.x264.mkv")
    assert "1080p" not in title.lower()
    assert "bluray" not in title.lower()
    assert "matrix" in title.lower()


def test_parse_movie():
    result = parse_movie("Inception.2010.720p.WEB-DL.mkv")
    assert result["year"] == 2010
    assert "inception" in result["title"].lower()


def test_parse_series():
    result = parse_series("Game.of.Thrones.S01E01.mkv")
    assert result["season"] == 1
    assert result["episode"] == 1


def test_parse_series_failure_case():
    result = parse_series("random_file_name.mkv")
    assert result["season"] is None
    assert result["episode"] is None


def test_parse_music_with_artist():
    result = parse_music("Coldplay - Yellow.mp3")
    assert result["artist"] == "Coldplay"
    assert result["track"] == "Yellow"


def test_parse_music_without_artist():
    result = parse_music("melodie_fara_artist.mp3")
    assert result["artist"] is None
    assert result["track"] == "Melodie Fara Artist"


def test_diacritics_preserved_in_title():
    result = clean_title("Amintiri.din.Copilărie.1080p.mkv")
    assert "ă" in result.lower()
    assert "copilărie" in result.lower()

    result2 = clean_title("Război.și.Pace.1966.720p.BluRay.mkv")
    assert "ă" in result2.lower()
    assert "ș" in result2.lower()


def test_diacritics_with_season_episode():
    result = parse_series("Lăsați-mă.să.Câștig.S02E05.mkv")
    assert result["season"] == 2
    assert result["episode"] == 5
    assert "ă" in result["title"].lower() or "â" in result["title"].lower()