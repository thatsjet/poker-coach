"""Tests for parse_user_action in main module."""

from poker_coach.main import parse_user_action

STATE = {
    "current_bet": 20,
    "min_raise": 20,
    "hero_stack": 500,
    "pot": 85,
}


class TestParseUserAction:
    def test_fold(self):
        assert parse_user_action("fold", STATE) == ("fold", 0)

    def test_check(self):
        assert parse_user_action("check", STATE) == ("check", 0)

    def test_call(self):
        assert parse_user_action("call", STATE) == ("call", 20)

    def test_raise_to_amount(self):
        assert parse_user_action("raise to 60", STATE) == ("raise", 60)

    def test_bet_amount(self):
        assert parse_user_action("bet 40", STATE) == ("raise", 40)

    def test_bet_the_pot(self):
        action, amount = parse_user_action("bet the pot", STATE)
        assert action == "raise"
        assert amount == 85

    def test_raise_pot(self):
        action, amount = parse_user_action("raise pot", STATE)
        assert action == "raise"
        assert amount == 85

    def test_bet_half_pot(self):
        action, amount = parse_user_action("bet half pot", STATE)
        assert action == "raise"
        assert amount == 42

    def test_bet_2_3_pot(self):
        action, amount = parse_user_action("bet 2/3 pot", STATE)
        assert action == "raise"
        assert amount == 56

    def test_bet_3_4_pot(self):
        action, amount = parse_user_action("bet 3/4 pot", STATE)
        assert action == "raise"
        assert amount == 63

    def test_bet_1_2_pot(self):
        action, amount = parse_user_action("bet 1/2 pot", STATE)
        assert action == "raise"
        assert amount == 42

    def test_all_in(self):
        action, amount = parse_user_action("all in", STATE)
        assert action == "raise"
        assert amount == 520

    def test_shove(self):
        action, amount = parse_user_action("shove", STATE)
        assert action == "raise"
        assert amount == 520
