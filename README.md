# Standings

## Setup

1. Create a free acount [football-data.org](https://www.football-data.org/client/register) and get an API key. The free tier allows 10 API calls per minute. 

2. Set an environment variable with your key:

```sh
export FOOTBALL_API_KEY='<YOUR_KEY_HERE>'
```

3. Install the pip requirements:

```sh
pip install requirements.md
```

## Run

For now just run it with the python command:

```sh
python standings.py
```

## Keybindings

- **Up/Down Arrows** to move up and down the table or match view.
- **Tab** to switch between the match view and table.
- **Ctrl-q** to quit.

## TODO

- UI improvements for the match view
- Better keybindings
- Better runner / install situation.
