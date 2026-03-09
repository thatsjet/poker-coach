"""NPC action resolution based on archetypes (weak/strong)."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from poker_coach.engine.deck import RANK_VALUES, Card
from poker_coach.engine.player import Player

PREMIUM_HANDS: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88",
    "AKs", "AKo", "AQs", "AQo", "AJs", "ATs",
    "KQs", "KQo", "KJs", "QJs", "JTs",
}

THREE_BET_HANDS: set[str] = {
    "AA", "KK", "QQ", "JJ", "AKs", "AKo", "AQs",
}


@dataclass
class NpcAction:
    action: str  # "fold", "call", "raise", "check"
    amount: int = 0


def _hand_key(cards: list[Card]) -> str:
    """Convert 2 hole cards to hand key like 'AKs', 'AKo', or 'AA'."""
    c0, c1 = cards[0], cards[1]
    # Put higher rank first
    if RANK_VALUES[c0.rank] < RANK_VALUES[c1.rank]:
        c0, c1 = c1, c0
    if c0.rank == c1.rank:
        return f"{c0.rank}{c1.rank}"
    suited = "s" if c0.suit == c1.suit else "o"
    return f"{c0.rank}{c1.rank}{suited}"


def _has_top_pair_or_better(cards: list[Card], community: list[Card]) -> bool:
    """Check if player has top pair+, pocket pair, or pair with board."""
    hole_ranks = [c.rank_value for c in cards]

    # Pocket pair counts
    if hole_ranks[0] == hole_ranks[1]:
        return True

    if not community:
        return False

    board_ranks = [c.rank_value for c in community]
    top_board_rank = max(board_ranks)

    # Check if any hole card pairs with top board card
    for hr in hole_ranks:
        if hr == top_board_rank:
            return True

    # Check if any hole card pairs with any board card (pair with board)
    for hr in hole_ranks:
        if hr in board_ranks:
            return True

    return False


def _has_draw(cards: list[Card], community: list[Card]) -> bool:
    """Check flush draw (4+ same suit) or open-ended straight draw."""
    all_cards = list(cards) + list(community)

    # Flush draw: 4+ cards of same suit
    suit_counts = Counter(c.suit for c in all_cards)
    if any(count >= 4 for count in suit_counts.values()):
        return True

    # Open-ended straight draw: 4 consecutive values in the combined cards
    values = sorted(set(c.rank_value for c in all_cards))
    for i in range(len(values) - 3):
        window = values[i : i + 4]
        if window[-1] - window[0] == 3:
            return True

    return False


def _has_two_pair_or_better(cards: list[Card], community: list[Card]) -> bool:
    """Check for two pair or better (trips, full house, quads)."""
    all_cards = list(cards) + list(community)
    rank_counts = Counter(c.rank_value for c in all_cards)
    hole_ranks = {c.rank_value for c in cards}

    # Trips or better: any rank appears 3+ times involving a hole card
    for rank, count in rank_counts.items():
        if count >= 3 and rank in hole_ranks:
            return True

    # Two pair: player's hole cards each pair with something
    pairs_involving_hole = 0
    for rank in hole_ranks:
        if rank_counts[rank] >= 2:
            pairs_involving_hole += 1
    if pairs_involving_hole >= 2:
        return True

    return False


def _resolve_weak(
    player: Player,
    street: str,
    current_bet: int,
    pot: int,
    community_cards: list[Card],
    rng: random.Random,
) -> NpcAction:
    """Resolve action for a weak NPC."""
    if street == "preflop":
        if current_bet == 0:
            return NpcAction(action="check")
        # Call any raise up to 15% of stack
        if current_bet <= player.stack * 0.15:
            return NpcAction(action="call", amount=current_bet)
        return NpcAction(action="fold")

    # Postflop
    has_two_pair = _has_two_pair_or_better(player.hole_cards, community_cards)
    has_top_pair = _has_top_pair_or_better(player.hole_cards, community_cards)
    has_draw_hand = _has_draw(player.hole_cards, community_cards)

    if current_bet == 0:
        # Facing no bet
        if has_two_pair:
            return NpcAction(action="raise", amount=pot // 2)
        return NpcAction(action="check")

    # Facing a bet
    if has_two_pair:
        return NpcAction(action="raise", amount=current_bet * 3)
    if has_top_pair:
        return NpcAction(action="call", amount=current_bet)
    if has_draw_hand and current_bet <= pot:
        return NpcAction(action="call", amount=current_bet)
    if current_bet <= pot and rng.random() < 0.2:
        return NpcAction(action="call", amount=current_bet)
    return NpcAction(action="fold")


def _resolve_strong(
    player: Player,
    street: str,
    current_bet: int,
    pot: int,
    community_cards: list[Card],
    rng: random.Random,
    position: str,
    big_blind: int = 10,
) -> NpcAction:
    """Resolve action for a strong NPC."""
    if street == "preflop":
        key = _hand_key(player.hole_cards)
        is_premium = key in PREMIUM_HANDS
        is_three_bet = key in THREE_BET_HANDS

        if current_bet == 0:
            # No bet to us
            if is_premium:
                return NpcAction(action="raise", amount=pot * 3)
            return NpcAction(action="check")

        # Facing a raise if current_bet exceeds the big blind
        facing_raise = current_bet > big_blind

        if facing_raise:
            if is_three_bet:
                return NpcAction(action="raise", amount=current_bet * 3)
            if is_premium:
                return NpcAction(action="call", amount=current_bet)
            return NpcAction(action="fold")

        # Just the big blind to call (open opportunity)
        if is_premium:
            return NpcAction(action="raise", amount=current_bet * 3)
        return NpcAction(action="fold")

    # Postflop
    has_two_pair = _has_two_pair_or_better(player.hole_cards, community_cards)
    has_top_pair = _has_top_pair_or_better(player.hole_cards, community_cards)

    if current_bet == 0:
        # No bet: c-bet logic
        if has_two_pair:
            return NpcAction(action="raise", amount=pot * 2 // 3)
        if has_top_pair and rng.random() < 0.7:
            return NpcAction(action="raise", amount=pot * 2 // 3)
        return NpcAction(action="check")

    # Facing a bet
    if has_two_pair:
        return NpcAction(action="raise", amount=current_bet * 3)
    if has_top_pair and current_bet <= pot:
        return NpcAction(action="call", amount=current_bet)
    return NpcAction(action="fold")


def resolve_npc_action(
    player: Player,
    street: str,
    current_bet: int,
    pot: int,
    community_cards: list[Card],
    rng: random.Random,
    position: str = "MP",
    big_blind: int = 10,
) -> NpcAction:
    """Resolve an NPC's action based on their archetype."""
    if player.archetype == "weak":
        return _resolve_weak(player, street, current_bet, pot, community_cards, rng)
    elif player.archetype == "strong":
        return _resolve_strong(
            player, street, current_bet, pot, community_cards, rng, position, big_blind
        )
    else:
        raise ValueError(f"Unknown archetype: {player.archetype}")
