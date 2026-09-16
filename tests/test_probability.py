import pytest

from wordle_tracker.probability import informed_probability, naive_probability


def test_naive_probability_known_n():
    assert naive_probability(1) == 1.0
    assert naive_probability(4) == 0.25
    assert naive_probability(2314) == pytest.approx(1 / 2314)


def test_naive_probability_rejects_non_positive():
    with pytest.raises(ValueError):
        naive_probability(0)


def test_informed_probability_single_candidate():
    assert informed_probability(["crane"]) == 1.0


def test_informed_probability_at_least_naive():
    candidates = ["crane", "trace", "react", "cater", "grape", "plane", "shale", "crime"]
    n = len(candidates)
    assert informed_probability(candidates) >= naive_probability(n)


def test_informed_probability_rejects_empty():
    with pytest.raises(ValueError):
        informed_probability([])


def test_informed_probability_beats_naive_on_a_separable_set():
    candidates = ["llama", "allot", "atoll", "small", "local"]
    naive = naive_probability(len(candidates))
    informed = informed_probability(candidates)
    assert informed >= naive
    # guessing 'llama' scores each of the other words differently, so the
    # best guess should do strictly better than picking at random.
    assert informed > naive
