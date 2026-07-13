# Structură prezentare – Metode de recuperare a datelor șterse (Data Carving, Metadata Search)

## 1. Slide de titlu

## 2. Cuprins 

## 3. Introducere – De ce recuperare de date?
- pierdere accidentală de date, ștergere intenționată, defecțiuni hardware, atacuri
- Importanța recuperării datelor în criminalistică digitală
- Exemple de scenarii reale (recuperare fișiere după formatare, investigații IT, incidente de securitate)

## 4. Ce înseamnă „ștergerea” unui fișier?
- Diferența dintre ștergerea logică și ștergerea fizică a datelor
- De ce datele rămân fizic pe disc până sunt suprascrise

## 5. Sisteme de fișiere – noțiuni de bază
- Structura unui sistem de fișiere (superblock, inode/MFT, tabelă de alocare)
- Cum sunt organizate metadatele vs. conținutul efectiv al fișierelor
- Diferențe relevante între FAT32, NTFS, ext4 pentru recuperare

## 6. Clasificarea metodelor de recuperare a datelor
- Recuperare bazată pe metadate (metadata-based recovery)
- Recuperare bazată pe conținut / semnătură (data carving)
- Recuperare hibridă (combinație a celor două)

## 7. Metadata Search 
- Definiție: recuperare folosind informațiile rămase în structurile de sistem de fișiere (inode, tabele de alocare)
- Avantaje: recuperare rapidă, păstrează numele fișierului, structura de foldere, timestamp-uri
- Limitări: nu funcționează dacă metadatele au fost suprascrise sau sistemul de fișiere e corupt

## 8. Metadata Search – funcționalitate
- Pași: identificarea intrărilor „șterse” dar încă prezente în tabela de metadate
- Refacerea legăturii dintre metadate și blocurile de date corespunzătoare

## 9. Data Carving
- Definiție: recuperarea fișierelor pe baza semnăturilor de fișier (magic numbers / header-footer), fără a folosi metadate
- Se folosește atunci când metadatele sunt pierdute, corupte sau sistemul de fișiere e necunoscut
- Avantaje: funcționează chiar și pe disc formatat sau spațiu neasociat

## 10. Data Carving – funcționalitate
- Scanarea brută a discului căutând semnături cunoscute (ex. `FFD8FF` pentru JPEG, `%PDF` pentru PDF)
- Identificarea header-ului și footer-ului fișierului
- Extragerea blocului de date dintre cele două

## 11. Comparație Metadata Search vs. Data Carving
- Tabel comparativ: viteză, acuratețe, păstrare nume/structură, dependență de sistemul de fișiere, rezistență la fragmentare
- Când se folosește fiecare metodă în practică

## 12. Probleme comune în recuperarea datelor
- Fragmentarea fișierelor
- Suprascrierea parțială/completă a datelor
- Criptarea discului ca obstacol
- SSD-uri și comanda TRIM – de ce recuperarea e mult mai dificilă pe SSD față de HDD

## 13. Tehnologii folosite
- Instrumente populare: `PhotoRec`, `TestDisk`, `Autopsy`, `Foremost`, `Scalpel`, `Bulk Extractor`+ scurtă descriere a fiecăruia și pentru ce tip de recuperare e potrivit

## 14. Demonstrație practică + Rezultate obținute (ce fișiere au fost recuperate cu succes)
- Screenshot-uri sau output relevant din terminal
- Ce fișiere au fost recuperate cu succes (tip, câte, integritate)
- Diferențe observate între cele două metode aplicate pe același set de date
- Limitări întâlnite în practică

## 15. Aplicabilitate în domeniul criminalisticii digitale (opțional, dacă se leagă de proiect)
- Rolul acestor metode în investigații (recuperare probe digitale)
- Considerații legale/etice (lanțul de custodie, integritatea probelor)

## 16. Concluzii

## 17. Bibliografie