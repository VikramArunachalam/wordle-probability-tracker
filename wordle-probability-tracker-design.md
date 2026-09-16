# Wordle Probability Tracker — Design Plan

## Goal

An interactive tool where the user sets the secret answer, enters guesses one at a time, and after each guess sees the probability of guessing correctly on the next attempt (and each attempt after that), based on the guesses made so far.

This is scoped narrowly: no strategy engine, no opener sweeps, no mode comparisons. Just guess -> feedback -> narrowed candidate set -> probability.

## User flow

1. User enters the secret word (5 letters, must be a real word).
2. Loop, up to 6 times:
   - User enters a guess.
   - Tool computes the feedback pattern (green / yellow / gray) against the secret word.
   - Tool filters the candidate list to words consistent with all feedback so far.
   - Tool prints the probability table (below).
   - If guess == secret word, stop and report success.
3. If 6 guesses used without success, report failure.

## Probability model

At any point, let `S` = current candidate set (words consistent with all feedback so far), `N = |S|`.

**Naive probability (v1, default):** assumes the next guess is picked uniformly at random from `S`.

```
P(correct on next guess) = 1 / N
```

**Informed probability (v2, stretch goal):** accounts for the fact that a well-chosen next guess narrows things further before you're forced to commit. Requires computing, for each candidate word in `S`, how it would partition `S` by feedback pattern, and finding the singleton-bucket fraction for the best guess:

```
h = (# words in S that would be uniquely identified by the best next guess) / N
```

`h` is always >= `1/N`, since an optimal guess does at least as well as a random pick. Both numbers are worth showing side by side once v2 exists — `1/N` is "if you just guess something," `h` is "if you guess well."

**Derived values shown each turn (both v1 and v2 use the same shape, just different `h`):**

- `P(win at this guess)` — probability of success on the guess about to be entered
- `Surv` — probability of having survived to this point without winning (running product of `1 - h` from prior guesses)
- Cumulative solve probability so far (`1 - Surv`)
- Remaining candidates `N`

**Display toggle:** once informed probability exists, a `--mode` flag controls what's shown — `naive`, `informed`, or `both` (default `both`, side by side). This also lets the user skip the expensive turn-1 informed calculation by running in `naive` mode when they just want a fast answer.

## Feedback rules (must get this right — common bug source)

Standard Wordle duplicate-letter handling:
1. First pass: mark exact position matches green.
2. Second pass, on remaining letters only: mark yellow if the letter appears elsewhere in the answer, but don't double-count a letter already fully accounted for by earlier greens/yellows.
3. Everything else gray.

Write this as an isolated, tested function before anything else — it's the foundation everything downstream depends on.

## Data requirements

- **Answer list**: valid secret words (~2,300 words, NYT Wordle answer list).
- **Guess list**: all valid guesses, larger list (~13,000 words). Needed so the user can enter any real word as a guess, not just possible answers.
- Source: bundle a static word list file (JSON or plain text, one word per line) rather than fetching at runtime.

## Architecture (suggested)

```
wordle_tracker/
  feedback.py      # compute_feedback(guess, answer) -> pattern
  candidates.py     # filter_candidates(word_list, guess_history) -> list
  probability.py    # naive_probability(n), informed_probability(candidates) [v2]
  cli.py            # main loop: I/O, orchestration
  data/
    answers.txt
    guesses.txt
```

Keep each module doing one thing. `probability.py` should take a candidate list in and return numbers out — no I/O, no printing, so it's easy to test independently of the CLI.

## Example output per turn

```
Guess 3: CRANE
Feedback: gray, gray, yellow, gray, green

Remaining candidates: 14
P(correct on next guess): 1/14 (7.1%)
Probability you've solved it by now: 61%
```

## Build phases

1. **Feedback engine** — `compute_feedback`, with tests covering duplicate-letter edge cases.
2. **Candidate filter** — apply accumulated feedback to narrow the word list.
3. **Naive probability + CLI loop** — wire up the full user flow with `1/N` probability. This is a usable v1 on its own.
4. **Informed probability** — add the best-guess partition calculation, plus the `--mode` toggle so naive and informed can be shown separately or together.

## Out of scope for this tool

- Auto-suggesting the best next guess (entropy/minimax strategy engine)
- Comparing strategies or starting words
- Hard mode vs. regular mode
- Multi-word fixed openers
- Any simulation over the full answer list (this tool tracks one live game against one known answer)

## Resolved decisions

- **Runtime:** Python
- **Word lists:** bundle static NYT-style answer/guess list files under `data/` (source to be pulled in at implementation time)
- **Probability modes:** build both naive and informed, switchable via `--mode` flag (see Display toggle above); naive ships first (phase 3), informed added phase 4
