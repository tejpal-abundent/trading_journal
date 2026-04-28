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


from stats import confidence_label


def test_confidence_label_boundaries():
    # Per the video: <30 noise, <100 noisy, <500 reasonable, <1000 strong, >=1000 conviction
    assert confidence_label(0) == "Noise"
    assert confidence_label(29) == "Noise"
    assert confidence_label(30) == "Noisy"
    assert confidence_label(99) == "Noisy"
    assert confidence_label(100) == "Reasonable"
    assert confidence_label(499) == "Reasonable"
    assert confidence_label(500) == "Strong"
    assert confidence_label(999) == "Strong"
    assert confidence_label(1000) == "Conviction"
    assert confidence_label(10_000) == "Conviction"


from stats import expected_max_loss_streak


def test_expected_streak_zero_n():
    assert expected_max_loss_streak(0.5, 0) == 0


def test_expected_streak_p_loss_zero():
    assert expected_max_loss_streak(0.0, 100) == 0


def test_expected_streak_p_loss_one():
    assert expected_max_loss_streak(1.0, 100) == 0  # degenerate, return 0


def test_expected_streak_50_50_100_trades():
    # Schilling: log(100*0.5)/log(2) = log(50)/log(2) ≈ 5.64 → 6
    result = expected_max_loss_streak(0.5, 100)
    assert 5 <= result <= 7


def test_expected_streak_returns_at_least_one():
    # Even tiny n should give >=1 if math is degenerate-ish
    assert expected_max_loss_streak(0.5, 2) >= 1
