from poker_coach.config import SessionConfig
from poker_coach.game_loop import GameLoop


class TestGameLoop:
    def test_creates_players(self):
        config = SessionConfig(num_players=4, strong_players=1, seed="test123")
        loop = GameLoop(config)
        assert len(loop.game_state.players) == 4
        assert loop.game_state.players[0].archetype == "hero"
        archetypes = [p.archetype for p in loop.game_state.players[1:]]
        assert archetypes.count("strong") == 1
        assert archetypes.count("weak") == 2

    def test_start_hand(self):
        config = SessionConfig(num_players=4, strong_players=1, seed="test123")
        loop = GameLoop(config)
        loop.start_hand()
        assert loop.game_state.hand_number == 1
        for p in loop.game_state.players:
            assert len(p.hole_cards) == 2

    def test_action_order_preflop(self):
        config = SessionConfig(num_players=4, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        order = loop.get_preflop_action_order()
        positions = loop.game_state.get_positions()
        # First to act should NOT be BB, last should be BB
        assert positions[order[-1]] == "BB"

    def test_action_order_postflop(self):
        config = SessionConfig(num_players=4, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        loop.game_state.street = "flop"  # simulate
        order = loop.get_postflop_action_order()
        positions = loop.game_state.get_positions()
        assert positions[order[0]] == "SB"

    def test_apply_hero_fold(self):
        config = SessionConfig(num_players=4, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        loop.apply_hero_action("fold")
        assert loop.game_state.players[0].has_folded is True

    def test_apply_hero_call(self):
        config = SessionConfig(num_players=4, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        initial_pot = loop.game_state.pot
        loop.apply_hero_action("call", loop.game_state.current_bet)
        assert loop.game_state.pot > initial_pot

    def test_is_hand_over_after_all_fold(self):
        config = SessionConfig(num_players=3, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        for p in loop.game_state.players[1:]:
            p.fold()
        assert loop.is_hand_over() is True

    def test_resolve_winners_last_standing(self):
        config = SessionConfig(num_players=3, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        loop.game_state.pot = 100
        for p in loop.game_state.players[1:]:
            p.fold()
        winners = loop.resolve_winners()
        assert len(winners) == 1
        assert winners[0].seat == 0

    def test_blind_escalation(self):
        config = SessionConfig(blind_structure="escalating", escalation_interval=2, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        loop.end_hand()
        assert not loop.should_escalate_blinds()  # hand 1
        loop.start_hand()
        loop.end_hand()
        assert loop.should_escalate_blinds()  # hand 2
        loop.escalate_blinds()
        assert loop.game_state.small_blind == 10
        assert loop.game_state.big_blind == 20

    def test_advance_street(self):
        config = SessionConfig(num_players=3, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()
        assert loop.game_state.street == "preflop"
        loop.advance_street()
        assert loop.game_state.street == "flop"
        assert len(loop.game_state.community_cards) == 3

    def test_end_hand_advances_button(self):
        config = SessionConfig(num_players=4, strong_players=0, seed="test")
        loop = GameLoop(config)
        initial_button = loop.game_state.button_index
        loop.end_hand()
        assert loop.game_state.button_index == initial_button + 1
