# Täglicher Shorts-Lauf (für Claude)

Arbeitsordner `X:\Claude\shorts`. Läuft ohne Rückfragen durch. Wenn ein Schritt fehlschlägt: den Short auf `failed` setzen oder das Video überspringen und weitermachen. Am Ende kurz berichten.

Regeln: **1 Short pro Tag veröffentlichen**, **höchstens 3 neue pro Tag erstellen**, Puffer = 3 fertige Shorts.
Freigabe ist automatisch (sofort öffentlich).

## 1. Posten (zuerst, geht schnell)
`py auto/shortqueue.py status`, dann **YouTube prüfen**, denn manche Shorts werden von Hand geplant.
In der Composio-Workbench:

```python
r,_=proxy_execute("GET","/channels","youtube",query_params={"part":"contentDetails","mine":"true"})
up=r["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
r,_=proxy_execute("GET","/playlistItems","youtube",query_params={"part":"contentDetails","playlistId":up,"maxResults":"10"})
ids=",".join(i["contentDetails"]["videoId"] for i in r["items"])
r,_=proxy_execute("GET","/videos","youtube",query_params={"part":"snippet,status","id":ids})
for v in r["items"]: print(v["id"],v["status"]["privacyStatus"],v["status"].get("publishAt"),v["snippet"]["publishedAt"],v["snippet"]["title"])
```

Der Tag ist **belegt**, wenn ein Video heute (Ortszeit Europe/Berlin) öffentlich wurde oder per `publishAt` für heute geplant ist.
Für so ein Video ohne `meta.json`-Eintrag wird dieser nachgetragen, falls der Ordner bekannt ist.
- Wenn der Tag nicht belegt ist, `posted_today` false ist und `due` nicht leer ist: den **ersten** Short aus `due` hochladen (Shorts mit festem `publish_on` kommen an ihrem Tag dran, sonst der älteste) (Route siehe unten).
  Danach `py auto/shortqueue.py set <ordner> status=posted youtube_id=<id>`.

## 2. Puffer auffüllen
Neue Shorts erstellen, solange `ready` < 3 und `made_today` < 3:

1. `py auto/find_videos.py` → `auto/candidates.json`, die besten zuerst (dauert ~5 min, einmal pro Lauf reicht). Videos mit `age_limit` 18 nur nehmen, wenn Firefox geschlossen ist.
2. `py auto/shortqueue.py new <id> <url> "<creator>" <hashtag>` → neuer Ordner `NNN`.
3. `py auto/prepare.py <ordner> <url>` → `src/captions.txt` und `src/heatmap.txt` lesen.
   Keine Untertitel → `py auto/shortqueue.py skip <id>`, Ordner löschen, nächstes Video.
4. Ist heute ein Eintrag aus `priority_games` in `watchlist.json` aktiv (`from` bis `until`), haben Videos zu diesem Spiel klar Vorrang: zuerst die nehmen, nur wenn keins taugt, andere.
   1 Story für einen 20–50-s-Short wählen: ein Moment mit Aufbau und Pointe (lustig, Wut, Schock, starke Meinung).
   Heatmap-Spitzen haben Vorrang. Je 3–8 Fenster mit ~2 s Puffer.
   Taugt nichts → `skip`, Ordner löschen, nächstes Video.
5. `py auto/cut.py <ordner> <url> a-b c-d ...` (Sekunden im Quellvideo).
6. `src/seg_*.jpg` ansehen und in `short.json` folgende Felder setzen:
   - `layout.facecam` und `layout.game` als [x, y, b, h] im 1920×1080-Bild. Ohne Facecam: `"layout": "full"` mit `center_x` oder `"fit"` pro Clip.
   - Clips auf die Sätze trimmen (Wortzeiten in `seg_*.words.json`).
   - `title` als Hook in GROSSBUCHSTABEN, mit `\\N` für den Umbruch.
   - `fixes` für falsch erkannte Namen.
   - `creator` steht schon drin. Der Name wird 5 s eingeblendet, bei jedem Creator-Wechsel erneut.
   - **Nur bei Path of Exile (1 oder 2):** `py auto/build_info.py <ordner>` liest den PoB-Link aus der Videobeschreibung (pobb.in, maxroll, pastebin) und schreibt `build.json`.
     Hat das geklappt, kommt `overlay` als `info` in `short.json`. Das ist eine gelbe Box ab Sekunde 5 für 6 s, z. B. „JUGGERNAUT · STATIC STRIKE / 8.4M DPS · 5.8K LIFE“.
     Prüfen, ob `skill` zum Video passt. PoB merkt sich manchmal die falsche Hauptgruppe; dann den Text von Hand korrigieren.
     Steht kein Link in der Beschreibung, aber einer ist im Video zu sehen, kann er als 2. Argument mitgegeben werden. Ohne Build gibt es keine Box (Exit-Code 1 ist dann okay).
     Für Details zum Build (z. B. „der Trick dabei“) kann der MCP-Server `poe2-optimizer` Gems und Mechaniken erklären, aber nur für PoE 2.
7. `py make_short.py <ordner>`, dann 2–3 Frames aus `short.mp4` prüfen: Facecam- und Game-Crop, Untertitel, Titel, Creator-Name.
8. Diese Felder in `meta.json` setzen (`shortqueue.py set` oder direkt editieren):
   - `yt_title` (≤ 70 Zeichen, Englisch, mit Hook).
   - `description`: 1–2 Sätze, dazu `Source: <source_url>` und `Credit: <creator>`. Wenn es eine `build.json` gibt, außerdem `Build: <source>`.
   - `tags`: immer #<hashtag> #<Spiel> #Reaction, dazu #Shorts.
   - `status=ready`.

## Upload-Route (Shorts und Compilation)
1. `gh release create tmp-short-NNN <mp4> --repo delroy77/Ideen --prerelease --title tmp --notes tmp`
2. Composio-Workbench: Asset herunterladen, `upload_local_file` → s3key. **Sofort** `gh release delete tmp-short-NNN --repo delroy77/Ideen --yes --cleanup-tag`.
3. `YOUTUBE_MULTIPART_UPLOAD_VIDEO` (Account `youtube_podley-divine` = Kanal **Delroy**, nicht „Mein Kanal“). Kategorie 20, `privacyStatus` public.
   Den Titel nehmen. Die Beschreibung bekommt die Hashtags am Ende. **Nicht** `YOUTUBE_UPLOAD_VIDEO` verwenden.
4. Danach `uploadStatus` prüfen (`processed`).
