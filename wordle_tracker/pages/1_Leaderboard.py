"""Leaderboard and head-to-head comparison across all players."""

import sys
from pathlib import Path

# `streamlit run` puts this file's own directory on sys.path, not the
# project root, so the `wordle_tracker` package isn't importable without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from wordle_tracker import db

st.set_page_config(page_title="Wordle Tracker Leaderboard", page_icon="🏆", layout="centered")
st.markdown("## Leaderboard")

leaderboard = db.get_leaderboard()
if leaderboard.empty:
    st.caption("No games saved yet -- play a round and save your stats to show up here.")
else:
    display = leaderboard.rename(
        columns={
            "nickname": "Nickname",
            "games_played": "Games",
            "win_rate": "Win rate",
            **{f"guess_{i}_pct": f"Guess {i}" for i in range(1, db.MAX_GUESSES + 1)},
        }
    )
    st.dataframe(
        display.style.format(
            {"Win rate": "{:.0%}", **{f"Guess {i}": "{:.1f}" for i in range(1, db.MAX_GUESSES + 1)}},
            na_rep="N/A",
        ),
        hide_index=True,
        width="stretch",
    )

st.markdown("## Head-to-head")
if len(leaderboard) < 2:
    st.caption("Need at least two players with saved games to compare.")
else:
    nicknames = leaderboard["nickname"].tolist()
    col1, col2 = st.columns(2)
    with col1:
        nickname_a = st.selectbox("Player A", nicknames, index=0)
    with col2:
        nickname_b = st.selectbox("Player B", nicknames, index=1)

    if nickname_a == nickname_b:
        st.caption("Pick two different players.")
    else:
        stats_a = leaderboard[leaderboard["nickname"] == nickname_a].iloc[0]
        stats_b = leaderboard[leaderboard["nickname"] == nickname_b].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.metric(nickname_a, f"{stats_a['win_rate']:.0%} win rate")
            st.caption(f"{stats_a['games_played']} games played")
        with col2:
            st.metric(nickname_b, f"{stats_b['win_rate']:.0%} win rate")
            st.caption(f"{stats_b['games_played']} games played")

        per_guess = pd.DataFrame(
            {
                "Guess": list(range(1, db.MAX_GUESSES + 1)),
                nickname_a: [stats_a[f"guess_{i}_pct"] for i in range(1, db.MAX_GUESSES + 1)],
                nickname_b: [stats_b[f"guess_{i}_pct"] for i in range(1, db.MAX_GUESSES + 1)],
            }
        )
        st.dataframe(
            per_guess.style.format({nickname_a: "{:.1f}", nickname_b: "{:.1f}"}, na_rep="N/A"),
            hide_index=True,
            width="stretch",
        )

        shared = db.get_shared_secret_games(nickname_a, nickname_b)
        if shared.empty:
            st.caption(
                f"{nickname_a} and {nickname_b} haven't both analyzed a game with "
                "the same secret word yet."
            )
        else:
            st.markdown("#### Turn-by-turn, same secret word")
            for secret, group in shared.groupby("secret"):
                st.caption(f"Secret: {secret.upper()}")
                st.dataframe(
                    group.drop(columns="secret").rename(
                        columns={
                            "turn": "Guess",
                            "guess_a": f"{nickname_a}'s word",
                            "n_after_a": f"{nickname_a} left",
                            "percentile_a": f"{nickname_a} pct",
                            "guess_b": f"{nickname_b}'s word",
                            "n_after_b": f"{nickname_b} left",
                            "percentile_b": f"{nickname_b} pct",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
