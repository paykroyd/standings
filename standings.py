import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from typing import cast

import requests
from dataclasses_json import dataclass_json, LetterCase
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, DataTable, Rule


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
    dt_object = datetime.fromisoformat(self.utc_date.replace('Z', '+00:00'))
    return dt_object.date()

  @property
  def finished(self) -> bool:
    return self.status == 'FINISHED'


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


class MatchWidget(Widget):
  DEFAULT_CSS = """
        MatchWidget {
            height: 4;
            height: 1fr;
            border: solid green;
        }

        #match_date {
            text-style: bold;
            color: #d2d2e0;
        }


        """

  def __init__(self, match: Match):
    super().__init__()
    self.match = match

  def compose(self) -> ComposeResult:
    # TODO: flesh out the Match class and then show more details here.

    if self.match.finished:
      self.styles.height = 5
      yield Container(
        Label(self.match.date.strftime("%a %b %d"), id="match_date"),
        Horizontal(
          Label(self.match.home_team.name),
          Label(" vs "),
          Label(self.match.away_team.name)
        ),
        Horizontal(
          Label(str(self.match.score.home)),
          Label(" - "),
          Label(str(self.match.score.away)),
        )
      )
    else:
      self.styles.height = 4
      yield Container(
        Label(self.match.date.strftime("%a %b %d"), id="match_date"),
        Horizontal(
          Label(self.match.home_team.name, id="home_label"),
          Label(" vs ", id="vs-label"),
          Label(self.match.away_team.name, id="away_label")
        ),
      )


class TeamView(VerticalScroll):
  DEFAULT_CSS = """
    #matches {
        height: auto;
        layout: vertical;
    }

    #name_label {
        padding: 1;
        text-style: bold;
    }
    """

  name = reactive("")
  matches: list[Match] = reactive([])

  def compose(self) -> ComposeResult:
    yield Label(self.name, id="name_label")
    yield Container(id="matches")

  def watch_name(self, new_name: str) -> None:
    try:
      self.query_one("#name_label", Label).update(new_name)
    except NoMatches:
      # This can happen before the label has been initialized.
      pass

  async def watch_matches(self, matches: list[Match]) -> None:
    try:
      container = self.query_one("#matches", Container) 
      container.remove_children()
      widgets = [MatchWidget(m) for m in matches]
      await container.mount(*widgets)
      self.scroll_to_unplayed(widgets)
    except NoMatches:
      pass

  def scroll_to_unplayed(self, widgets: list[MatchWidget]) -> None:
    scroll_target = None
    for child in widgets:
      child.refresh(layout=True)
      if scroll_target is None and not child.match.finished:
        scroll_target = child

    if scroll_target:
      self.call_after_refresh(self.scroll_to_widget, scroll_target, animate=False)
    else:
      self.scroll_to(y=0, animate=False)


  def filter(self, filter_fn, scroll_to_unplayed=False) -> None:
    try:
      container = self.query_one("#matches", Container)
      container.remove_children()
      widgets = [MatchWidget(m) for m in self.matches if filter_fn(m)]
      container.mount(*widgets)

      if scroll_to_unplayed:
        self.scroll_to_unplayed(widgets)
      else:
        self.scroll_to(y=0, animate=False)
    except Nomatches:
      pass

  def filter_to_played(self) -> None:
    self.filter(lambda m: m.finished)

  def filter_to_unplayed(self) -> None:
    self.filter(lambda m: not m.finished)

  def show_all(self) -> None:
      self.filter(lambda m: True, scroll_to_unplayed=True)




class StandingsApp(App):

  BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
              ("u", "filter_to_unplayed", "Show unplayed matches"),
              ("p", "filter_to_played", "Show played matches"),
              ("a", "show_all", "Show all matches"),]

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

  def action_filter_to_unplayed(self) -> None:
    """Filters the team view to only unplayed matches."""
    team_view = self.query_one("#team_view", TeamView)
    team_view.filter_to_unplayed()

  def action_filter_to_played(self) -> None:
    """Filters the team view to only unplayed matches."""
    team_view = self.query_one("#team_view", TeamView)
    team_view.filter_to_played()

  def action_show_all(self) -> None:
    """Filters the team view to only unplayed matches."""
    team_view = self.query_one("#team_view", TeamView)
    team_view.show_all()




if __name__ == '__main__':
  app = StandingsApp()
  app.run()

