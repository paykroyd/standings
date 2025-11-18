from datetime import date, datetime
from functools import cache
import os
import requests
import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label, DataTable, Rule
from textual.widget import Widget

from textual.containers import Container, Horizontal, HorizontalGroup, VerticalScroll
from textual.reactive import reactive
from textual.css.query import NoMatches


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
class Match:
    id: str
    utc_date: str
    home_team: Team
    away_team: Team

    @property
    def date(self) -> date:
        dt_object = datetime.fromisoformat(self.utc_date.replace('Z', '+00:00'))
        return dt_object.date()


def get_standings() -> list[Standing]:
    url = BASE_URL + "/competitions/PL/standings"
    headers = { 'X-Auth-Token': API_KEY }
    params = {"season": "2025" }

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()

    standings = resp.json()["standings"]
    table = [Standing.from_json(json.dumps(row)) for row in standings[0]["table"]]

    return table


@cache
def get_matches(team: Team):
    url = BASE_URL + f"/teams/{team.id}/matches/"

    headers = { 'X-Auth-Token': API_KEY }
    params = {"season": "2025", "competitions": "PL"}

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    matches = resp.json()["matches"]
    return [Match.from_json(json.dumps(m)) for m in matches]


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


class TeamView(VerticalScroll):
    DEFAULT_CSS = """
    #matches {
        height: auto;
        layout: vertical;
    }
    """

    name = reactive("")
    matches: list[Match] = reactive([])

    def compose(self) -> ComposeResult:
        yield Label(self.name, id="name_label")
        yield Container(id="matches")
    
    def watch_name(self, new_name: str) -> None:
        try:
            self.query_one("#name_label", Label).update(f"{new_name} - {len(self.matches)} matches")
        except NoMatches:
            # This can happen before the label has been initialized.
            pass

    def watch_matches(self, matches: list[Match]) -> None:
        try:
            container = self.query_one("#matches", Container) 
            container.remove_children()
            container.mount(*[MatchWidget(m) for m in matches])
        except NoMatches:
            pass

        
class MatchWidget(Widget):
    DEFAULT_CSS = """
        MatchWidget {
            height: 2;
        }
        """

    def __init__(self, match: Match):
        super().__init__()
        self.match = match

    def compose(self) -> ComposeResult:
        # TODO: flesh out the Match class and then show more details here.
        self.styles.height = 2

        yield Container(
            Label(self.match.date.strftime("%a %b %d")),
            Horizontal(
                Label(self.match.home_team.name),
                Label(" vs "),
                Label(self.match.away_team.name)
            )
        )


class StandingsApp(App):

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self):
        super().__init__()
        self.standings = get_standings()

    def on_data_table_row_highlighted(self, selection: DataTable.RowSelected):
        team_view = self.query_one("#team_view", TeamView)
        index = selection.data_table.get_row_index(selection.row_key)
        standing = self.standings[index]
        matches = get_matches(standing.team)
        team_view.name = standing.team.name
        team_view.matches = matches

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield StandingsTable()
        yield Rule(line_style="double")
        yield TeamView(id="team_view")

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

