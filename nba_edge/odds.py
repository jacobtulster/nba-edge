from __future__ import annotations

import re
from typing import Any

import requests

from nba_edge.config import ODDS_API_KEY, ODDS_URL

# Full name / nickname → abbreviation
TEAM_ALIASES = {
    "atlanta hawks": "ATL",
    "boston celtics": "BOS",
    "brooklyn nets": "BKN",
    "charlotte hornets": "CHA",
    "chicago bulls": "CHI",
    "cleveland cavaliers": "CLE",
    "dallas mavericks": "DAL",
    "denver nuggets": "DEN",
    "detroit pistons": "DET",
    "golden state warriors": "GSW",
    "houston rockets": "HOU",
    "indiana pacers": "IND",
    "la clippers": "LAC",
    "los angeles clippers": "LAC",
    "la lakers": "LAL",
    "los angeles lakers": "LAL",
    "memphis grizzlies": "MEM",
    "miami heat": "MIA",
    "milwaukee bucks": "MIL",
    "minnesota timberwolves": "MIN",
    "new orleans pelicans": "NOP",
    "new york knicks": "NYK",
    "oklahoma city thunder": "OKC",
    "orlando magic": "ORL",
    "philadelphia 76ers": "PHI",
    "phoenix suns": "PHX",
    "portland trail blazers": "POR",
    "sacramento kings": "SAC",
    "san antonio spurs": "SAS",
    "toronto raptors": "TOR",
    "utah jazz": "UTA",
    "washington wizards": "WAS",
}


def team_key(name: str) -> str:
    raw = str(name).strip()
    lower = raw.lower()
    if lower in TEAM_ALIASES:
        return TEAM_ALIASES[lower]
    if len(raw) <= 3:
        return raw.upper()
    return re.sub(r"[^a-z0-9]", "", lower)


def american_or_decimal_to_implied(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        return 0.0
    return 1.0 / decimal_odds


def expected_value(model_prob: float, decimal_odds: float) -> float:
    """EV per $1 stake at decimal odds."""
    return model_prob * decimal_odds - 1.0


def fetch_h2h_odds() -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not ODDS_API_KEY:
        raise ValueError("Missing ODDS_API_KEY. Set it in .env or GitHub Actions secrets.")

    response = requests.get(
        ODDS_URL,
        params={
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        },
        timeout=60,
    )
    response.raise_for_status()
    meta = {
        "requests_remaining": response.headers.get("x-requests-remaining", ""),
        "requests_used": response.headers.get("x-requests-used", ""),
    }
    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected Odds API payload: {data}")
    return data, meta


def best_h2h_prices(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pick the best (highest) decimal moneyline for each side across US books."""
    rows = []
    for event in events:
        home_name = event.get("home_team")
        away_name = event.get("away_team")
        home_abbr = team_key(home_name)
        away_abbr = team_key(away_name)

        best_home = None
        best_away = None
        best_home_book = None
        best_away_book = None

        for book in event.get("bookmakers") or []:
            book_name = book.get("title") or book.get("key")
            for market in book.get("markets") or []:
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes") or []:
                    price = float(outcome.get("price") or 0)
                    name = outcome.get("name")
                    if team_key(name) == home_abbr:
                        if best_home is None or price > best_home:
                            best_home = price
                            best_home_book = book_name
                    elif team_key(name) == away_abbr:
                        if best_away is None or price > best_away:
                            best_away = price
                            best_away_book = book_name

        rows.append(
            {
                "home_team": home_name,
                "away_team": away_name,
                "home_abbreviation": home_abbr,
                "away_abbreviation": away_abbr,
                "commence_time": event.get("commence_time"),
                "home_decimal": best_home,
                "away_decimal": best_away,
                "home_book": best_home_book,
                "away_book": best_away_book,
            }
        )
    return rows
