from stats import wilson_ci


def test_wilson_ci_zero_n_returns_none():
    assert wilson_ci(0, 0) is None


def test_wilson_ci_50_of_100_brackets_50_percent():
    lo, hi = wilson_ci(50, 100)
    assert 39.0 < lo < 41.0
    assert 59.0 < hi < 61.0


def test_wilson_ci_1_of_1_does_not_return_100_100():
    lo, hi = wilson_ci(1, 1)
    assert lo < 100.0
    assert hi == 100.0  # upper bound *can* hit 100 at p=1
    assert lo < 50.0    # lower bound must be well below 100


def test_wilson_ci_returns_tuple_rounded_to_one_decimal():
    lo, hi = wilson_ci(7, 18)
    # Both values should have at most 1 decimal place
    assert lo == round(lo, 1)
    assert hi == round(hi, 1)


def test_wilson_ci_ordering():
    lo, hi = wilson_ci(11, 18)
    assert lo < hi
