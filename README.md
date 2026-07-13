# proiect-practica

# Cerințe proiect – Aplicație/Script gestiune Download-uri

## Structură de bază
Proiectul va organiza fișierele în următoarele directoare:
- `Downloads/`
- `Movies/`
- `Series/`
- `Music/`
- `Documents/`
- `Executables/`

## 1. Detectare și clasificare fișiere

- Detectarea tipului de fișier după conținut (magic bytes / `python-magic`), nu doar după extensie
- Ignorarea fișierelor incomplete (`.part`, `.crdownload`, `.tmp`) până se termină descărcarea
- Detectare fișiere duplicate prin hash (MD5/SHA256) – ștergere automată sau mutare în `Duplicates/`
- Suport pentru arhive (`.zip`, `.rar`, `.7z`) – extragere automată înainte de clasificare
- Listă de extensii configurabilă pentru fiecare categorie (documente, executabile, imagini, subtitrări etc.)
- Categorie suplimentară pentru subtitrări (`.srt`, `.sub`) – asociere automată cu fișierul video corespunzător
- Categorie pentru imagini/poze descărcate separat (`Pictures/`)

## 2. Metadate și API

- Cache local pentru metadate (SQLite sau fișier JSON) ca să nu se interogheze API-ul de mai multe ori pentru același titlu
- Fallback pe mai multe API-uri (OMDb, TMDb, TVDB) dacă primul nu găsește rezultatul
- Descărcare poster/copertă (`poster.jpg`) lângă fișierul media
- Gestionarea erorilor de API (rate limit, lipsă conexiune, titlu negăsit) fără oprirea scriptului
- Cheie API stocată în fișier de configurare separat, nu hardcodată în cod

## 3. Parsare nume fișiere

- Regex robust pentru identificarea sezon/episod (`S01E02`, `1x02`, `Season 1 Episode 2` etc.)
- Extragere an apariție din numele fișierului (ex. `Film.2023.1080p`)
- Tratarea cazului în care parsarea eșuează – mutare în `Unsorted/` sau `NeedsReview/` în loc de crash
- Suport pentru nume în format diferit (română/engleză, diacritice)

## 4. Logging, monitorizare și notificări

- Logging complet într-un fișier (`.log`), cu timestamp, acțiune, sursă, destinație, erori
- Nivele de logging (INFO, WARNING, ERROR)
- Mod „dry-run” – simulează organizarea fără să mute efectiv fișierele (util pentru testare/demo)
- Notificări desktop pe Linux (`notify-send`) la finalizarea organizării sau la erori
- Raport de sumar după fiecare rulare (câte fișiere mutate, câte erori, cât spațiu ocupat)

## 5. Automatizare și rulare continuă

- Watcher pe folderul `Downloads` folosind librăria `watchdog` – organizare automată la fiecare fișier nou
- Rulare ca serviciu `systemd` pe Linux, pornire automată la boot
- Programare periodică cu `cron` ca alternativă la watcher

## 6. Interfață și interacțiune cu utilizatorul

- CLI cu argumente (`argparse` sau `click`)
- Interfață grafică simplăbpentru a organiza manual fișierele
- Interfață web minimală (Flask/FastAPI) pentru monitorizare status și istoricul organizării
- Progress bar pentru fișiere mari, folosind
- Confirmare manuală opțională înainte de mutare (mod interactiv)

## 8. Funcționalități

- Suport pentru mai multe locații de bibliotecă media (ex. discuri diferite pentru filme/seriale)
- Statistici globale: total fișiere organizate, spațiu ocupat pe categorie, cele mai recente adăugări
- Curățare automată a folderelor goale rămase după mutare
- Reguli configurabile de redenumire (template-uri, ex: `{titlu} ({an})`)
- Detectare coliziuni de nume (dacă există deja un fișier cu același nume în destinație) și redenumire automată
- Suport multi-limbă pentru metadate (română/engleză)
- Undo / istoric acțiuni – posibilitatea de a anula ultima organizare

## 9. Securitate și robustețe

- Validarea căilor de fișiere pentru a evita path traversal sau mutări în afara folderelor definite
- Limitarea numărului de cereri către API pentru a evita blocarea cheii
- Backup/verificare integritate fișier după mutare (comparare hash înainte/după)
