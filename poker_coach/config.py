"""Session configuration for poker coach."""

import secrets
from dataclasses import dataclass, field


@dataclass
class SessionConfig:
    """Configuration for a poker coaching session."""

    num_players: int = 6
    strong_players: int = 1
    stack_mode: str = "fixed"  # "fixed" or "range"
    starting_stack: int = 500
    stack_range_min: int = 300
    stack_range_max: int = 700
    num_hands: int = 20
    blind_structure: str = "fixed"  # "fixed" or "escalating"
    small_blind: int = 5
    big_blind: int = 10
    escalation_interval: int = 5
    show_archetypes: bool = True
    seed: str = field(default_factory=lambda: secrets.token_hex(8))

    @property
    def weak_players(self) -> int:
        """Number of weak players (total minus hero minus strong)."""
        return self.num_players - 1 - self.strong_players
