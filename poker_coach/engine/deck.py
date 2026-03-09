from __future__ import annotations

import random
from dataclasses import dataclass

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["s", "h", "d", "c"]
RANK_VALUES = {r: i for i, r in enumerate(RANKS, start=2)}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def rank_value(self) -> int:
        return RANK_VALUES[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


class Deck:
    def __init__(self, rng: random.Random) -> None:
        self.cards = [Card(r, s) for r in RANKS for s in SUITS]
        rng.shuffle(self.cards)

    def deal_one(self) -> Card:
        return self.cards.pop()

    def deal(self, n: int) -> list[Card]:
        return [self.deal_one() for _ in range(n)]
