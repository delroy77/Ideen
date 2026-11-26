# Craft Anything

Quelle: <https://github.com/storytold/craft-anything> (Stand: 26.11.2026, early alpha, MIT/Apache-2.0)

## Konzept
Open-Source-Werkzeug in Rust (Desktop-App, CLI, MCP-Server, Web/WASM), das eine Website, App oder ein
Spiel untersucht und dann von einem Coding-Agenten (z. B. Claude Code) eine **eigene Version** bauen lässt.
Ablauf: **Study → Build → Check → Ready** – das Ergebnis wird gegen das Original geprüft und verfeinert.

- **Clean room** (Standard): arbeitet nur mit dem, was sichtbar ist (Screenshots, Layout, Farben, Fonts).
- **Deep**: liest auch Code/Dateien (eigene Engines, optional Ghidra) – nur für private Nutzung.
- Spiele-Rebuilds in Unity, Unreal oder Godot; optional Bilder/3D-Modelle über eigenen fal.ai-Key.

## Zielsetzung
Prüfen, ob Craft Anything für eigene Projekte nützlich ist – v. a. um schnell Prototypen von
Websites/Tools zu bauen, deren Aufbau man als Vorlage nimmt, ohne fremde Inhalte zu kopieren.

## Funktionsideen
- Landingpage / Übersichtsseite für den Shorts-Kanal (`shorts/`) nach dem Vorbild bestehender Seiten bauen lassen
- UI-Ideen für **Delroys Suite** (`DelroysSuite/`) aus Screenshots eigener Mockups ableiten
- MCP-Server in Claude Code einbinden, um Websites gezielt zu analysieren („Just look inside“)
- Testen, wie gut der „Check“-Schritt Unterschiede zum Original erkennt

## Technische Überlegungen
- Installer für Windows/macOS/Linux/FreeBSD auf der Releases-Seite; Builder ist standardmäßig Claude Code
- Dependency-Installationen (npm, cargo …) führen Code aus – nur bei vertrauenswürdigen Projekten „immer erlauben“
- **Verantwortungsvoll nutzen:** nur Software, die man besitzt oder untersuchen darf; keine Logos/Texte/Bilder
  Dritter übernehmen; umgeht kein DRM, Logins oder Anti-Cheat (wichtig bei Spielen wie WoW/PoE)

## Mockups / Diagramme
- Screenshots im Original-README: `docs/images/project-website.png`

## Prototypen
- noch keine

## Notizen / offene Punkte
- Status laut Projekt: „early alpha“; API-Key-Builder und andere Agenten noch nicht live getestet
- Erst mit einem kleinen, eigenen Website-Projekt ausprobieren
- Doku zum Weiterlesen: `docs/STATUS.md`, `docs/ROADMAP.md`, `docs/claude-code.md`

## Status
- [x] Idee gesammelt
- [ ] Konzept ausgearbeitet
- [ ] Erste Bewertung
- [ ] Prototyp
- [ ] Bereit für eigenes Repository
