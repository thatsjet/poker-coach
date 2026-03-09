"""Tests for position labels and button rotation."""

import pytest

from poker_coach.engine.positions import (
    POSITION_LABELS,
    get_positions,
    rotate_button,
)


class TestPositionLabels:
    def test_all_table_sizes_present(self):
        for size in range(2, 10):
            assert size in POSITION_LABELS

    def test_labels_start_with_btn(self):
        for size, labels in POSITION_LABELS.items():
            assert labels[0] == "BTN"

    def test_labels_length_matches_size(self):
        for size, labels in POSITION_LABELS.items():
            assert len(labels) == size


class TestGetPositions:
    def test_two_players(self):
        positions = get_positions(2, button_index=0)
        assert positions == ["BTN", "BB"]

    def test_three_players(self):
        positions = get_positions(3, button_index=0)
        assert positions == ["BTN", "SB", "BB"]

    def test_six_players(self):
        positions = get_positions(6, button_index=0)
        assert positions == ["BTN", "SB", "BB", "UTG", "HJ", "CO"]

    def test_nine_players(self):
        positions = get_positions(9, button_index=0)
        assert positions == [
            "BTN", "SB", "BB", "UTG", "UTG+1", "MP", "MP+1", "HJ", "CO"
        ]

    def test_button_rotation(self):
        positions = get_positions(6, button_index=1)
        assert positions[1] == "BTN"
        assert positions[2] == "SB"

    def test_button_at_last_seat(self):
        positions = get_positions(6, button_index=5)
        assert positions[5] == "BTN"
        assert positions[0] == "SB"
        assert positions[1] == "BB"

    def test_invalid_num_players_too_small(self):
        with pytest.raises(ValueError):
            get_positions(1, button_index=0)

    def test_invalid_num_players_too_large(self):
        with pytest.raises(ValueError):
            get_positions(10, button_index=0)

    def test_invalid_button_index(self):
        with pytest.raises(ValueError):
            get_positions(6, button_index=6)

    def test_negative_button_index(self):
        with pytest.raises(ValueError):
            get_positions(6, button_index=-1)


class TestRotateButton:
    def test_rotate_button(self):
        assert rotate_button(0, 6) == 1
        assert rotate_button(5, 6) == 0

    def test_rotate_wraps_around(self):
        assert rotate_button(8, 9) == 0

    def test_rotate_middle(self):
        assert rotate_button(3, 6) == 4
