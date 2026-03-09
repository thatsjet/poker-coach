"""Player data model for poker game state."""

from __future__ import annotations

from dataclasses import dataclass, field

from poker_coach.engine.deck import Card


@dataclass
class Player:
    """Represents a player at the poker table."""

    seat: int
    name: str
    archetype: str  # "hero", "weak", "strong"
    stack: int
    hole_cards: list[Card] = field(default_factory=list)
    current_bet: int = 0
    is_active: bool = True
    has_folded: bool = False
    is_all_in: bool = False

    def post_blind(self, amount: int) -> int:
        """Post a blind, returning the actual amount posted."""
        actual = min(amount, self.stack)
        self.stack -= actual
        self.current_bet += actual
        if self.stack == 0:
            self.is_all_in = True
        return actual

    def place_bet(self, amount: int) -> int:
        """Place a bet, returning the actual amount bet."""
        actual = min(amount, self.stack)
        self.stack -= actual
        self.current_bet += actual
        if self.stack == 0:
            self.is_all_in = True
        return actual

    def fold(self) -> None:
        """Fold the hand."""
        self.has_folded = True
        self.is_active = False

    def reset_for_new_hand(self) -> None:
        """Reset player state for a new hand."""
        self.hole_cards = []
        self.current_bet = 0
        self.is_active = self.stack > 0
        self.has_folded = False
        self.is_all_in = False
