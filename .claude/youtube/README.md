# YouTube Agent Skills

Installiert aus https://github.com/jakeschincariol/youtube-agent-skill (MIT, siehe `../skills/YT-SKILLS-LICENSE`).

Die Skills liegen in `.claude/skills/yt-*` und werden in jeder Claude-Code-Session in diesem Repo automatisch geladen:
`/yt-script`, `/yt-package`, `/yt-edit`, `/yt-comment`, `/yt-plan`, `/yt-viral`, `/yt-retention`, `/yt-shorts`, `/yt-seo`, `/yt-chapters`, `/yt-audit`.

`voice.md` hier ausfüllen (eigene Stimme/Stil). Die Skills lesen `~/.claude/youtube/voice.md` –
in Cloud-Sessions diese Datei als Quelle verwenden bzw. vorher dorthin kopieren:
`mkdir -p ~/.claude/youtube && cp .claude/youtube/voice.md ~/.claude/youtube/`

## YouTube-Verbindung über Composio (eigene Google-App)

- Cloud-Umgebung: **„Ideen“** verwenden. Dort ist der Composio-Projekt-API-Key als Netzwerk-Secret für
  `backend.composio.dev` hinterlegt (Header `x-api-key`, wird vom Proxy eingesetzt – nie im Code/Chat).
- Composio-Projekt: `yt_automation`, Auth Config `ac_5tirSr_PSNwM` (eigene Google-OAuth-App „yt-automation“,
  Status „In Produktion“, ungeprüft → Uploads zunächst privat).
- Composio-User-ID: `delroy`, Kanal „Delroy“ (`UCL98n_R7IDSZcWbBeBNUc7A`).
- Nicht den claude.ai-Composio-Connector („For You“) für YouTube nutzen – der verwendet die geteilte Composio-App
  mit oft erschöpftem Kontingent.

Session anlegen und Tool ausführen (REST v3.1):

```bash
B=https://backend.composio.dev/api/v3.1
SID=$(curl -s -X POST $B/tool_router/session -H "x-api-key: proxy-injected" -H "Content-Type: application/json" \
  -d '{"user_id":"delroy","toolkits":{"enable":["youtube"]},"auth_configs":{"youtube":"ac_5tirSr_PSNwM"}}' | jq -r .session_id)
curl -s -X POST $B/tool_router/session/$SID/execute -H "x-api-key: proxy-injected" -H "Content-Type: application/json" \
  -d '{"tool_slug":"YOUTUBE_LIST_CHANNELS","arguments":{"mine":true}}'
```

Vor jedem Upload: Titel/Beschreibung/Sichtbarkeit mit dem Nutzer bestätigen.

## Automatische Shorts: `/yt-autoshort`

Thema rein, fertiger Short raus: Skript (Hook geprüft) → Edge-TTS-Stimme → Pixabay-Clips → Untertitel
Wort für Wort → Qualitätsprüfung → Upload über Composio. Kostenlos.

- Stilvorlage: `.claude/skills/yt-autoshort/style.json` (Sprache, Stimme, Länge, Untertitel-Look, Upload).
- Braucht die Umgebung „Ideen“ und dort die Umgebungsvariable `PIXABAY_API_KEY`.
- Pro Session einmal: `pip install -q edge-tts`.
