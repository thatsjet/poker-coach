"""Tests for betting round fixes: all-in current_bet, side pots,
button/blind skip inactive, and NPC re-raise loop."""

import random

from poker_coach.config import SessionConfig
from poker_coach.engine.deck import Card
from poker_coach.engine.game_state import GameState
from poker_coach.engine.player import Player
from poker_coach.game_loop import GameLoop


def _make_player(seat, name="P", archetype="weak", stack=500):
    return Player(seat=seat, name=name, archetype=archetype, stack=stack)


def _make_state(players, sb=5, bb=10, seed=42, button=0):
    return GameState(
        players=players,
        small_blind=sb,
        big_blind=bb,
        rng=random.Random(seed),
        button_index=button,
    )


# ── Bug 1: All-in shouldn't reduce current_bet ──────────────────────


class TestAllInCurrentBet:
    def test_allin_for_less_doesnt_reduce_current_bet(self):
        """Player all-in for less than current bet shouldn't lower it."""
        config = SessionConfig(num_players=3, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()

        # Set current bet high
        loop.game_state.current_bet = 100

        # Player with only 30 chips tries to "raise" to 100
        short = loop.game_state.players[1]
        short.stack = 30
        short.current_bet = 0

        loop._apply_action(short, "raise", 100)

        # current_bet should NOT drop to 30
        assert loop.game_state.current_bet == 100
        assert short.is_all_in is True
        assert short.current_bet == 30

    def test_allin_for_more_updates_current_bet(self):
        """Normal raise should update current bet."""
        config = SessionConfig(num_players=3, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()

        loop.game_state.current_bet = 50
        player = loop.game_state.players[1]
        player.current_bet = 0

        loop._apply_action(player, "raise", 150)

        assert loop.game_state.current_bet == 150
        assert loop.game_state.min_raise == 150

    def test_allin_exact_match_updates(self):
        """All-in that exactly matches current bet doesn't change it."""
        config = SessionConfig(num_players=3, strong_players=0, seed="test")
        loop = GameLoop(config)
        loop.start_hand()

        loop.game_state.current_bet = 50
        player = loop.game_state.players[1]
        player.stack = 50
        player.current_bet = 0

        loop._apply_action(player, "raise", 50)

        # 50 == 50, not greater, so current_bet stays
        assert loop.game_state.current_bet == 50
        assert player.is_all_in is True


# ── Bug 2: Button/blinds skip inactive players ──────────────────────


class TestButtonSkipsInactive:
    def test_advance_button_skips_busted_player(self):
        """Button should skip over eliminated (stack=0) players."""
        players = [
            _make_player(0, "P0", stack=500),
            _make_player(1, "P1", stack=0),  # busted
            _make_player(2, "P2", stack=500),
            _make_player(3, "P3", stack=500),
        ]
        gs = _make_state(players, button=0)

        # Reset so busted player is inactive
        for p in gs.players:
            p.reset_for_new_hand()

        assert gs.players[1].is_active is False

        gs.advance_button()
        # Should skip seat 1 (busted) and land on seat 2
        assert gs.button_index == 2

    def test_advance_button_skips_multiple_busted(self):
        """Button should skip over multiple consecutive busted players."""
        players = [
            _make_player(0, "P0", stack=500),
            _make_player(1, "P1", stack=0),
            _make_player(2, "P2", stack=0),
            _make_player(3, "P3", stack=500),
        ]
        gs = _make_state(players, button=0)
        for p in gs.players:
            p.reset_for_new_hand()

        gs.advance_button()
        assert gs.button_index == 3

    def test_blinds_skip_inactive_player(self):
        """Blind posting should skip busted players."""
        players = [
            _make_player(0, "P0", stack=500),  # BTN
            _make_player(1, "P1", stack=0),  # would be SB but busted
            _make_player(2, "P2", stack=500),  # should get SB
            _make_player(3, "P3", stack=500),  # should get BB
        ]
        gs = _make_state(players, button=0)
        for p in gs.players:
            p.reset_for_new_hand()

        gs.start_hand()

        # Busted player should not have posted
        assert players[1].current_bet == 0
        # SB should be seat 2 (first active after button)
        assert players[2].current_bet == 5
        # BB should be seat 3
        assert players[3].current_bet == 10
        assert gs.pot == 15


# ── Bug 3: Side pots ────────────────────────────────────────────────


class TestSidePots:
    def _make_loop_with_players(self, stacks):
        """Helper to create a game loop with specific stack sizes."""
        config = SessionConfig(
            num_players=len(stacks), strong_players=0, seed="sidepot"
        )
        loop = GameLoop(config)
        for i, stack in enumerate(stacks):
            loop.game_state.players[i].stack = stack
        return loop

    def test_no_side_pot_equal_stacks(self):
        """No side pots when all players invest equally."""
        loop = self._make_loop_with_players([500, 500, 500])
        loop.start_hand()

        # All three players invest 100
        for p in loop.game_state.players:
            p.total_invested = 100
            p.has_folded = False
        loop.game_state.pot = 300

        pots = loop._calculate_side_pots()
        assert len(pots) == 1
        assert pots[0][0] == 300
        assert len(pots[0][1]) == 3

    def test_side_pot_one_short_stack(self):
        """One short-stacked all-in creates main pot + side pot."""
        loop = self._make_loop_with_players([50, 500, 500])
        loop.start_hand()

        # Player 0 all-in for 50, players 1 and 2 invest 100 each
        p0, p1, p2 = loop.game_state.players
        p0.total_invested = 50
        p0.is_all_in = True
        p0.has_folded = False
        p1.total_invested = 100
        p1.has_folded = False
        p2.total_invested = 100
        p2.has_folded = False
        loop.game_state.pot = 250

        pots = loop._calculate_side_pots()

        # Main pot: 50 * 3 = 150 (all three eligible)
        assert pots[0][0] == 150
        assert len(pots[0][1]) == 3

        # Side pot: (100-50) * 2 = 100 (only P1, P2 eligible)
        assert pots[1][0] == 100
        assert len(pots[1][1]) == 2
        assert p0 not in pots[1][1]

    def test_side_pot_two_short_stacks(self):
        """Two different all-in amounts create three pots."""
        loop = self._make_loop_with_players([30, 80, 500])
        loop.start_hand()

        p0, p1, p2 = loop.game_state.players
        p0.total_invested = 30
        p0.is_all_in = True
        p0.has_folded = False
        p1.total_invested = 80
        p1.is_all_in = True
        p1.has_folded = False
        p2.total_invested = 200
        p2.has_folded = False
        loop.game_state.pot = 310

        pots = loop._calculate_side_pots()
        assert len(pots) == 3

        # Main: 30 * 3 = 90
        assert pots[0][0] == 90
        assert len(pots[0][1]) == 3

        # Side 1: (80-30) * 2 = 100
        assert pots[1][0] == 100
        assert len(pots[1][1]) == 2
        assert p0 not in pots[1][1]

        # Side 2: (200-80) * 1 = 120
        assert pots[2][0] == 120
        assert len(pots[2][1]) == 1
        assert pots[2][1] == [p2]

    def test_side_pot_with_folded_player(self):
        """Folded player's chips contribute to pots but they can't win."""
        loop = self._make_loop_with_players([500, 500, 500])
        loop.start_hand()

        p0, p1, p2 = loop.game_state.players
        p0.total_invested = 50
        p0.has_folded = True
        p0.is_active = False
        p1.total_invested = 100
        p1.has_folded = False
        p2.total_invested = 100
        p2.has_folded = False
        loop.game_state.pot = 250

        pots = loop._calculate_side_pots()

        # Only one investment level from non-folded players: 100
        # But P0's 50 still goes into the pot
        assert len(pots) == 1
        # Total: min(50,100) + min(100,100) + min(100,100) = 50 + 100 + 100 = 250
        assert pots[0][0] == 250
        # Only P1 and P2 can win
        assert len(pots[0][1]) == 2
        assert p0 not in pots[0][1]

    def test_side_pot_total_matches_game_pot(self):
        """Sum of all side pots should equal total pot."""
        loop = self._make_loop_with_players([25, 75, 200, 500])
        loop.start_hand()

        players = loop.game_state.players
        investments = [25, 75, 200, 200]
        total = sum(investments)
        for p, inv in zip(players, investments):
            p.total_invested = inv
            p.has_folded = False
        loop.game_state.pot = total

        pots = loop._calculate_side_pots()
        pot_total = sum(amount for amount, _ in pots)
        assert pot_total == total

    def test_resolve_winners_with_side_pot(self):
        """Short-stack winner only gets main pot, not side pot."""
        loop = self._make_loop_with_players([50, 500, 500])
        loop.start_hand()

        p0, p1, p2 = loop.game_state.players
        # P0 all-in for 50, P1 and P2 each invest 100
        p0.total_invested = 50
        p0.stack = 0
        p0.is_all_in = True
        p1.total_invested = 100
        p1.stack = 400
        p2.total_invested = 100
        p2.stack = 400
        loop.game_state.pot = 250

        # Give P0 the best hand (royal flush)
        p0.hole_cards = [Card("A", "♠"), Card("K", "♠")]
        # P2 beats P1 for side pot (ace kicker vs low cards)
        p1.hole_cards = [Card("2", "♣"), Card("3", "♦")]
        p2.hole_cards = [Card("A", "♣"), Card("9", "♦")]
        loop.game_state.community_cards = [
            Card("Q", "♠"), Card("J", "♠"), Card("T", "♠"),
            Card("8", "♥"), Card("7", "♥"),
        ]

        initial_p0 = p0.stack
        initial_p2 = p2.stack

        winners = loop.resolve_winners()

        # P0 wins main pot (150) but NOT side pot (100)
        assert p0.stack == initial_p0 + 150
        assert p0 in winners

        # P2 wins side pot with ace-high vs P1's low cards
        assert p2.stack == initial_p2 + 100


# ── Bug 4: NPC re-raise loop ────────────────────────────────────────


class TestNpcReraiseLoop:
    def test_npc_responds_to_later_raise(self):
        """NPCs earlier in order must respond to raises by later NPCs."""
        config = SessionConfig(num_players=4, strong_players=0, seed="reraise")
        loop = GameLoop(config)
        loop.start_hand()

        # Manually set up: hero raised to 40, now NPCs respond
        hero = loop.game_state.players[0]
        hero.current_bet = 40
        hero.total_invested = 40
        loop.game_state.current_bet = 40
        loop.game_state.pot = 55  # blinds + hero raise

        # NPC1 has 10 in (SB), NPC2 has 10 in (BB), NPC3 has 0 in
        # After resolve_npc_actions_after_hero, if any NPC raises,
        # all others should get to respond
        actions = loop.resolve_npc_actions_after_hero()

        # Verify all NPCs have either matched current bet or folded
        for p in loop.game_state.players[1:]:
            if not p.has_folded and not p.is_all_in:
                assert p.current_bet >= loop.game_state.current_bet


# ── Player total_invested tracking ──────────────────────────────────


class TestTotalInvested:
    def test_post_blind_tracks_investment(self):
        p = _make_player(0, stack=500)
        p.post_blind(10)
        assert p.total_invested == 10

    def test_place_bet_tracks_investment(self):
        p = _make_player(0, stack=500)
        p.place_bet(50)
        assert p.total_invested == 50

    def test_investment_accumulates_across_bets(self):
        p = _make_player(0, stack=500)
        p.post_blind(10)
        p.place_bet(40)
        assert p.total_invested == 50

    def test_reset_clears_investment(self):
        p = _make_player(0, stack=500)
        p.place_bet(100)
        p.reset_for_new_hand()
        assert p.total_invested == 0
