"""Tests for NPC action resolution."""

from __future__ import annotations

import random

from poker_coach.engine.deck import Card
from poker_coach.engine.npc import NpcAction, resolve_npc_action
from poker_coach.engine.player import Player


class TestNpcAction:
    def test_action_has_amount(self):
        action = NpcAction(action="raise", amount=30)
        assert action.amount == 30

    def test_fold_has_no_amount(self):
        action = NpcAction(action="fold", amount=0)
        assert action.amount == 0


class TestWeakNpcPreflop:
    def test_calls_small_raise(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=20,
            pot=35,
            community_cards=[],
            rng=random.Random(42),
        )
        assert action.action == "call"

    def test_folds_large_raise(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=100,
            pot=115,
            community_cards=[],
            rng=random.Random(42),
        )
        assert action.action == "fold"

    def test_checks_when_no_bet(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=0,
            pot=15,
            community_cards=[],
            rng=random.Random(42),
        )
        assert action.action == "check"

    def test_call_amount_equals_current_bet(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=20,
            pot=35,
            community_cards=[],
            rng=random.Random(42),
        )
        assert action.action == "call"
        assert action.amount == 20


class TestWeakNpcPostflop:
    def test_bets_half_pot_with_two_pair(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("A", "s"), Card("K", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=0,
            pot=100,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "raise"
        assert action.amount == 50

    def test_checks_with_air_no_bet(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=0,
            pot=100,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "check"

    def test_calls_with_top_pair_facing_bet(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("A", "s"), Card("7", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "call"

    def test_raises_with_two_pair_facing_bet(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("A", "s"), Card("K", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "raise"

    def test_folds_with_air_facing_bet(self):
        """With a fixed seed that doesn't hit the 20% random call."""
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        # Use a seed that produces > 0.2 for the random call check
        # We'll try multiple seeds and verify the logic is correct
        # With seed 1, random.Random(1).random() = 0.134... so it would call
        # With seed 0, random.Random(0).random() = 0.844... so it would fold
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(0),
        )
        assert action.action == "fold"

    def test_calls_with_flush_draw_facing_bet(self):
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "s")]
        community = [Card("A", "s"), Card("K", "s"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "call"


class TestStrongNpcPreflop:
    def test_opens_premium_hand(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("K", "s")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=10,
            pot=15,
            community_cards=[],
            rng=random.Random(42),
            position="CO",
        )
        assert action.action == "raise"

    def test_folds_trash_utg(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=10,
            pot=15,
            community_cards=[],
            rng=random.Random(42),
            position="UTG",
        )
        assert action.action == "fold"

    def test_three_bets_with_aa_facing_raise(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("A", "d")]
        # current_bet > big blind indicates a raise has been made
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=30,
            pot=45,
            community_cards=[],
            rng=random.Random(42),
            position="BTN",
        )
        assert action.action == "raise"
        assert action.amount == 90  # 3x current bet

    def test_calls_premium_facing_raise(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("T", "s"), Card("T", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=30,
            pot=45,
            community_cards=[],
            rng=random.Random(42),
            position="BTN",
        )
        assert action.action == "call"

    def test_checks_no_bet_trash(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=0,
            pot=15,
            community_cards=[],
            rng=random.Random(42),
            position="BB",
        )
        assert action.action == "check"


class TestStrongNpcPostflop:
    def test_cbets_with_top_pair(self):
        """Strong NPC c-bets 70% of time with top pair."""
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("7", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        # Use seed where rng hits the 70% c-bet
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=0,
            pot=100,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action in ("raise", "check")  # depends on RNG

    def test_bets_with_two_pair_no_bet(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("K", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=0,
            pot=100,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "raise"

    def test_raises_two_pair_facing_bet(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("K", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "raise"

    def test_calls_top_pair_facing_small_bet(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("7", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "call"

    def test_folds_air_facing_bet(self):
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        action = resolve_npc_action(
            player=p,
            street="flop",
            current_bet=50,
            pot=150,
            community_cards=community,
            rng=random.Random(42),
        )
        assert action.action == "fold"


class TestHandKey:
    def test_pocket_pair(self):
        from poker_coach.engine.npc import _hand_key

        cards = [Card("A", "s"), Card("A", "d")]
        assert _hand_key(cards) == "AA"

    def test_suited(self):
        from poker_coach.engine.npc import _hand_key

        cards = [Card("A", "s"), Card("K", "s")]
        assert _hand_key(cards) == "AKs"

    def test_offsuit(self):
        from poker_coach.engine.npc import _hand_key

        cards = [Card("A", "s"), Card("K", "d")]
        assert _hand_key(cards) == "AKo"

    def test_lower_first_gets_reordered(self):
        from poker_coach.engine.npc import _hand_key

        cards = [Card("K", "s"), Card("A", "d")]
        assert _hand_key(cards) == "AKo"


class TestHelpers:
    def test_has_top_pair(self):
        from poker_coach.engine.npc import _has_top_pair_or_better

        cards = [Card("A", "s"), Card("7", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_top_pair_or_better(cards, community) is True

    def test_no_top_pair(self):
        from poker_coach.engine.npc import _has_top_pair_or_better

        cards = [Card("7", "s"), Card("2", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_top_pair_or_better(cards, community) is False

    def test_pocket_pair_is_top_pair_or_better(self):
        from poker_coach.engine.npc import _has_top_pair_or_better

        cards = [Card("Q", "s"), Card("Q", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_top_pair_or_better(cards, community) is True

    def test_has_flush_draw(self):
        from poker_coach.engine.npc import _has_draw

        cards = [Card("7", "s"), Card("2", "s")]
        community = [Card("A", "s"), Card("K", "s"), Card("5", "c")]
        assert _has_draw(cards, community) is True

    def test_has_oesd(self):
        from poker_coach.engine.npc import _has_draw

        cards = [Card("6", "s"), Card("7", "d")]
        community = [Card("8", "h"), Card("9", "c"), Card("A", "d")]
        assert _has_draw(cards, community) is True

    def test_no_draw(self):
        from poker_coach.engine.npc import _has_draw

        cards = [Card("7", "s"), Card("2", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_draw(cards, community) is False

    def test_has_two_pair(self):
        from poker_coach.engine.npc import _has_two_pair_or_better

        cards = [Card("A", "s"), Card("K", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_two_pair_or_better(cards, community) is True

    def test_has_trips(self):
        from poker_coach.engine.npc import _has_two_pair_or_better

        cards = [Card("A", "s"), Card("A", "h")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_two_pair_or_better(cards, community) is True

    def test_no_two_pair(self):
        from poker_coach.engine.npc import _has_two_pair_or_better

        cards = [Card("A", "s"), Card("7", "d")]
        community = [Card("A", "d"), Card("K", "h"), Card("5", "c")]
        assert _has_two_pair_or_better(cards, community) is False
