from __future__ import annotations

import itertools
from collections import Counter
from dataclasses import dataclass

from poker_coach.engine.deck import Card

CATEGORY_RANK = {
    "high_card": 0,
    "pair": 1,
    "two_pair": 2,
    "three_of_a_kind": 3,
    "straight": 4,
    "flush": 5,
    "full_house": 6,
    "four_of_a_kind": 7,
    "straight_flush": 8,
    "royal_flush": 9,
}


@dataclass(frozen=True)
class HandRank:
    category: str
    tiebreakers: tuple[int, ...]

    def _key(self) -> tuple[int, tuple[int, ...]]:
        return (CATEGORY_RANK[self.category], self.tiebreakers)

    def __lt__(self, other: HandRank) -> bool:
        return self._key() < other._key()

    def __le__(self, other: HandRank) -> bool:
        return self._key() <= other._key()

    def __gt__(self, other: HandRank) -> bool:
        return self._key() > other._key()

    def __ge__(self, other: HandRank) -> bool:
        return self._key() >= other._key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandRank):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())


def _is_flush(cards: list[Card]) -> bool:
    return len({c.suit for c in cards}) == 1


def _is_straight(values: list[int]) -> tuple[bool, int]:
    """Check for a straight. Returns (is_straight, high_card).
    Values must be sorted descending."""
    # Normal straight
    if values[0] - values[4] == 4 and len(set(values)) == 5:
        return True, values[0]
    # Wheel: A-2-3-4-5
    if values == [14, 5, 4, 3, 2]:
        return True, 5
    return False, 0


def evaluate_hand(cards: list[Card]) -> HandRank:
    """Evaluate exactly 5 cards and return a HandRank."""
    if len(cards) != 5:
        raise ValueError(f"Expected 5 cards, got {len(cards)}")

    values = sorted((c.rank_value for c in cards), reverse=True)
    flush = _is_flush(cards)
    straight, straight_high = _is_straight(values)

    counts = Counter(values)
    # Group by frequency desc, then by value desc
    freq_groups = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    if straight and flush:
        if straight_high == 14:
            return HandRank("royal_flush", (14,))
        return HandRank("straight_flush", (straight_high,))

    if freq_groups[0][1] == 4:
        quad_val = freq_groups[0][0]
        kicker = freq_groups[1][0]
        return HandRank("four_of_a_kind", (quad_val, kicker))

    if freq_groups[0][1] == 3 and freq_groups[1][1] == 2:
        return HandRank("full_house", (freq_groups[0][0], freq_groups[1][0]))

    if flush:
        return HandRank("flush", tuple(values))

    if straight:
        return HandRank("straight", (straight_high,))

    if freq_groups[0][1] == 3:
        trip_val = freq_groups[0][0]
        kickers = sorted([v for v, c in freq_groups[1:]], reverse=True)
        return HandRank("three_of_a_kind", (trip_val, *kickers))

    if freq_groups[0][1] == 2 and freq_groups[1][1] == 2:
        high_pair = max(freq_groups[0][0], freq_groups[1][0])
        low_pair = min(freq_groups[0][0], freq_groups[1][0])
        kicker = freq_groups[2][0]
        return HandRank("two_pair", (high_pair, low_pair, kicker))

    if freq_groups[0][1] == 2:
        pair_val = freq_groups[0][0]
        kickers = sorted([v for v, c in freq_groups[1:]], reverse=True)
        return HandRank("pair", (pair_val, *kickers))

    return HandRank("high_card", tuple(values))


def best_five_card_hand(cards: list[Card]) -> HandRank:
    """Find the best 5-card hand from 5-7 cards."""
    if len(cards) < 5 or len(cards) > 7:
        raise ValueError(f"Expected 5-7 cards, got {len(cards)}")
    return max(evaluate_hand(list(combo)) for combo in itertools.combinations(cards, 5))


def determine_winners(players: list, community_cards: list[Card]) -> list:
    """Determine winner(s) from active players. Returns list (split pot if tied)."""
    best_rank: HandRank | None = None
    winners = []
    for player in players:
        all_cards = player.hole_cards + community_cards
        rank = best_five_card_hand(all_cards)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            winners = [player]
        elif rank == best_rank:
            winners.append(player)
    return winners
