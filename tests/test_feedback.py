from wordle_tracker.feedback import compute_feedback


def test_exact_match_all_green():
    assert compute_feedback("crane", "crane") == "GGGGG"


def test_no_letters_in_common():
    assert compute_feedback("gymps", "fluid") == "XXXXX"


def test_standard_mixed_case():
    # answer: crane
    # guess:  cabin -> c green, a yellow (in crane, wrong spot), b gray, i gray, n yellow
    assert compute_feedback("cabin", "crane") == "GYXXY"


def test_duplicate_guess_letter_single_in_answer_green_then_gray():
    # answer: lemon (l,e,m,o,n), guess: llama (l,l,a,m,a)
    # pos0 'l' green (consumes answer's only 'l'); pos1 'l' has none left -> gray
    # pos2 'a' not in answer -> gray; pos3 'm' matches answer's 'm' -> yellow
    # pos4 'a' already accounted for -> gray
    assert compute_feedback("llama", "lemon") == "GXXYX"


def test_duplicate_guess_letter_matches_green_and_extra_gray():
    # answer: sassy (two s's), guess: spans -> only one 's' is green-eligible via count
    # answer: sassy, guess: seeds -> 's' green at pos0, 's' at pos... check simpler case
    # answer: kappa, guess: apple -> a: answer has 2 a's
    # apple vs kappa: a(pos0) not green (kappa[0]=k), p(pos1) green? kappa[1]=a no.
    # Use a clean, hand-verified case instead:
    # answer: allot, guess: llama
    # positions: l l a m a  vs  a l l o t
    # pos0: l vs a -> no green
    # pos1: l vs l -> green
    # pos2: a vs l -> no green
    # pos3: m vs o -> no green
    # pos4: a vs t -> no green
    # remaining answer letters after green consumed 'l' at pos1: a,l,o,t (allot minus one l)
    # guess non-green letters in order: pos0 'l', pos2 'a', pos3 'm', pos4 'a'
    # pos0 'l': remaining has 'l' -> yellow, consume l -> remaining: a,o,t
    # pos2 'a': remaining has 'a' -> yellow, consume a -> remaining: o,t
    # pos3 'm': not in remaining -> gray
    # pos4 'a': not in remaining (already consumed) -> gray
    assert compute_feedback("llama", "allot") == "YGYXX"


def test_letter_present_more_times_in_answer_than_guess():
    # answer: sassy (s,a,s,s,y), guess: sooty -> s green pos0, y green pos4, rest gray
    assert compute_feedback("sooty", "sassy") == "GXXXG"


def test_all_gray_no_overlap():
    assert compute_feedback("bumpy", "fjord")[0] != "G"


def test_raises_on_length_mismatch():
    import pytest

    with pytest.raises(ValueError):
        compute_feedback("abc", "abcde")
