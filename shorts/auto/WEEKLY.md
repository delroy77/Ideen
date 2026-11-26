# Wöchentliche Compilation (für Claude)

Arbeitsordner `X:\Claude\shorts`. Läuft ohne Rückfragen. Ziel: lange Videos bringen Abos.

1. `py auto/shortqueue.py week` → veröffentlichte Shorts der letzten 7 Tage.
   Bei weniger als 3: abbrechen und das berichten.
2. `py auto/compile_week.py weekly/<JJJJ-MM-TT> <ordner1> <ordner2> ...` in Posting-Reihenfolge.
   Beste/stärkste Short zuerst ist auch ok.
3. 2 Frames prüfen: Short mittig, Creator-Name sichtbar, „SUBSCRIBE“-Hinweis rechts.
4. Hochladen über die Upload-Route aus `DAILY.md` (Release-Tag `tmp-weekly-<datum>`). Als **normales Video**, nicht als Short.
   - Titel, z. B. „Best Streamer Moments of the Week #N – Kai Cenat, Asmongold …“ (≤ 70 Zeichen).
   - Beschreibung: 1–2 Sätze, dann `chapters.txt` (Kapitel), Credits mit allen Quell-URLs aus den `meta.json`, dann „Subscribe for a new clip every day“.
   - Tags/Hashtags: alle Creator, die Spiele, #Compilation #Reaction.
5. Danach in jeder `meta.json` der verwendeten Shorts `compilation=<datum>` setzen (`py auto/shortqueue.py set <ordner> compilation=<datum>`).
6. **Trends auffrischen** (auch wenn die Compilation ausfällt): per Websuche (z. B. Twitch-/YouTube-Gaming-Charts der Woche) die 5–8 meistgestreamten bzw. viralsten Spiele bestimmen und `trending_games` in `auto/watchlist.json` ersetzen. `pinned_games` und `priority_games` NICHT ändern. Große englische Streamer (≥ 1 Mio. Abos), die diese Woche viral gingen und noch fehlen, in `channels` aufnehmen (Handle vorher mit `py -m yt_dlp --flat-playlist -I 1:1 --print title <url>` prüfen). Im Bericht nennen, was sich geändert hat.
