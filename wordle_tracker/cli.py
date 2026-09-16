"""Interactive Wordle probability tracker: guess -> feedback -> narrowed candidates -> probability."""

import argparse
from pathlib import Path

from wordle_tracker.candidates import filter_candidates
from wordle_tracker.feedback import GREEN, YELLOW, compute_feedback
from wordle_tracker.probability import informed_probability, naive_probability

DATA_DIR = Path(__file__).parent / "data"
MAX_GUESSES = 6
WORD_LENGTH = 5

FEEDBACK_NAMES = {GREEN: "green", YELLOW: "yellow"}


def load_word_list(path: Path) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def describe_feedback(pattern: str) -> str:
    return ", ".join(FEEDBACK_NAMES.get(letter, "gray") for letter in pattern)


def prompt_word(label: str, valid_words: set[str]) -> str:
    while True:
        word = input(f"{label}: ").strip().lower()
        if len(word) != WORD_LENGTH or not word.isalpha():
            print(f"  -> must be a {WORD_LENGTH}-letter word.")
            continue
        if word not in valid_words:
            print(f"  -> '{word}' isn't in the word list.")
            continue
        return word


def run_game(secret: str, guesses: set[str], mode: str) -> None:
    candidates = list(guesses)
    surv = 1.0
    guess_history: list[tuple[str, str]] = []

    for turn in range(1, MAX_GUESSES + 1):
        n = len(candidates)
        naive_p = naive_probability(n)
        # Turn 1 has no feedback yet to inform a choice, so every word is equally
        # good -- skip the expensive O(n^2) computation and fall back to naive.
        skip_informed = turn == 1
        informed_p = (
            informed_probability(candidates)
            if mode in ("informed", "both") and not skip_informed
            else None
        )

        guess = prompt_word(f"Guess {turn}", guesses)
        pattern = compute_feedback(guess, secret)
        guess_history.append((guess, pattern))
        won = guess == secret

        h = informed_p if informed_p is not None else naive_p
        surv = 0.0 if won else surv * (1 - h)

        print(f"Feedback: {describe_feedback(pattern)}")
        print(f"Remaining candidates: {n}")
        if mode in ("naive", "both") or (mode == "informed" and skip_informed):
            print(f"P(correct on this guess) [naive]:    1/{n} ({naive_p:.1%})")
        if informed_p is not None:
            print(f"P(correct on this guess) [informed]: {informed_p:.1%}")
        elif mode in ("informed", "both") and skip_informed:
            print("P(correct on this guess) [informed]: skipped on first guess (no info yet)")
        print(f"Probability you've solved it by now: {1 - surv:.1%}")
        print()

        if won:
            print(f"Solved in {turn} guess{'es' if turn != 1 else ''}!")
            return

        candidates = filter_candidates(candidates, guess_history)

    print(f"Out of guesses. The word was: {secret}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wordle probability tracker")
    parser.add_argument(
        "--mode",
        choices=["naive", "informed", "both"],
        default="both",
        help="which probability model(s) to show each turn (default: both)",
    )
    args = parser.parse_args()

    guesses = set(load_word_list(DATA_DIR / "guesses.txt"))

    print("Wordle Probability Tracker")
    secret = prompt_word("Secret word", guesses)
    print()
    run_game(secret, guesses, args.mode)


if __name__ == "__main__":
    main()
