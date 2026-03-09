"""Tests for Player and GameState."""

import random

from poker_coach.engine.player import Player
from poker_coach.engine.game_state import GameState


class TestPlayer:
    def test_create_player(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=500)
        assert p.seat == 0
        assert p.stack == 500
        assert p.is_active is True
        assert p.hole_cards == []

    def test_post_blind(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=500)
        p.post_blind(10)
        assert p.stack == 490
        assert p.current_bet == 10

    def test_post_blind_all_in(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=5)
        actual = p.post_blind(10)
        assert actual == 5
        assert p.stack == 0
        assert p.current_bet == 5
        assert p.is_all_in is True

    def test_place_bet(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=500)
        actual = p.place_bet(100)
        assert actual == 100
        assert p.stack == 400
        assert p.current_bet == 100

    def test_place_bet_all_in(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=50)
        actual = p.place_bet(100)
        assert actual == 50
        assert p.stack == 0
        assert p.is_all_in is True

    def test_fold(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=500)
        p.fold()
        assert p.has_folded is True
        assert p.is_active is False

    def test_reset_for_new_hand(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=500)
        p.place_bet(100)
        p.fold()
        p.reset_for_new_hand()
        assert p.hole_cards == []
        assert p.current_bet == 0
        assert p.is_active is True
        assert p.has_folded is False
        assert p.is_all_in is False

    def test_reset_for_new_hand_zero_stack(self):
        p = Player(seat=0, name="Hero", archetype="hero", stack=0)
        p.reset_for_new_hand()
        assert p.is_active is False


class TestGameStateSetup:
    def _make_state(self, num_players=6, seed=42):
        players = []
        players.append(Player(seat=0, name="Hero", archetype="hero", stack=500))
        for i in range(1, num_players):
            players.append(
                Player(seat=i, name=f"NPC{i}", archetype="weak", stack=500)
            )
        return GameState(
            players=players,
            small_blind=5,
            big_blind=10,
            rng=random.Random(seed),
        )

    def test_initial_state(self):
        gs = self._make_state()
        assert gs.hand_number == 0
        assert gs.street == "preflop"
        assert gs.pot == 0

    def test_start_hand_deals_cards(self):
        gs = self._make_state()
        gs.start_hand()
        assert gs.hand_number == 1
        for p in gs.players:
            assert len(p.hole_cards) == 2

    def test_start_hand_posts_blinds(self):
        gs = self._make_state()
        gs.start_hand()
        # Button is seat 0, so SB is seat 1, BB is seat 2
        assert gs.players[1].current_bet == 5  # SB
        assert gs.players[2].current_bet == 10  # BB
        assert gs.pot == 15

    def test_start_hand_posts_blinds_two_players(self):
        gs = self._make_state(num_players=2)
        gs.start_hand()
        # 2-player: BTN posts SB, other posts BB
        assert gs.players[0].current_bet == 5  # BTN/SB
        assert gs.players[1].current_bet == 10  # BB
        assert gs.pot == 15

    def test_advance_street_flop(self):
        gs = self._make_state()
        gs.start_hand()
        gs.advance_street()
        assert gs.street == "flop"
        assert len(gs.community_cards) == 3
        # Player bets should be reset
        for p in gs.players:
            assert p.current_bet == 0
        assert gs.current_bet == 0

    def test_advance_street_turn(self):
        gs = self._make_state()
        gs.start_hand()
        gs.advance_street()  # flop
        gs.advance_street()  # turn
        assert gs.street == "turn"
        assert len(gs.community_cards) == 4

    def test_advance_street_river(self):
        gs = self._make_state()
        gs.start_hand()
        gs.advance_street()  # flop
        gs.advance_street()  # turn
        gs.advance_street()  # river
        assert gs.street == "river"
        assert len(gs.community_cards) == 5

    def test_get_active_players(self):
        gs = self._make_state()
        gs.start_hand()
        assert len(gs.get_active_players()) == 6
        gs.players[1].fold()
        assert len(gs.get_active_players()) == 5

    def test_get_positions(self):
        gs = self._make_state()
        positions = gs.get_positions()
        assert len(positions) == 6
        assert positions[0] == "BTN"

    def test_advance_button(self):
        gs = self._make_state()
        assert gs.button_index == 0
        gs.advance_button()
        assert gs.button_index == 1

    def test_to_dict_has_required_keys(self):
        gs = self._make_state()
        gs.start_hand()
        d = gs.to_dict(hero_seat=0)
        assert "hand_number" in d
        assert "street" in d
        assert "hero_cards" in d
        assert "community_cards" in d
        assert "pot" in d
        assert "players" in d
        assert "hero_position" in d
        assert "hero_stack" in d
        assert "current_bet" in d
        assert "min_raise" in d

    def test_to_dict_includes_hero_in_players(self):
        gs = self._make_state()
        gs.start_hand()
        d = gs.to_dict(hero_seat=0)
        hero_entries = [p for p in d["players"] if p["is_hero"]]
        assert len(hero_entries) == 1
        assert hero_entries[0]["seat"] == 0

    def test_current_bet_after_start_hand(self):
        gs = self._make_state()
        gs.start_hand()
        assert gs.current_bet == 10  # big blind
