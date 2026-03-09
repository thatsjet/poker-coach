"""Game state management for poker hands."""

from __future__ import annotations

import random

from poker_coach.engine.deck import Deck
from poker_coach.engine.player import Player
from poker_coach.engine.positions import get_positions, rotate_button

STREETS = ["preflop", "flop", "turn", "river", "showdown"]


class GameState:
    """Tracks the full state of a poker game across hands and streets."""

    def __init__(
        self,
        players: list[Player],
        small_blind: int,
        big_blind: int,
        rng: random.Random,
        button_index: int = 0,
    ) -> None:
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.rng = rng
        self.button_index = button_index
        self.hand_number = 0
        self.street = "preflop"
        self.pot = 0
        self.community_cards: list = []
        self.deck: Deck | None = None
        self.current_bet = 0
        self.min_raise = big_blind

    def start_hand(self) -> None:
        """Begin a new hand: increment counter, reset state, deal, post blinds."""
        self.hand_number += 1
        self.street = "preflop"
        self.pot = 0
        self.community_cards = []
        self.current_bet = 0

        for p in self.players:
            p.reset_for_new_hand()

        self.deck = Deck(self.rng)

        # Deal 2 hole cards to each active player
        for p in self.players:
            if p.is_active:
                p.hole_cards = self.deck.deal(2)

        # Post blinds
        num = len(self.players)
        if num == 2:
            # Heads-up: BTN posts SB, other posts BB
            sb_seat = self.button_index
            bb_seat = (self.button_index + 1) % num
        else:
            sb_seat = (self.button_index + 1) % num
            bb_seat = (self.button_index + 2) % num

        sb_actual = self.players[sb_seat].post_blind(self.small_blind)
        bb_actual = self.players[bb_seat].post_blind(self.big_blind)
        self.pot = sb_actual + bb_actual
        self.current_bet = self.big_blind
        self.min_raise = self.big_blind

    def advance_street(self) -> None:
        """Move to the next street, reset bets, deal community cards."""
        idx = STREETS.index(self.street)
        self.street = STREETS[idx + 1]

        # Reset player bets
        for p in self.players:
            p.current_bet = 0
        self.current_bet = 0

        # Deal community cards
        if self.deck is not None:
            if self.street == "flop":
                self.community_cards.extend(self.deck.deal(3))
            elif self.street in ("turn", "river"):
                self.community_cards.extend(self.deck.deal(1))

    def get_active_players(self) -> list[Player]:
        """Return players who have not folded and are still active."""
        return [p for p in self.players if p.is_active and not p.has_folded]

    def get_positions(self) -> list[str]:
        """Return position labels for all seats."""
        return get_positions(len(self.players), self.button_index)

    def advance_button(self) -> None:
        """Move the button to the next seat."""
        self.button_index = rotate_button(self.button_index, len(self.players))

    def to_dict(self, hero_seat: int) -> dict:
        """Return game state as a dictionary, from the hero's perspective."""
        positions = self.get_positions()
        hero = self.players[hero_seat]

        other_players = []
        for p in self.players:
            if p.seat == hero_seat:
                continue
            if p.has_folded:
                status = "folded"
            elif p.is_all_in:
                status = "all-in"
            elif not p.is_active:
                status = "out"
            else:
                status = "active"
            other_players.append(
                {
                    "seat": p.seat,
                    "name": p.name,
                    "archetype": p.archetype,
                    "position": positions[p.seat],
                    "stack": p.stack,
                    "current_bet": p.current_bet,
                    "status": status,
                }
            )

        return {
            "hand_number": self.hand_number,
            "street": self.street,
            "hero_position": positions[hero_seat],
            "hero_cards": [str(c) for c in hero.hole_cards],
            "community_cards": [str(c) for c in self.community_cards],
            "pot": self.pot,
            "hero_stack": hero.stack,
            "players": other_players,
            "current_bet": self.current_bet,
            "min_raise": self.min_raise,
        }
