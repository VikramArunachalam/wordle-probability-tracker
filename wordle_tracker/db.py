"""Thin Postgres (Supabase) data-access layer for cross-player stats.

Every write is fail-open: a DB hiccup should never block someone from
playing or seeing their just-finished game's results, which already live in
st.session_state regardless of whether the save below succeeds. Reads
return empty results on failure so the leaderboard page renders (if
emptily) instead of crashing. Requires a `[connections.supabase]` entry in
secrets.toml -- see .streamlit/secrets.toml.example.
"""

import pandas as pd
import streamlit as st
from sqlalchemy import text

# Matches app.py's MAX_GUESSES -- the leaderboard breaks percentile down by
# guess number, one column per turn 1..MAX_GUESSES.
MAX_GUESSES = 6

EMPTY_LEADERBOARD_COLUMNS = [
    "nickname",
    "games_played",
    "win_rate",
    *[f"guess_{i}_pct" for i in range(1, MAX_GUESSES + 1)],
]
EMPTY_SHARED_SECRET_COLUMNS = [
    "secret",
    "turn",
    "guess_a",
    "n_after_a",
    "percentile_a",
    "guess_b",
    "n_after_b",
    "percentile_b",
]


def _connection():
    return st.connection("supabase", type="sql")


def ensure_user(nickname: str) -> int | None:
    """Case-insensitive lookup-or-create. Returns None (never raises) on failure."""
    nickname = nickname.strip()
    if not nickname:
        return None
    try:
        with _connection().session as session:
            row = session.execute(
                text("select id from users where lower(nickname) = lower(:nickname)"),
                {"nickname": nickname},
            ).fetchone()
            if row:
                return row[0]
            row = session.execute(
                text("insert into users (nickname) values (:nickname) returning id"),
                {"nickname": nickname},
            ).fetchone()
            session.commit()
            return row[0]
    except Exception:
        return None


def save_game(user_id: int, secret: str, won: bool, num_guesses: int) -> int | None:
    try:
        with _connection().session as session:
            row = session.execute(
                text(
                    "insert into games (user_id, secret, won, num_guesses) "
                    "values (:user_id, :secret, :won, :num_guesses) returning id"
                ),
                {"user_id": user_id, "secret": secret, "won": won, "num_guesses": num_guesses},
            ).fetchone()
            session.commit()
            return row[0]
    except Exception as exc:
        st.warning(f"Couldn't save this game's stats ({exc.__class__.__name__}).")
        return None


def save_turn_analysis(game_id: int, results: list[dict]) -> None:
    try:
        with _connection().session as session:
            for r in results:
                session.execute(
                    text(
                        "insert into turn_analysis "
                        "(game_id, turn, guess, n_after, percentile, median_remaining) "
                        "values (:game_id, :turn, :guess, :n_after, :percentile, :median_remaining)"
                    ),
                    {
                        "game_id": game_id,
                        "turn": r["turn"],
                        "guess": r["guess"],
                        "n_after": r["n_after"],
                        "percentile": r["percentile"],
                        "median_remaining": r["median_remaining"],
                    },
                )
            session.commit()
    except Exception as exc:
        st.warning(f"Couldn't save this game's turn-by-turn analysis ({exc.__class__.__name__}).")


def get_leaderboard() -> pd.DataFrame:
    """One row per player: games played, win rate, and average percentile broken
    down per guess number. A guess_N_pct column is NULL (shown as N/A) for a
    player who has never had a turn N analyzed -- e.g. nobody's taken 6 guesses."""
    per_turn_cols = ",\n                ".join(
        f"avg(case when t.turn = {i} then t.percentile end) as guess_{i}_pct"
        for i in range(1, MAX_GUESSES + 1)
    )
    try:
        return _connection().query(
            f"""
            select
                u.nickname,
                count(distinct g.id) as games_played,
                avg(case when g.won then 1.0 else 0.0 end) as win_rate,
                {per_turn_cols}
            from users u
            join games g on g.user_id = u.id
            left join turn_analysis t on t.game_id = g.id
            group by u.nickname
            order by win_rate desc, games_played desc
            """,
            ttl=0,
        )
    except Exception:
        return pd.DataFrame(columns=EMPTY_LEADERBOARD_COLUMNS)


def get_shared_secret_games(nickname_a: str, nickname_b: str) -> pd.DataFrame:
    """Turn-by-turn comparison for games where both players drew the same secret
    and both ran the full guess-quality analysis (only then does turn_analysis exist)."""
    try:
        return _connection().query(
            """
            select
                ga.secret,
                ta.turn,
                ta.guess as guess_a, ta.n_after as n_after_a, ta.percentile as percentile_a,
                tb.guess as guess_b, tb.n_after as n_after_b, tb.percentile as percentile_b
            from games ga
            join users ua on ua.id = ga.user_id
            join games gb on gb.secret = ga.secret and gb.id != ga.id
            join users ub on ub.id = gb.user_id
            join turn_analysis ta on ta.game_id = ga.id
            join turn_analysis tb on tb.game_id = gb.id and tb.turn = ta.turn
            where lower(ua.nickname) = lower(:a) and lower(ub.nickname) = lower(:b)
            order by ga.played_at desc, ta.turn asc
            """,
            params={"a": nickname_a, "b": nickname_b},
            ttl=0,
        )
    except Exception:
        return pd.DataFrame(columns=EMPTY_SHARED_SECRET_COLUMNS)
