#!/usr/bin/env python3
"""Pull / update NBA games from BallDontLie into data/games.csv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from nba_edge.balldontlie import (
    current_nba_season,
    fetch_season_games,
    games_to_dataframe,
)
from nba_edge.config import DATA_DIR, GAMES_PATH, HISTORICAL_SEASONS


def _save(games: pd.DataFrame) -> None:
    games = games.drop_duplicates("game_id").sort_values(["game_date", "game_id"])
    games.to_csv(GAMES_PATH, index=False)
    completed = games[
        games["status_state"].fillna("").str.lower().eq("final")
        | games["status"].fillna("").astype(str).str.lower().eq("final")
    ]
    print(f"Saved {len(games)} games → {GAMES_PATH}")
    print(f"Completed finals: {len(completed)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="Re-download all historical seasons (slow; use sparingly)",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    season_now = current_nba_season()

    if args.full or not GAMES_PATH.exists():
        seasons = sorted(set(HISTORICAL_SEASONS + [season_now]))
        print(f"Full refresh for seasons: {seasons}")
        frames = []
        for season in seasons:
            print(f"Fetching season {season}…")
            raw = fetch_season_games(season)
            df = games_to_dataframe(raw)
            print(f"  {len(df)} games")
            frames.append(df)
        games = pd.concat(frames, ignore_index=True)
        _save(games)
        return 0

    # Incremental: keep history, refresh current season only
    existing = pd.read_csv(GAMES_PATH)
    existing["game_date"] = pd.to_datetime(existing["game_date"], errors="coerce")
    print(f"Incremental refresh for season {season_now}…")
    raw = fetch_season_games(season_now)
    current = games_to_dataframe(raw)
    print(f"  {len(current)} current-season games")

    prior = existing[existing["season"] != season_now]
    games = pd.concat([prior, current], ignore_index=True)
    _save(games)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
