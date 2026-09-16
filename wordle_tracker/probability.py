"""Probability of solving on the next guess, given the current candidate set.

Pure functions only: candidates/counts in, numbers out. No I/O here so this
stays easy to test and to reuse outside the CLI.
"""

from collections import Counter

from wordle_tracker.feedback import compute_feedback


def naive_probability(n: int) -> float:
    """P(correct on next guess) assuming it's picked uniformly at random from n candidates."""
    if n <= 0:
        raise ValueError("n must be positive")
    return 1 / n


def informed_probability(candidates: list[str]) -> float:
    """Best-case P(correct on next guess) if the next guess is chosen optimally.

    For each candidate acting as a hypothetical guess, partition the
    candidate set by the feedback pattern it would produce against every
    other candidate. A word lands in a singleton bucket if that guess would
    uniquely identify it. Returns the largest singleton-bucket fraction over
    all choices of guess -- i.e. how well the best possible next guess does.

    O(n^2) in len(candidates); candidate sets shrink fast after guess 1, but
    this is why the CLI's `naive` mode exists as a fast path on turn 1.
    """
    n = len(candidates)
    if n <= 0:
        raise ValueError("candidates must be non-empty")
    if n == 1:
        return 1.0

    best_singletons = 0
    for guess in candidates:
        bucket_sizes: Counter[str] = Counter(
            compute_feedback(guess, candidate) for candidate in candidates
        )
        singletons = sum(1 for size in bucket_sizes.values() if size == 1)
        if singletons > best_singletons:
            best_singletons = singletons

    return best_singletons / n
