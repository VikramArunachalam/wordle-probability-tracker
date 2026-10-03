# Wordle Probability Tracker

Track your odds of solving as you play: enter a secret word, then enter guesses
one at a time. After each guess the tool shows the remaining candidate count
and the probability of solving on the next attempt.

## Usage

```
python -m wordle_tracker.cli --mode both
```

`--mode` controls which probability model(s) are shown each turn:
- `naive` — `1/N`, assuming the next guess is picked at random from the remaining candidates. Fast.
- `informed` — best-case odds if the next guess is chosen optimally (partitions candidates by feedback pattern). O(N^2) in the candidate count; skipped on turn 1 (no feedback yet to narrow anything, so the first guess is effectively random) and falls back to naive there.
- `both` (default) — show both side by side.

## Tests

```
pip install pytest
pytest tests/
```

## Word lists

`wordle_tracker/data/guesses.txt` (14,855 words, from
[dracos/valid-wordle-words.txt](https://gist.github.com/dracos/dd0668f281e685bad51479e5acaadb93),
kept in sync with NYT's live valid-guess list) is used both to validate what
you can type and as the candidate pool for probability calculations — since
a player has no way of knowing the secret is actually drawn from a smaller
curated answer list, the odds shown treat every valid word as equally
plausible.
`wordle_tracker/data/answers.txt` (2,315 words, the actual NYT answer list)
ships alongside it but isn't used by the tracker. To use a different list,
replace `guesses.txt` (one lowercase 5-letter word per line).
