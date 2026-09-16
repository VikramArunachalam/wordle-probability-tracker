"""Streamlit UI for the Wordle probability tracker.

Thin presentation layer only -- all game logic lives in candidates.py,
feedback.py, and probability.py and is reused as-is.
"""

import sys
from pathlib import Path

# `streamlit run` puts this file's own directory on sys.path, not the
# project root, so the `wordle_tracker` package isn't importable without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from wordle_tracker.candidates import filter_candidates
from wordle_tracker.feedback import GRAY, GREEN, YELLOW, compute_feedback
from wordle_tracker.probability import informed_probability, naive_probability

DATA_DIR = Path(__file__).parent / "data"
MAX_GUESSES = 6
WORD_LENGTH = 5

TILE_COLORS = {
    GREEN: "#6aaa64",
    YELLOW: "#c9b458",
    GRAY: "#787c7f",
}

st.set_page_config(page_title="Wordle Probability Tracker", page_icon="🟩", layout="centered")


@st.cache_data
def load_word_list(path: Path) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@600;700;800&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Libre Franklin', 'Helvetica Neue', Arial, sans-serif;
        }
        .wordle-title {
            font-family: 'Libre Franklin', sans-serif;
            font-weight: 800;
            font-size: 2.2rem;
            letter-spacing: 0.02em;
            text-align: center;
            border-bottom: 1px solid #d3d6da;
            padding-bottom: 0.6rem;
            margin-bottom: 1rem;
        }
        .wordle-row {
            display: flex;
            justify-content: center;
            gap: 5px;
            margin-bottom: 5px;
        }
        .wordle-tile {
            width: 52px;
            height: 52px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
            font-weight: 700;
            color: white;
            text-transform: uppercase;
            border-radius: 3px;
            box-sizing: border-box;
        }
        .wordle-tile.empty {
            background: white;
            border: 2px solid #d3d6da;
            color: #d3d6da;
        }
        .stat-box {
            background: #f6f6f6;
            border-radius: 8px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 0.6rem;
            border: 1px solid #e3e3e3;
        }
        .stat-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #787c7f;
            font-weight: 700;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: 800;
            color: #1a1a1b;
        }
        .stats-history-wrap {
            background: #ffffff;
            border: 1px solid #d3d6da;
            border-radius: 8px;
            padding: 0.3rem 0.75rem;
            margin-bottom: 0.8rem;
        }
        .stats-history {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }
        .stats-history th {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #787c7f;
            font-weight: 700;
            text-align: right;
            padding: 0.35rem 0.5rem;
            border-bottom: 2px solid #d3d6da;
        }
        .stats-history th:first-child, .stats-history td:first-child {
            text-align: left;
        }
        .stats-history td {
            text-align: right;
            padding: 0.4rem 0.5rem;
            border-bottom: 1px solid #e3e3e3;
            font-weight: 700;
            color: #1a1a1b;
        }
        .stats-history tr:last-child td {
            color: #1a1a1b;
            background: #f6f6f6;
        }
        .candidate-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 0.4rem 0.1rem;
        }
        .candidate-chip {
            background: #f6f6f6;
            border: 1px solid #d3d6da;
            border-radius: 4px;
            padding: 4px 9px;
            font-weight: 700;
            letter-spacing: 0.03em;
            font-size: 0.85rem;
            text-transform: uppercase;
            color: #1a1a1b;
        }
        .win-banner {
            background: #6aaa64;
            color: white;
            font-weight: 800;
            text-align: center;
            padding: 0.9rem;
            border-radius: 8px;
            font-size: 1.2rem;
            margin-top: 0.6rem;
        }
        .lose-banner {
            background: #787c7f;
            color: white;
            font-weight: 800;
            text-align: center;
            padding: 0.9rem;
            border-radius: 8px;
            font-size: 1.2rem;
            margin-top: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_row(letters: str, pattern: str | None) -> None:
    tiles = []
    for i in range(WORD_LENGTH):
        letter = letters[i] if i < len(letters) else ""
        if pattern is None or not letter:
            tiles.append(f'<div class="wordle-tile empty">{letter}</div>')
        else:
            color = TILE_COLORS[pattern[i]]
            tiles.append(
                f'<div class="wordle-tile" style="background:{color};">{letter}</div>'
            )
    st.markdown(f'<div class="wordle-row">{"".join(tiles)}</div>', unsafe_allow_html=True)


def render_board(guess_history: list[tuple[str, str]]) -> None:
    for guess, pattern in guess_history:
        render_row(guess, pattern)
    for _ in range(MAX_GUESSES - len(guess_history)):
        render_row("", None)


def init_state(guesses: set[str]) -> None:
    st.session_state.setdefault("secret", None)
    st.session_state.setdefault("guess_history", [])
    st.session_state.setdefault("candidates", list(guesses))
    st.session_state.setdefault("surv", 1.0)
    st.session_state.setdefault("status", "playing")  # playing, won, lost
    st.session_state.setdefault("error", None)
    st.session_state.setdefault("stats_history", [])


def reset_game(guesses: set[str]) -> None:
    st.session_state.secret = None
    st.session_state.guess_history = []
    st.session_state.candidates = list(guesses)
    st.session_state.surv = 1.0
    st.session_state.status = "playing"
    st.session_state.error = None
    st.session_state.stats_history = []


def render_stats_history(stats_history: list[dict]) -> None:
    if not stats_history:
        return
    rows = []
    for rec in stats_history:
        naive_cell = f"1/{rec['n']} ({rec['naive_p']:.1%})"
        informed_cell = f"{rec['informed_p']:.1%}" if rec["informed_p"] is not None else "&mdash;"
        rows.append(
            f"<tr><td>{rec['turn']}</td><td>{rec['n']}</td><td>{naive_cell}</td>"
            f"<td>{informed_cell}</td><td>{rec['solved_by_now']:.1%}</td></tr>"
        )
    st.markdown(
        '<div class="stats-history-wrap"><table class="stats-history"><thead><tr>'
        "<th>Guess</th><th>Remaining</th><th>Naive</th><th>Informed</th><th>Solved by now</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    # Every turn's word list, once it was small enough to show, stays
    # browsable here rather than disappearing once you guess again.
    for rec in stats_history:
        if rec["candidates"] is not None:
            render_candidate_list(rec["candidates"], label=f"Guess {rec['turn']}")


def render_candidate_list(candidates: list[str], label: str | None = None) -> None:
    chips = "".join(f'<div class="candidate-chip">{word}</div>' for word in sorted(candidates))
    prefix = f"{label} — " if label else ""
    with st.expander(f"{prefix}See the {len(candidates)} possible words"):
        st.markdown(f'<div class="candidate-grid">{chips}</div>', unsafe_allow_html=True)


def main() -> None:
    inject_css()
    st.markdown('<div class="wordle-title">Wordle Probability Tracker</div>', unsafe_allow_html=True)

    guesses = set(load_word_list(DATA_DIR / "guesses.txt"))
    init_state(guesses)

    with st.sidebar:
        st.header("Settings")
        mode = st.radio("Probability model", ["naive", "both", "informed"], index=0)
        if st.button("New game", use_container_width=True):
            reset_game(guesses)
            st.rerun()

    if st.session_state.secret is None:
        st.write("Enter the secret word to track odds against as you guess.")
        with st.form("secret_form"):
            secret_input = st.text_input("Secret word", max_chars=WORD_LENGTH).strip().lower()
            submitted = st.form_submit_button("Start")
        if submitted:
            if len(secret_input) != WORD_LENGTH or not secret_input.isalpha():
                st.error(f"Must be a {WORD_LENGTH}-letter word.")
            elif secret_input not in guesses:
                st.error(f"'{secret_input}' isn't in the word list.")
            else:
                st.session_state.secret = secret_input
                st.rerun()
        return

    secret = st.session_state.secret
    guess_history = st.session_state.guess_history
    turn = len(guess_history) + 1

    render_board(guess_history)

    n = len(st.session_state.candidates)
    naive_p = naive_probability(n) if n > 0 else 0.0
    skip_informed = turn == 1
    informed_p = None
    if st.session_state.status == "playing" and n > 0 and mode in ("informed", "both") and not skip_informed:
        informed_p = informed_probability(st.session_state.candidates)

    # Every turn's odds stay visible here once played, instead of being
    # overwritten by the next turn's numbers.
    render_stats_history(st.session_state.stats_history)

    if st.session_state.status == "playing":
        st.caption(f"Guess {turn} odds")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">Remaining candidates</div>'
                f'<div class="stat-value">{n}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">Solved by now</div>'
                f'<div class="stat-value">{(1 - st.session_state.surv):.1%}</div></div>',
                unsafe_allow_html=True,
            )

        if mode in ("naive", "both") or (mode == "informed" and skip_informed):
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">P(correct) &mdash; naive</div>'
                f'<div class="stat-value">1/{n} ({naive_p:.1%})</div></div>',
                unsafe_allow_html=True,
            )
        if informed_p is not None:
            st.markdown(
                f'<div class="stat-box"><div class="stat-label">P(correct) &mdash; informed</div>'
                f'<div class="stat-value">{informed_p:.1%}</div></div>',
                unsafe_allow_html=True,
            )
        elif mode in ("informed", "both") and skip_informed:
            st.caption("Informed odds skipped on the first guess (no info yet) -- using naive.")

        if 0 < n <= 50:
            render_candidate_list(st.session_state.candidates, label=f"Guess {turn} (current)")

    if st.session_state.status == "won":
        st.markdown(
            f'<div class="win-banner">Solved in {turn - 1} guess{"es" if turn - 1 != 1 else ""}!</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.status == "lost":
        st.markdown(
            f'<div class="lose-banner">Out of guesses. The word was {secret.upper()}.</div>',
            unsafe_allow_html=True,
        )
    else:
        with st.form("guess_form", clear_on_submit=True):
            guess_input = st.text_input(f"Guess {turn}", max_chars=WORD_LENGTH)
            submitted = st.form_submit_button("Submit guess")
        if submitted:
            guess = guess_input.strip().lower()
            if len(guess) != WORD_LENGTH or not guess.isalpha():
                st.session_state.error = f"Must be a {WORD_LENGTH}-letter word."
            elif guess not in guesses:
                st.session_state.error = f"'{guess}' isn't in the word list."
            else:
                st.session_state.error = None
                pattern = compute_feedback(guess, secret)
                st.session_state.guess_history.append((guess, pattern))
                won = guess == secret

                h = informed_p if informed_p is not None else naive_p
                st.session_state.surv = 0.0 if won else st.session_state.surv * (1 - h)
                st.session_state.stats_history.append(
                    {
                        "turn": turn,
                        "n": n,
                        "naive_p": naive_p,
                        "informed_p": informed_p,
                        "solved_by_now": 1 - st.session_state.surv,
                        "candidates": list(st.session_state.candidates) if n <= 50 else None,
                    }
                )

                if won:
                    st.session_state.status = "won"
                elif turn == MAX_GUESSES:
                    st.session_state.status = "lost"
                else:
                    st.session_state.candidates = filter_candidates(
                        st.session_state.candidates, st.session_state.guess_history
                    )
            st.rerun()

    if st.session_state.error:
        st.error(st.session_state.error)


if __name__ == "__main__":
    main()
