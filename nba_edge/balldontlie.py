from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

from nba_edge.config import BALLDONTLIE_API_KEY, BALLDONTLIE_GAMES_URL


def _headers() -> dict[str, str]:
    if not BALLDONTLIE_API_KEY:
        raise ValueError(
            "Missing BALLDONTLIE_API_KEY. Set it in .env or GitHub Actions secrets."
        )
    return {"Authorization": BALLDONTLIE_API_KEY}


def _get(params: list[tuple[str, Any]], max_retries: int = 4) -> dict:
    for attempt in range(max_retries):
        response = requests.get(
            BALLDONTLIE_GAMES_URL,
            headers=_headers(),
            params=params,
            timeout=60,
        )
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 15))
            time.sleep(max(wait, 5))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("BallDontLie rate limit exceeded after retries.")


def fetch_season_games(season: int) -> list[dict]:
    """Download all regular-season games for a BallDontLie season year."""
    games: list[dict] = []
    cursor: int | None = None

    while True:
        params: list[tuple[str, Any]] = [
            ("seasons[]", season),
            ("per_page", 100),
        ]
        if cursor is not None:
            params.append(("cursor", cursor))

        payload = _get(params)
        batch = payload.get("data") or []
        games.extend(batch)

        meta = payload.get("meta") or {}
        next_cursor = meta.get("next_cursor")
        if not next_cursor or not batch:
            break
        cursor = next_cursor
        time.sleep(0.35)

    return games


def fetch_games_for_date(date_iso: str, season: int) -> list[dict]:
    params: list[tuple[str, Any]] = [
        ("dates[]", date_iso),
        ("seasons[]", season),
        ("per_page", 100),
    ]
    payload = _get(params)
    return payload.get("data") or []


def games_to_dataframe(raw_games: list[dict]) -> pd.DataFrame:
    rows = []
    for g in raw_games:
        home = g.get("home_team") or {}
        away = g.get("visitor_team") or {}
        rows.append(
            {
                "game_id": g.get("id"),
                "game_date": str(g.get("date") or "")[:10],
                "datetime_utc": g.get("datetime") or g.get("date"),
                "season": g.get("season"),
                "postseason": bool(g.get("postseason")),
                "status": g.get("status"),
                "status_state": (g.get("status_state") or "").lower(),
                "home_team": home.get("full_name") or home.get("name"),
                "away_team": away.get("full_name") or away.get("name"),
                "home_abbreviation": (home.get("abbreviation") or "").upper(),
                "away_abbreviation": (away.get("abbreviation") or "").upper(),
                "home_points": g.get("home_team_score"),
                "away_points": g.get("visitor_team_score"),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates("game_id")
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["home_points"] = pd.to_numeric(df["home_points"], errors="coerce")
    df["away_points"] = pd.to_numeric(df["away_points"], errors="coerce")
    return df.sort_values(["game_date", "game_id"]).reset_index(drop=True)


def is_final(row: pd.Series) -> bool:
    state = str(row.get("status_state") or "").lower()
    status = str(row.get("status") or "").lower()
    return state == "final" or status == "final"


def current_nba_season(today: pd.Timestamp | None = None) -> int:
    """NBA season label = calendar year of the season start (Oct)."""
    today = today or pd.Timestamp.now(tz="America/New_York")
    if today.tzinfo is None:
        today = today.tz_localize("America/New_York")
    else:
        today = today.tz_convert("America/New_York")
    return today.year if today.month >= 10 else today.year - 1
