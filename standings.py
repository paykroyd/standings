import os
import requests
import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, DataTable
from textual.widgets import Static
from rich.table import Table



API_KEY = os.environ.get("FOOTBALL_API_KEY")
BASE_URL = "http://api.football-data.org/v4"

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
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


def get_standings() -> list[Standing]:
    url = BASE_URL + "/competitions/PL/standings"
    print(API_KEY)
    headers = { 'X-Auth-Token': API_KEY }
    params = {"season": "2025" }

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()

    standings = resp.json()["standings"]
    table = [Standing.from_json(json.dumps(row)) for row in standings[0]["table"]]

    return table


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
            self.add_row(str(team.position),
                          team.team.short_name,
                          str(team.played_games),
                          str(team.won),
                          str(team.draw),
                          str(team.lost),
                          str(team.goals_for),
                          str(team.goals_against),
                          str(team.goal_difference),
                          str(team.points))


class StandingsApp(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self):
        super().__init__()
        self.standings = get_standings()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield StandingsTable()


    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.update_data(self.standings)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == '__main__':
    app = StandingsApp()
    app.run()

