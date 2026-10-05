"""Fetch the day's official NYT Wordle answer.

Reads NYT's public, undocumented daily-puzzle JSON endpoint -- the same one
many open-source Wordle tools use. No authentication required, but since
it's undocumented, NYT could change or remove its shape without notice;
every call here is defensive and returns None on any failure rather than
raising, so a broken fetch just hides the "play today's Wordle" option.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

# The daily puzzle changes at midnight US Eastern time, not the server's own
# timezone (Streamlit Cloud runs UTC) -- using the wrong clock would show
# the previous or next day's word for several hours around midnight.
NYT_TIMEZONE = ZoneInfo("America/New_York")
WORD_LENGTH = 5


def todays_date() -> date:
    """Today's Wordle puzzle date, per NYT's own Eastern-time day boundary."""
    return datetime.now(NYT_TIMEZONE).date()


def fetch_solution(puzzle_date: date) -> str | None:
    """The puzzle_date's answer, or None if unreachable or malformed.

    Doesn't check the word against our own guesses.txt -- callers should do
    that themselves (and treat a mismatch the same as a failed fetch), since
    that keeps this function cacheable on the date alone rather than also
    hashing the whole word list on every call.
    """
    url = f"https://www.nytimes.com/svc/wordle/v2/{puzzle_date.isoformat()}.json"
    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        solution = response.json()["solution"].strip().lower()
    except Exception:
        return None
    if len(solution) != WORD_LENGTH or not solution.isalpha():
        return None
    return solution
