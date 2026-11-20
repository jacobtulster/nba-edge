from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
GAMES_PATH = DATA_DIR / "games.csv"
TEAM_STATE_PATH = DATA_DIR / "team_state.csv"
MODEL_PATH = DATA_DIR / "model_b.joblib"
EV_BOARD_PATH = DOCS_DIR / "ev_board.json"

load_dotenv(ROOT / ".env")

BALLDONTLIE_API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "").strip()
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "").strip()

# Research Elo params from the Colab notebook
BASE_ELO = 1500.0
HOME_ADVANTAGE = 65.0
K_FACTOR = 20.0
SEASON_CARRYOVER = 0.75

MODEL_B_FEATURES = [
    "home_elo_difference",
    "home_recent_form_advantage",
    "home_avg_margin_5",
    "away_avg_margin_5",
    "home_avg_margin_10",
    "away_avg_margin_10",
]

# Seasons to keep in the local DB (BallDontLie season = start year)
# Three completed + current is enough for Model B on free-tier API limits.
HISTORICAL_SEASONS = [2024, 2025, 2026]

RUN_HOUR_START_ET = 8
RUN_HOUR_END_ET = 23  # inclusive (11pm Eastern)

BALLDONTLIE_GAMES_URL = "https://api.balldontlie.io/v1/games"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
