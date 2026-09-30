"""Vectorized (numpy) batch computation of Wordle feedback and 'opening score'.

Mirrors the sequential green-then-yellow duplicate-letter algorithm in
feedback.compute_feedback exactly, but evaluates one guess against an array
of candidates with numpy vector ops instead of a Python loop per candidate.
Only worth the extra complexity because the full post-game analysis scores
every word in the ~13k-word guess list against every remaining candidate at
each turn -- see probability.py's pure-Python version for the O(n^2)
single-guess case that stays fast enough without this.
"""

import random
import time

import numpy as np

from wordle_tracker.candidates import filter_candidates

WORD_LENGTH = 5
ALPHABET_SIZE = 26
GRAY, YELLOW, GREEN = 0, 1, 2


def words_to_array(words: list[str]) -> np.ndarray:
    """(len(words), WORD_LENGTH) int16 array of letter codes 0-25."""
    flat = np.frombuffer("".join(words).encode("ascii"), dtype=np.uint8)
    return (flat.reshape(len(words), WORD_LENGTH).astype(np.int16) - ord("a"))


def letter_counts(candidates_arr: np.ndarray) -> np.ndarray:
    """(C, 26) count of each letter per candidate word."""
    c = candidates_arr.shape[0]
    counts = np.zeros((c, ALPHABET_SIZE), dtype=np.int16)
    rows = np.arange(c)
    for k in range(WORD_LENGTH):
        np.add.at(counts, (rows, candidates_arr[:, k]), 1)
    return counts


def _feedback_codes(
    guess_arr: np.ndarray, candidates_arr: np.ndarray, cand_counts: np.ndarray
) -> np.ndarray:
    """(C,) array of base-3 feedback-pattern codes for guess_arr against each candidate."""
    c = candidates_arr.shape[0]
    green = candidates_arr == guess_arr[None, :]  # (C, 5) bool

    green_counts = np.zeros((c, ALPHABET_SIZE), dtype=np.int16)
    for k in range(WORD_LENGTH):
        green_counts[:, guess_arr[k]] += green[:, k]

    remaining = cand_counts - green_counts  # (C, 26), letters left to match per candidate

    pattern = np.where(green, GREEN, GRAY).astype(np.int8)  # (C, 5)
    for k in range(WORD_LENGTH):
        letter = int(guess_arr[k])
        not_green = ~green[:, k]
        is_yellow = not_green & (remaining[:, letter] > 0)
        pattern[is_yellow, k] = YELLOW
        remaining[is_yellow, letter] -= 1

    codes = np.zeros(c, dtype=np.int32)
    for k in range(WORD_LENGTH):
        codes = codes * 3 + pattern[:, k]
    return codes


def actual_remaining(
    guess_arr: np.ndarray, candidates_arr: np.ndarray, cand_counts: np.ndarray, secret_idx: int
) -> int:
    """Candidates actually left after guessing this word, given the real secret.

    Partitions the candidates by the feedback pattern this guess would
    produce against each of them, then returns the size of whichever
    partition the real secret (at secret_idx in candidates_arr) actually
    falls into -- i.e. what would really happen, not an average over every
    hypothetical secret. Lower is better; 1 is the best possible outcome.

    This is deliberately not an expected-value metric. Guessing the literal
    correct answer always lands the secret in a singleton bucket (itself),
    so it always scores the best possible 1 here -- unlike an
    expectation-over-all-candidates metric, which can rate a "scout" word
    higher if the real guess happens to be bad at telling the *other*,
    wrong candidates apart from each other.
    """
    codes = _feedback_codes(guess_arr, candidates_arr, cand_counts)
    bucket_sizes = np.bincount(codes, minlength=3**WORD_LENGTH)
    return int(bucket_sizes[codes[secret_idx]])


def opening_scores(
    guess_words: list[str], candidate_words: list[str], secret_idx: int
) -> dict[str, int]:
    """Candidates actually left behind by every word in guess_words, given the real secret."""
    guesses_arr = words_to_array(guess_words)
    candidates_arr = words_to_array(candidate_words)
    cand_counts = letter_counts(candidates_arr)

    scores = {}
    for i, word in enumerate(guess_words):
        scores[word] = actual_remaining(guesses_arr[i], candidates_arr, cand_counts, secret_idx)
    return scores


def prepare_turns(
    guess_history: list[tuple[str, str]], all_words: list[str], secret: str
) -> list[dict]:
    """Reconstruct the pre-guess candidate set for every turn, including turn 1."""
    turns = []
    for t in range(1, len(guess_history) + 1):
        candidates = filter_candidates(all_words, guess_history[: t - 1])
        guess, pattern = guess_history[t - 1]
        n_after = len(filter_candidates(candidates, [(guess, pattern)]))
        turns.append(
            {
                "turn": t,
                "guess": guess,
                "candidates": candidates,
                "n": len(candidates),
                "n_after": n_after,
                "secret_idx": candidates.index(secret),
            }
        )
    return turns


def estimate_seconds(turns: list[dict], all_words: list[str], sample_size: int = 300) -> float:
    """Extrapolate full-analysis runtime from timing a small random sample of guesses.

    Cost per turn is dominated by one O(n) vector op per guess word scored,
    so timing a sample and scaling by (len(all_words) / sample_size) tracks
    actual runtime closely regardless of machine speed -- see the
    calibration check this was validated against before use.
    """
    sample = random.sample(all_words, min(sample_size, len(all_words)))
    total = 0.0
    for rec in turns:
        t0 = time.perf_counter()
        opening_scores(sample, rec["candidates"], rec["secret_idx"])
        t1 = time.perf_counter()
        total += (t1 - t0) * (len(all_words) / len(sample))
    return total


def run_full_analysis(turns: list[dict], all_words: list[str], progress_cb=None) -> list[dict]:
    """Score every guess word against every turn's actual candidate set.

    For each turn, returns the average and median candidates-actually-left
    (given the real secret) across every word in all_words, plus the
    percentile rank of the guess actually made -- the fraction of the field
    that would have left *more* candidates behind (done worse) than it did.
    """
    results = []
    for i, rec in enumerate(turns):
        scores = opening_scores(all_words, rec["candidates"], rec["secret_idx"])
        actual = scores[rec["guess"]]
        values = np.fromiter(scores.values(), dtype=np.float64, count=len(scores))
        avg = float(values.mean())
        median = float(np.median(values))
        percentile = float((values >= actual).mean() * 100)
        results.append(
            {
                "turn": rec["turn"],
                "guess": rec["guess"],
                "n": rec["n"],
                "n_after": rec["n_after"],
                "avg_remaining": avg,
                "median_remaining": median,
                "percentile": percentile,
            }
        )
        if progress_cb:
            progress_cb((i + 1) / len(turns))
    return results
