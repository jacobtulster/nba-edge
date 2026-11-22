from __future__ import annotations

import os
import time
from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests

from nba_edge.config import BALLDONTLIE_API_KEY, BALLDONTLIE_GAMES_URL

# Free-tier safe default: ~4 requests/minute
REQUEST_DELAY = float(os.environ.get("NBA_EDGE_REQUEST_DELAY", "1.5"))


def _headers() -> dict[str, str]:
    if not BALLDONTLIE_API_KEY:
        raise ValueError(
            "Missing BALLDONTLIE_API_KEY. Set it in .env or GitHub Actions secrets."
        )
    return {"Authorization": BALLDONTLIE_API_KEY}


def _get(params: list[tuple[str, Any]], max_retries: int = 12) -> dict:
    for attempt in range(max_retries):
        response = requests.get(
            BALLDONTLIE_GAMES_URL,
            headers=_headers(),
            params=params,
            timeout=30,
        )
        if response.status_code == 429:
            wait = min(int(response.headers.get("Retry-After", 20)), 30)
            print(f"Rate limited (attempt {attempt + 1}/{max_retries}); waiting {wait}s")
            time.sleep(wait)
            continue
        response.raise_for_status()
        if REQUEST_DELAY > 0:
            time.sleep(REQUEST_DELAY)
        return response.json()
    raise RuntimeError("BallDontLie rate limit exceeded after retries.")


def fetch_games(seasons: list[int], label: str = "games") -> list[dict]:
    """Paginate games for one or more seasons with progress + safety caps."""
    games: list[dict] = []
    cursor: int | None = None
    seen_cursors: set[int] = set()
    page = 0
    max_pages = 80

    while page < max_pages:
        page += 1
        params: list[tuple[str, Any]] = [("per_page", 100)]
        for season in seasons:
            params.append(("seasons[]", season))
        if cursor is not None:
            params.append(("cursor", cursor))

        payload = _get(params)
        batch = payload.get("data") or []
        games.extend(batch)

        meta = payload.get("meta") or {}
        next_cursor = meta.get("next_cursor")
        print(f"  {label} page {page}: +{len(batch)} (total {len(games)})")

        if not next_cursor or not batch:
            break
        if next_cursor in seen_cursors:
            print("  Stopping: repeated cursor.")
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    return games


def fetch_season_games(season: int) -> list[dict]:
    return fetch_games([season], label=f"season {season}")


def fetch_games_for_dates(dates: list[str], season: int) -> list[dict]:
    """Fetch a small date window (used for hourly incremental updates)."""
    params: list[tuple[str, Any]] = [
        ("seasons[]", season),
        ("per_page", 100),
    ]
    for d in dates:
        params.append(("dates[]", d))
    payload = _get(params)
    return payload.get("data") or []


def fetch_games_for_date(date_iso: str, season: int) -> list[dict]:
    return fetch_games_for_dates([date_iso], season)


def recent_date_strings(days: int = 14, today: date | None = None) -> list[str]:
    today = today or date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(days)]


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
    return (
        state == "final"
        or status == "final"
        or "final" in status
        or state in {"post", "closed"}
    )


def current_nba_season(today: pd.Timestamp | None = None) -> int:
    """NBA season label = calendar year of the season start (Oct)."""
    today = today or pd.Timestamp.now(tz="America/New_York")
    if today.tzinfo is None:
        today = today.tz_localize("America/New_York")
    else:
        today = today.tz_convert("America/New_York")
    return today.year if today.month >= 10 else today.year - 1


def merge_prefer_finals(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    """Replace overlapping game_ids, preferring final / scored rows."""
    if incoming is None or incoming.empty:
        return existing
    if existing is None or existing.empty:
        return incoming.copy()

    frames = [existing.copy(), incoming.copy()]
    for frame in frames:
        frame["game_id"] = pd.to_numeric(frame["game_id"], errors="coerce")
        state = frame.get("status_state")
        status = frame.get("status")
        state_s = state.fillna("").astype(str).str.lower() if state is not None else ""
        status_s = status.fillna("").astype(str).str.lower() if status is not None else ""
        has_score = frame["home_points"].notna() & frame["away_points"].notna()
        is_done = (
            state_s.eq("final")
            | status_s.eq("final")
            | status_s.str.contains("final", na=False)
        )
        frame["_prefer"] = is_done.astype(int) * 2 + has_score.astype(int)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["game_id", "_prefer"]).drop_duplicates(
        "game_id", keep="last"
    )
    return combined.drop(columns=["_prefer"], errors="ignore").reset_index(drop=True)


def _espn_abbr(abbr: str) -> str:
    """Normalize ESPN abbreviations toward BallDontLie / Odds API codes."""
    a = str(abbr or "").upper()
    return {
        "NY": "NYK",
        "GS": "GSW",
        "SA": "SAS",
        "NO": "NOP",
        "UTAH": "UTA",
        "WSH": "WAS",
    }.get(a, a)


def _espn_game_date_et(event_date: str | None, fallback: str) -> str:
    """Scoreboard dates are requested in ET; keep ET calendar day, not UTC slice."""
    if not event_date:
        return str(fallback)[:10]
    ts = pd.to_datetime(event_date, utc=True, errors="coerce")
    if pd.isna(ts):
        return str(event_date)[:10]
    try:
        return ts.tz_convert("America/New_York").strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return str(fallback)[:10]


def fetch_games_for_dates_espn(dates: list[str]) -> list[dict]:
    """Public ESPN scoreboard fallback when BallDontLie is unavailable/stale."""
    out: list[dict] = []
    for d in dates:
        ymd = str(d).replace("-", "")[:8]
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
            f"scoreboard?dates={ymd}"
        )
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            print(f"  ESPN scoreboard {d}: {exc}")
            continue
        if REQUEST_DELAY > 0:
            time.sleep(min(REQUEST_DELAY, 0.4))
        for event in payload.get("events") or []:
            comp = (event.get("competitions") or [{}])[0]
            status = ((comp.get("status") or {}).get("type") or {})
            competitors = comp.get("competitors") or []
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            home_team = home.get("team") or {}
            away_team = away.get("team") or {}
            completed = bool(status.get("completed")) or str(status.get("name") or "").upper() == "STATUS_FINAL"
            out.append(
                {
                    "id": event.get("id"),
                    "date": str(d)[:10],  # keep the requested ET slate day
                    "datetime": event.get("date"),
                    "season": None,
                    "postseason": False,
                    "status": "Final" if completed else (status.get("description") or status.get("name")),
                    "status_state": "final" if completed else "in_progress",
                    "home_team": {
                        "full_name": home_team.get("displayName"),
                        "name": home_team.get("name"),
                        "abbreviation": _espn_abbr(home_team.get("abbreviation")),
                    },
                    "visitor_team": {
                        "full_name": away_team.get("displayName"),
                        "name": away_team.get("name"),
                        "abbreviation": _espn_abbr(away_team.get("abbreviation")),
                    },
                    "home_team_score": home.get("score"),
                    "visitor_team_score": away.get("score"),
                    "grade_source": "espn",
                }
            )
    return out


def _match_keys(df: pd.DataFrame) -> pd.Series:
    return (
        df["away_abbreviation"].astype(str).str.upper()
        + "|"
        + df["home_abbreviation"].astype(str).str.upper()
    )


def refresh_scores_for_dates(games: pd.DataFrame, dates: list[str], season: int) -> pd.DataFrame:
    """Pull fresh scores for specific dates (BDL, then ESPN) and merge."""
    uniq = sorted({str(d)[:10] for d in dates if d})
    if not uniq:
        return games
    recent = pd.DataFrame()
    try:
        raw = fetch_games_for_dates(uniq, season)
        recent = games_to_dataframe(raw)
        if not recent.empty:
            recent["grade_source"] = "balldontlie"
    except Exception as exc:  # noqa: BLE001
        print(f"  BDL score refresh failed: {exc}")
    # Always overlay ESPN finals so we can grade even when BDL lags / lacks a key.
    espn_raw = fetch_games_for_dates_espn(uniq)
    espn_df = games_to_dataframe(espn_raw)
    if not espn_df.empty:
        espn_df["grade_source"] = "espn"
        # ESPN ids differ from BDL — remap onto BDL ids by away|home (date±1 tolerant).
        if games is not None and not games.empty:
            keyed = games.copy()
            keyed["_mk"] = _match_keys(keyed)
            keyed["_d"] = keyed["game_date"].astype(str).str[:10]
            espn_df["_mk"] = _match_keys(espn_df)
            espn_df["_d"] = espn_df["game_date"].astype(str).str[:10]
            id_map: dict[str, Any] = {}
            for _, r in keyed.iterrows():
                if pd.isna(r.get("game_id")):
                    continue
                id_map[f"{r['_d']}|{r['_mk']}"] = r["game_id"]
                id_map[str(r["_mk"])] = r["game_id"]
            mapped = []
            for _, r in espn_df.iterrows():
                gid = id_map.get(f"{r['_d']}|{r['_mk']}") or id_map.get(str(r["_mk"]))
                mapped.append(gid if gid is not None else r["game_id"])
            espn_df["game_id"] = mapped
            espn_df = espn_df.drop(columns=["_mk", "_d"], errors="ignore")
        recent = merge_prefer_finals(recent, espn_df) if not recent.empty else espn_df
    print(f"  score refresh {uniq[0]}…{uniq[-1]}: {len(recent)} games")
    return merge_prefer_finals(games, recent)
