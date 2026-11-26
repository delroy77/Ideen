# YouTube Agent Skills

Installiert aus https://github.com/jakeschincariol/youtube-agent-skill (MIT, siehe `../skills/YT-SKILLS-LICENSE`).

Die Skills liegen in `.claude/skills/yt-*` und werden in jeder Claude-Code-Session in diesem Repo automatisch geladen:
`/yt-script`, `/yt-package`, `/yt-edit`, `/yt-comment`, `/yt-plan`, `/yt-viral`, `/yt-retention`, `/yt-shorts`, `/yt-seo`, `/yt-chapters`, `/yt-audit`.

`voice.md` hier ausfüllen (eigene Stimme/Stil). Die Skills lesen `~/.claude/youtube/voice.md` –
in Cloud-Sessions diese Datei als Quelle verwenden bzw. vorher dorthin kopieren:
`mkdir -p ~/.claude/youtube && cp .claude/youtube/voice.md ~/.claude/youtube/`
