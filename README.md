# Standings

## Setup

1. Create a free acount [football-data.org](https://www.football-data.org/client/register) and get an API key. The free tier allows 10 API calls per minute. 

2. Set an environment variable with your key:

```sh
export FOOTBALL_API_KEY='<YOUR_KEY_HERE>'
```

3. Install the pip requirements:

```sh
pip install -r requirements.txt
```

## Run

For now just run it with the python command:

```sh
python standings.py

```

## Build

```sh
pyinstaller standings.spec
```

## Keybindings

- **j/k** to move up and down the standings table or match view.
- **Enter** to select a team and view their matches.
- **Escape** to return to the standings table.
- **u** to show only unplayed matches (when viewing matches).
- **p** to show only played matches (when viewing matches).
- **a** to show all matches (when viewing matches).
- **q** to quit.

## TODO

- UI improvements for the match view
