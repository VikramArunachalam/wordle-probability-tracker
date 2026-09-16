from wordle_tracker.candidates import filter_candidates
from wordle_tracker.feedback import compute_feedback

WORDS = ["crane", "trace", "react", "cater", "grape", "plane", "shale", "crime"]


def test_no_history_returns_everything():
    assert filter_candidates(WORDS, []) == WORDS


def test_single_guess_narrows_to_consistent_words():
    secret = "grape"
    pattern = compute_feedback("crane", secret)
    result = filter_candidates(WORDS, [("crane", pattern)])
    assert result == [w for w in WORDS if compute_feedback("crane", w) == pattern]
    assert "grape" in result


def test_multiple_guesses_compound_narrowing():
    secret = "grape"
    history = []
    for guess in ["crane", "plane"]:
        history.append((guess, compute_feedback(guess, secret)))
    result = filter_candidates(WORDS, history)
    assert "grape" in result
    for word in result:
        assert all(compute_feedback(g, word) == p for g, p in history)


def test_true_answer_always_survives_its_own_feedback():
    secret = "shale"
    history = [(g, compute_feedback(g, secret)) for g in ["crime", "grape", "trace"]]
    result = filter_candidates(WORDS, history)
    assert secret in result


def test_feedback_can_eliminate_all_but_the_answer():
    secret = "crime"
    history = [(g, compute_feedback(g, secret)) for g in WORDS if g != secret]
    result = filter_candidates(WORDS, history)
    assert result == [secret]


def test_duplicate_letter_feedback_narrows_correctly():
    # 'llama' vs secret 'allot' -> YGYXX (see test_feedback.py); only words
    # producing that exact pattern against this guess should survive.
    pool = ["allot", "llama", "atoll", "small", "local"]
    secret = "allot"
    pattern = compute_feedback("llama", secret)
    result = filter_candidates(pool, [("llama", pattern)])
    assert result == [w for w in pool if compute_feedback("llama", w) == pattern]
    assert "allot" in result
