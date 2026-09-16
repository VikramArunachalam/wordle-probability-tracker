"""Compute Wordle-style green/yellow/gray feedback for a guess against an answer."""

from collections import Counter

GREEN = "G"
YELLOW = "Y"
GRAY = "X"


def compute_feedback(guess: str, answer: str) -> str:
    """Return a 5-character pattern of G/Y/X for `guess` scored against `answer`.

    Standard Wordle duplicate-letter handling: greens are resolved first and
    consume a copy of that letter from the answer's remaining pool, so a
    repeated guess letter only gets yellow for copies still unaccounted for.
    """
    if len(guess) != len(answer):
        raise ValueError("guess and answer must be the same length")

    pattern = [GRAY] * len(guess)
    remaining = Counter(answer)

    for i, letter in enumerate(guess):
        if letter == answer[i]:
            pattern[i] = GREEN
            remaining[letter] -= 1

    for i, letter in enumerate(guess):
        if pattern[i] == GREEN:
            continue
        if remaining[letter] > 0:
            pattern[i] = YELLOW
            remaining[letter] -= 1

    return "".join(pattern)
