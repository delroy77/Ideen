# Shorts-Generator

## Konzept
Aus langen Videos (z. B. Livestreams) automatisch Shorts erstellen: die besten Szenen finden, auf 9:16 schneiden und mit Wort-für-Wort-Untertiteln versehen.

## Zielsetzung
Mit wenig Handarbeit regelmäßig Shorts produzieren (YouTube Shorts, TikTok, Reels).

## Funktionsideen
- Highlights über YouTube-Heatmap („Meistgesehen“) oder das Transkript finden
- Nur die benötigten Ausschnitte herunterladen (`yt-dlp --download-sections`)
- Layout: Facecam oben + Gameplay unten, oder Vollbild-Crop
- Untertitel in **Originalsprache**, aktuelles Wort hervorgehoben, Flüche zensiert
- Titel-Einblendung am Anfang (Hook)

## Technische Überlegungen
- Tools: `ffmpeg`, `yt-dlp`, `faster-whisper` (Modell `small`, CPU)
- `transcribe.py <video> <out.json> start-end ...` → Wort-Zeitstempel für Ausschnitte
- `make_short.py <ordner>` → rendert `short.mp4` aus `<ordner>/short.json`
- `short.json`: Quellen, Clips (start/end, optional `"layout": "full"` + `center_x`), Crop-Bereiche, Titel, Wort-Korrekturen
- Videos und Downloads landen in `<ordner>/src/` und werden nicht committet

## Prototypen
- `001/` – Kai Cenat „BEATING GTA 6 *FINALE*“ → 46-s-Short „He got the worst GTA 6 ending“

## Notizen / offene Punkte
- Highlight-Auswahl ist noch halb manuell (Score aus Transkript + Auswahl durch Claude)
- Facecam-Position ist pro Stream anders → aktuell von Hand in `short.json`
- Ton wird nicht gepiept, nur die Untertitel zensiert
- Rechte: fremde Streams können Copyright-Claims auslösen

## Status
- [x] Idee gesammelt
- [x] Konzept ausgearbeitet
- [ ] Erste Bewertung
- [x] Prototyp
- [ ] Bereit für eigenes Repository
