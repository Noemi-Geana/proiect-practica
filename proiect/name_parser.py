import re

# Cuvinte tehnice din nume care trebuie eliminate (rezoluție, codec, quality, etc)
_NOISE_TOKENS = [
    r"1080p", r"720p", r"2160p", r"480p", r"4k",
    r"x264", r"x265", r"h264", r"h265", r"hevc",
    r"web-?dl", r"webrip", r"bluray", r"brrip", r"dvdrip", r"hdtv",
    r"yify", r"yts(\.mx)?", r"rarbg", r"eztv",
    r"aac", r"ac3", r"dts", r"5\.1",
    r"multi", r"subs?", r"dublat", r"romana",
]
_NOISE_PATTERN = re.compile(r"(?i)\b(" + "|".join(_NOISE_TOKENS) + r")\b")

# Extrage ani: 1920-2099
_YEAR_PATTERN = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")

# Extrage sezon și episod: S01E02, s1e2, 1x02, Season 1 Episode 2
_SEASON_EPISODE_PATTERNS = [
    re.compile(r"(?i)s(\d{1,2})e(\d{1,3})"),
    re.compile(r"(?i)(\d{1,2})x(\d{1,3})"),
    re.compile(r"(?i)season\s*(\d{1,2})\s*episode\s*(\d{1,3})"),
]


def extract_year(filename: str) -> int | None:
    # Caută anul în format YYYY (1900-2099)
    match = _YEAR_PATTERN.search(filename)
    return int(match.group(1)) if match else None


def extract_season_episode(filename: str) -> tuple[int, int] | None:
    # Caută sezon și episod în orice format
    for pattern in _SEASON_EPISODE_PATTERNS:
        match = pattern.search(filename)
        if match:
            season, episode = int(match.group(1)), int(match.group(2))
            return season, episode
    return None


def clean_title(filename: str) -> str:
    # Curață titlul: scoate extensie, zgomot, numere, caractere speciale
    
    name = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", filename)  # Scoate .mkv, .mp4, etc
    
    # Scoate marcajele de sezon/episod
    for pattern in _SEASON_EPISODE_PATTERNS:
        name = pattern.sub(" ", name)
    
    # Scoate anul
    name = _YEAR_PATTERN.sub(" ", name)
    
    # Scoate cuvintele tehnice
    name = _NOISE_PATTERN.sub(" ", name)
    
    # Înlocuiește puncte/underscore cu spații și normalizează
    name = re.sub(r"[._]+", " ", name)
    name = re.sub(r"[\[\](){}]", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -_")
    
    return name.title() if name else "Unknown"


def parse_movie(filename: str) -> dict:
    # Extrage titlu și an din nume film
    return {
        "title": clean_title(filename),
        "year": extract_year(filename),
    }


def parse_series(filename: str) -> dict:
    # Extrage titlu, sezon și episod din nume serial
    se = extract_season_episode(filename)
    return {
        "title": clean_title(filename),
        "season": se[0] if se else None,
        "episode": se[1] if se else None,
    }


def _normalize_spacing(text: str) -> str:
    # Înlocuiește puncte/underscore cu spații, apoi normalizează
    text = re.sub(r"[._]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_music(filename: str) -> dict:
    # Extrage artist și cântec din nume (format: Artist - Song.mp3)
    
    name = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", filename)  # Scoate extensie
    name = _normalize_spacing(name)
    
    # Împarte după '-': artist din stânga, cântec din dreapta
    parts = re.split(r"\s*-\s*", name, maxsplit=1)
    
    if len(parts) == 2:
        artist, track = parts
        return {"artist": artist.strip().title(), "track": track.strip().title()}
    
    # Nu e format Artist - Song: consideră tot ca titlu cântec
    return {"artist": None, "track": name.strip().title()}