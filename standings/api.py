"""Football data API functions."""

import json
import os
from functools import cache

import requests

from standings.models import Match, Standing, Team

API_KEY = os.environ.get("FOOTBALL_API_KEY")
BASE_URL = "http://api.football-data.org/v4"


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
