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
from textual.widgets import Label, DataTable, Rule


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


class MatchesTable(DataTable):
  def __init__(self, id: str):
    super().__init__(id=id)
    self.matches = []
    self.cursor_type = "row"
    self.zebra_stripes = False  # Disable zebra stripes since we're using 2 rows per match
    self.add_columns("Date", "Team", "Score", "MD")

  def update_data(self, matches: list[Match]) -> None:
    self.matches = matches
    self.clear()

    for match in self.matches:
      date_str = match.date.strftime("%a %b %d")
      matchday_str = str(match.matchday)

      if match.finished:
        score_str = str(match.score.home)
        score_str_away = str(match.score.away)
      else:
        score_str = ""
        score_str_away = ""

      # Add home team row
      self.add_row(
        date_str,
        match.home_team.short_name,
        score_str,
        matchday_str
      )

      # Add away team row (2nd row for this match)
      self.add_row(
        "",  # Empty date for second row
        match.away_team.short_name,
        score_str_away,
        ""  # Empty matchday for second row
      )

  def scroll_to_unplayed(self) -> None:
    """Scroll to the first unplayed match."""
    for idx, match in enumerate(self.matches):
      if not match.finished:
        # Each match takes 2 rows, so multiply by 2
        row_idx = idx * 2
        if row_idx < self.row_count:
          self.move_cursor(row=row_idx)
          break


class TeamView(Container):
  DEFAULT_CSS = """
    #name_label {
        padding: 1;
        text-style: bold;
    }

    #matches_table {
        height: 1fr;
    }
    """

  name = reactive("")
  matches: list[Match] = reactive([])

  def compose(self) -> ComposeResult:
    yield Label(self.name, id="name_label")
    yield MatchesTable(id="matches_table")

  def watch_name(self, new_name: str) -> None:
    try:
      self.query_one("#name_label", Label).update(new_name)
    except NoMatches:
      # This can happen before the label has been initialized.
      pass

  def watch_matches(self, matches: list[Match]) -> None:
    try:
      table = self.query_one("#matches_table", MatchesTable)
      table.update_data(matches)
      table.scroll_to_unplayed()
    except NoMatches:
      pass

  def filter(self, filter_fn, scroll_to_unplayed=False) -> None:
    try:
      table = self.query_one("#matches_table", MatchesTable)
      filtered_matches = [m for m in self.matches if filter_fn(m)]
      table.update_data(filtered_matches)
      if scroll_to_unplayed:
        table.scroll_to_unplayed()
    except NoMatches:
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
              ("a", "show_all", "Show all matches"),
              ("b", "show_standings", "Back to standings"),
              ("q", "quit", "Quit"),
            ]

  current_view = reactive("standings")

  def __init__(self):
    super().__init__()
    self.standings = get_standings()

  def on_data_table_row_selected(self, selection: DataTable.RowSelected):
    index = selection.data_table.get_row_index(selection.row_key)
    standing = self.standings[index]
    matches = get_matches(standing.team)

    team_view = self.query_one("#team_view", TeamView)
    team_view.name = standing.team.name
    team_view.matches = matches

    self.current_view = "matches"

  def compose(self) -> ComposeResult:
    """Create child widgets for the app."""
    yield StandingsTable()
    yield TeamView(id="team_view")

  def on_mount(self) -> None:
    table = self.query_one(DataTable)
    table.update_data(self.standings)
    # Initially hide the team view
    team_view = self.query_one("#team_view", TeamView)
    team_view.display = False

  def watch_current_view(self, view: str) -> None:
    """Update visibility based on current view."""
    table = self.query_one(DataTable)
    team_view = self.query_one("#team_view", TeamView)

    if view == "standings":
      table.display = True
      team_view.display = False
      table.focus()
    else:  # matches
      table.display = False
      team_view.display = True
      team_view.focus()

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

  def action_show_standings(self) -> None:
    """Return to the standings table view."""
    self.current_view = "standings"




if __name__ == '__main__':
  app = StandingsApp()
  app.run(inline=True)

