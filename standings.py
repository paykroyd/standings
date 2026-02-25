import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache

import requests
from dataclasses_json import LetterCase, dataclass_json
from rich.text import Text
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer

API_KEY = os.environ.get("FOOTBALL_API_KEY")
BASE_URL = "http://api.football-data.org/v4"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass(frozen=True)
class Team:
    id: str
    name: str
    short_name: str
    tla: str
    crest: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Standing:
    position: int
    team: Team
    played_games: int
    form: str
    won: int
    draw: int
    lost: int
    points: int
    goals_for: int
    goals_against: int
    goal_difference: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ScoreSnapshot:
    home: int
    away: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Score:
    winner: str
    full_time: ScoreSnapshot

    @property
    def home(self):
        return self.full_time.home

    @property
    def away(self):
        return self.full_time.away


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Match:
    id: str
    utc_date: str
    home_team: Team
    away_team: Team
    status: str
    matchday: int
    score: Score

    @property
    def date(self) -> date:
        dt_object = datetime.fromisoformat(self.utc_date.replace("Z", "+00:00"))
        return dt_object.date()

    @property
    def finished(self) -> bool:
        return self.status == "FINISHED"

    @property
    def winner(self) -> Team | None:
        if self.score.home > self.score.away:
            return self.home_team
        elif self.score.home == self.score.away:
            return None
        else:
            return self.away_team


def get_standings() -> list[Standing]:
    url = BASE_URL + "/competitions/PL/standings"
    headers = {"X-Auth-Token": API_KEY}
    params = {"season": "2025"}

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()

    standings = resp.json()["standings"]
    table = [Standing.from_json(json.dumps(row)) for row in standings[0]["table"]]

    return table


@cache
def get_matches(team: Team):
    url = BASE_URL + f"/teams/{team.id}/matches/"

    headers = {"X-Auth-Token": API_KEY}
    params = {"season": "2025", "competitions": "PL"}

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    matches = resp.json()["matches"]
    return [Match.from_json(json.dumps(m)) for m in matches]


DataTable.BINDINGS = DataTable.BINDINGS + [
    ("j", "cursor_down", "Move cursor down"),
    ("k", "cursor_up", "Move cursor up"),
    ("ctrl+d", "page_down", "Move cursor down a page"),
    ("ctrl+u", "page_up", "Move cursor up a page"),
]


class StandingsTable(DataTable):
    ROWS = ["Pos", "Club", "GP", "W", "D", "L", "GF", "GA", "GD", "PTS"]

    def __init__(self):
        super().__init__()
        self.standings = []
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns(*StandingsTable.ROWS)

    def update_data(self, standings: list[Standing]) -> None:
        self.standings = standings
        self.clear()
        for team in self.standings:
            self.add_row(
                str(team.position),
                team.team.short_name,
                str(team.played_games),
                str(team.won),
                str(team.draw),
                str(team.lost),
                str(team.goals_for),
                str(team.goals_against),
                str(team.goal_difference),
                str(team.points),
            )


class MatchesTable(DataTable):
    def __init__(self, team: Team | None = None):
        super().__init__()
        self.team = team
        self.matches = []
        self.cursor_type = "row"
        self.zebra_stripes = True

        cols = ["Match Day", "Date", "Match", "Score"]
        if self.team:
            cols.insert(2, "Result")
        self.add_columns(*cols)

    def update_data(self, matches: list[Match]) -> None:
        self.matches = matches
        self.clear()

        for match in self.matches:
            date_str = match.date.strftime("%a %b %d")

            if match.finished:
                score_str = f"{match.score.home} - {match.score.away}"
            else:
                score_str = Text("-", justify="center")

            match_str = f"{match.home_team.short_name} vs {match.away_team.short_name}"
            if self.team:
                if not match.finished:
                    result_cell = Text("-")
                elif match.winner == self.team:
                    result_cell = Text("W", style="bold green")
                elif match.winner is None:
                    result_cell = Text("D")
                else:
                    result_cell = Text("L", style="bold red")
                self.add_row(
                    str(match.matchday), date_str, result_cell, match_str, score_str
                )
            else:
                self.add_row(str(match.matchday), date_str, match_str, score_str)

    def scroll_to_unplayed(self) -> None:
        """Scroll to the first unplayed match."""
        for idx, match in enumerate(self.matches):
            if not match.finished:
                if idx < self.row_count:
                    self.move_cursor(row=idx)
                    break


class MatchesScreen(Screen):
    BINDINGS = [
        ("b", "app.pop_screen", "Back"),
        ("escape", "app.pop_screen", "Back"),
        ("u", "filter_to_unplayed", "Unplayed"),
        ("p", "filter_to_played", "Played"),
        ("a", "show_all", "All"),
    ]

    def __init__(self, team: Team, matches: list[Match]):
        super().__init__()
        self.team = team
        self.matches = matches

    def compose(self) -> ComposeResult:
        table = MatchesTable(self.team)
        table.border_title = self.team.short_name
        yield table
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(MatchesTable)
        table.update_data(self.matches)
        table.scroll_to_unplayed()
        table.focus()

    def _filter(self, filter_fn, scroll_to_unplayed=False) -> None:
        table = self.query_one(MatchesTable)
        filtered_matches = [m for m in self.matches if filter_fn(m)]
        table.update_data(filtered_matches)
        if scroll_to_unplayed:
            table.scroll_to_unplayed()

    def action_filter_to_played(self) -> None:
        self._filter(lambda m: m.finished)

    def action_filter_to_unplayed(self) -> None:
        self._filter(lambda m: not m.finished)

    def action_show_all(self) -> None:
        self._filter(lambda m: True, scroll_to_unplayed=True)


class StandingsApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.standings = get_standings()

    def compose(self) -> ComposeResult:
        yield StandingsTable()

    def on_mount(self) -> None:
        table = self.query_one(StandingsTable)
        table.update_data(self.standings)

    def on_data_table_row_selected(self, selection: DataTable.RowSelected):
        index = selection.data_table.get_row_index(selection.row_key)
        standing = self.standings[index]
        matches = get_matches(standing.team)
        self.push_screen(MatchesScreen(standing.team, matches))


if __name__ == "__main__":
    app = StandingsApp()
    app.run(inline=True)
