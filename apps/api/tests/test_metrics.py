"""Unit tests for the pure metric functions.

No database, no I/O, no config. These are the fast ones - if the arithmetic is
wrong, everything downstream is wrong, and this file finds it in milliseconds.
"""

from __future__ import annotations

import pytest

from slotsight.analytics import metrics as mx


class TestToDollars:
    def test_converts_cents(self) -> None:
        assert mx.to_dollars(12_345) == 123.45

    def test_rounds_to_cent(self) -> None:
        assert mx.to_dollars(100.4) == 1.0

    def test_zero(self) -> None:
        assert mx.to_dollars(0) == 0.0


class TestWpupd:
    def test_basic(self) -> None:
        # $3,000 won over 30 days == $100/day
        assert mx.wpupd(300_000, 30) == 100.0

    def test_zero_days_is_zero_not_error(self) -> None:
        """A machine with no recorded days is a real state, not an exception."""
        assert mx.wpupd(500_000, 0) == 0.0

    def test_negative_days_guarded(self) -> None:
        assert mx.wpupd(500_000, -5) == 0.0

    def test_machine_can_lose_money(self) -> None:
        assert mx.wpupd(-50_000, 10) == -50.0


class TestHoldPct:
    def test_basic(self) -> None:
        assert mx.hold_pct(8_750, 100_000) == pytest.approx(0.0875)

    def test_dark_machine_returns_zero(self) -> None:
        """No coin-in is a legitimate state across hundreds of machines."""
        assert mx.hold_pct(0, 0) == 0.0

    def test_negative_coin_in_guarded(self) -> None:
        assert mx.hold_pct(100, -5) == 0.0


class TestIndexToAverage:
    def test_exactly_average_is_one(self) -> None:
        assert mx.index_to_average(250.0, 250.0) == 1.0

    def test_twenty_percent_below(self) -> None:
        assert mx.index_to_average(200.0, 250.0) == pytest.approx(0.8)

    def test_empty_cohort_returns_zero(self) -> None:
        assert mx.index_to_average(250.0, 0.0) == 0.0


class TestHoldDeviationRatio:
    def test_at_par_is_one(self) -> None:
        assert mx.hold_deviation_ratio(0.0875, 0.0875) == 1.0

    def test_metering_fault_shape(self) -> None:
        """3.4x par is the shape of a bill validator fault, not performance."""
        assert mx.hold_deviation_ratio(0.298, 0.0875) == pytest.approx(3.4, abs=0.05)

    def test_zero_par_guarded(self) -> None:
        assert mx.hold_deviation_ratio(0.1, 0.0) == 0.0


class TestLinearTrendSlope:
    def test_flat_series_is_zero(self) -> None:
        assert mx.linear_trend_slope([5.0] * 10) == pytest.approx(0.0)

    def test_rising_series_is_positive(self) -> None:
        assert mx.linear_trend_slope([1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.0)

    def test_falling_series_is_negative(self) -> None:
        assert mx.linear_trend_slope([4.0, 3.0, 2.0, 1.0]) == pytest.approx(-1.0)

    def test_single_point_is_zero(self) -> None:
        assert mx.linear_trend_slope([7.0]) == 0.0

    def test_empty_is_zero(self) -> None:
        assert mx.linear_trend_slope([]) == 0.0


class TestPctChange:
    def test_increase(self) -> None:
        assert mx.pct_change(110.0, 100.0) == pytest.approx(10.0)

    def test_decrease(self) -> None:
        assert mx.pct_change(90.0, 100.0) == pytest.approx(-10.0)

    def test_zero_previous_guarded(self) -> None:
        assert mx.pct_change(50.0, 0.0) == 0.0


class TestPeerCohortKey:
    def test_same_denom_and_type_share_a_cohort(self) -> None:
        assert mx.peer_cohort_key(1, "video_reel") == mx.peer_cohort_key(1, "video_reel")

    def test_denomination_separates_cohorts(self) -> None:
        """A $5 machine and a penny machine are not peers.

        This is the assertion that encodes the single most important
        judgement call in the analytics: benchmarking across denominations
        just sorts by denomination.
        """
        assert mx.peer_cohort_key(1, "video_reel") != mx.peer_cohort_key(500, "video_reel")

    def test_game_type_separates_cohorts(self) -> None:
        assert mx.peer_cohort_key(1, "video_reel") != mx.peer_cohort_key(1, "video_poker")
