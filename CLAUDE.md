# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Premier League standings TUI app built with Textual. Displays league table and team match schedules using the football-data.org API.

## Commands

```bash
# Activate virtual environment first
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app (requires FOOTBALL_API_KEY env var)
python standings.py

# Build standalone executable
pyinstaller --onefile --name standings standings.py
# Output: dist/football
```

## Architecture

**standings.py** - Single-file application containing:

- **Data models**: `Team`, `Standing`, `Match`, `Score`, `ScoreSnapshot` - dataclasses with JSON deserialization via `dataclasses-json`
- **API functions**: `get_standings()`, `get_matches(team)` - cached requests to football-data.org
- **UI components**:
  - `StandingsTable` - League table DataTable
  - `MatchesTable` - Team fixtures (2 rows per match: home/away teams)
  - `MatchesScreen` - Screen with match filters (unplayed/played/all)
  - `StandingsApp` - Main app, uses screen stack for navigation

**Navigation pattern**: Push `MatchesScreen` onto stack when selecting a team, pop to return. Keybindings include vim-style j/k navigation.
