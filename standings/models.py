"""Football data API models."""

from dataclasses import dataclass
from datetime import date, datetime

from dataclasses_json import LetterCase, dataclass_json


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
