"""Narrow a word list down to candidates consistent with feedback seen so far."""

from wordle_tracker.feedback import compute_feedback


def filter_candidates(word_list: list[str], guess_history: list[tuple[str, str]]) -> list[str]:
    """Return the words in `word_list` consistent with every (guess, pattern) pair.

    A candidate is consistent with a past guess if scoring that guess against
    the candidate (as if the candidate were the answer) reproduces the exact
    feedback pattern that was actually observed.
    """
    survivors = []
    for word in word_list:
        if all(compute_feedback(guess, word) == pattern for guess, pattern in guess_history):
            survivors.append(word)
    return survivors
