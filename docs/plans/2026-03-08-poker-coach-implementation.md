# Poker Coach Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI poker coach that runs simulated No Limit Hold'em hands with NPC opponents and provides AI-powered coaching feedback via Claude.

**Architecture:** Monolithic Python CLI. Game engine handles all state/dealing/NPC actions deterministically. AI coach (Claude Sonnet via Anthropic SDK) evaluates user decisions at each action point. Session logs saved as markdown.

**Tech Stack:** Python 3.11+, `click` (CLI), `rich` (terminal UI), `anthropic` (Claude API), `uv` (package runner), `pytest` (testing)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `poker_coach/__init__.py`
- Create: `poker_coach/engine/__init__.py`
- Create: `poker_coach/coach/__init__.py`
- Create: `poker_coach/main.py`
- Create: `tests/__init__.py`
- Create: `tests/engine/__init__.py`
- Create: `tests/coach/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "poker-coach"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "anthropic>=0.40",
]

[project.scripts]
poker-coach = "poker_coach.main:main"

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8.0",
]
```

**Step 2: Create directory structure and empty init files**

```bash
mkdir -p poker_coach/engine poker_coach/coach tests/engine tests/coach
touch poker_coach/__init__.py poker_coach/engine/__init__.py poker_coach/coach/__init__.py
touch tests/__init__.py tests/engine/__init__.py tests/coach/__init__.py
```

**Step 3: Create minimal main.py**

```python
import click


@click.command()
@click.option("--seed", default=None, help="RNG seed for reproducibility")
def main(seed: str | None) -> None:
    """Poker Coach — AI-powered No Limit Hold'em training."""
    click.echo("Poker Coach starting...")


if __name__ == "__main__":
    main()
```

**Step 4: Install dependencies and verify**

Run: `cd /Users/jeremyanderson/projects/poker-coach && uv sync`
Expected: dependencies install successfully

Run: `uv run python -m poker_coach.main --help`
Expected: shows help text with `--seed` option

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock poker_coach/ tests/
git commit -m "feat: project scaffolding with uv, click, rich, anthropic deps"
```

---

### Task 2: Card and Deck

**Files:**
- Create: `poker_coach/engine/deck.py`
- Create: `tests/engine/test_deck.py`

**Step 1: Write failing tests**

```python
# tests/engine/test_deck.py
import random

from poker_coach.engine.deck import Card, Deck


class TestCard:
    def test_card_creation(self):
        card = Card("A", "s")
        assert card.rank == "A"
        assert card.suit == "s"

    def test_card_str(self):
        assert str(Card("A", "s")) == "As"
        assert str(Card("T", "h")) == "Th"

    def test_card_equality(self):
        assert Card("A", "s") == Card("A", "s")
        assert Card("A", "s") != Card("A", "h")

    def test_card_rank_value(self):
        assert Card("2", "s").rank_value == 2
        assert Card("T", "s").rank_value == 10
        assert Card("J", "s").rank_value == 11
        assert Card("Q", "s").rank_value == 12
        assert Card("K", "s").rank_value == 13
        assert Card("A", "s").rank_value == 14


class TestDeck:
    def test_deck_has_52_cards(self):
        deck = Deck(random.Random(42))
        assert len(deck.cards) == 52

    def test_deck_all_unique(self):
        deck = Deck(random.Random(42))
        card_strs = [str(c) for c in deck.cards]
        assert len(set(card_strs)) == 52

    def test_deal_one(self):
        deck = Deck(random.Random(42))
        card = deck.deal_one()
        assert isinstance(card, Card)
        assert len(deck.cards) == 51

    def test_deal_many(self):
        deck = Deck(random.Random(42))
        cards = deck.deal(5)
        assert len(cards) == 5
        assert len(deck.cards) == 47

    def test_deterministic_with_same_seed(self):
        d1 = Deck(random.Random(42))
        d2 = Deck(random.Random(42))
        assert [str(c) for c in d1.cards] == [str(c) for c in d2.cards]

    def test_different_seeds_differ(self):
        d1 = Deck(random.Random(42))
        d2 = Deck(random.Random(99))
        assert [str(c) for c in d1.cards] != [str(c) for c in d2.cards]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/engine/test_deck.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/engine/deck.py
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_deck.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/engine/deck.py tests/engine/test_deck.py
git commit -m "feat: Card and Deck with seeded RNG"
```

---

### Task 3: Hand Evaluation

**Files:**
- Create: `poker_coach/engine/hand_eval.py`
- Create: `tests/engine/test_hand_eval.py`

**Step 1: Write failing tests**

```python
# tests/engine/test_hand_eval.py
from poker_coach.engine.deck import Card
from poker_coach.engine.hand_eval import HandRank, evaluate_hand, best_five_card_hand


def _cards(s: str) -> list[Card]:
    """Parse 'As Kh Qd' into list of Cards."""
    return [Card(t[0], t[1]) for t in s.split()]


class TestHandRank:
    def test_high_card(self):
        result = evaluate_hand(_cards("As Kh Qd Jc 9s"))
        assert result.category == "high_card"

    def test_pair(self):
        result = evaluate_hand(_cards("As Ah Qd Jc 9s"))
        assert result.category == "pair"

    def test_two_pair(self):
        result = evaluate_hand(_cards("As Ah Qd Qc 9s"))
        assert result.category == "two_pair"

    def test_three_of_a_kind(self):
        result = evaluate_hand(_cards("As Ah Ad Jc 9s"))
        assert result.category == "three_of_a_kind"

    def test_straight(self):
        result = evaluate_hand(_cards("5s 6h 7d 8c 9s"))
        assert result.category == "straight"

    def test_wheel_straight(self):
        result = evaluate_hand(_cards("As 2h 3d 4c 5s"))
        assert result.category == "straight"

    def test_flush(self):
        result = evaluate_hand(_cards("As Ks Qs Js 9s"))
        assert result.category == "flush"

    def test_full_house(self):
        result = evaluate_hand(_cards("As Ah Ad Kc Ks"))
        assert result.category == "full_house"

    def test_four_of_a_kind(self):
        result = evaluate_hand(_cards("As Ah Ad Ac Ks"))
        assert result.category == "four_of_a_kind"

    def test_straight_flush(self):
        result = evaluate_hand(_cards("5s 6s 7s 8s 9s"))
        assert result.category == "straight_flush"

    def test_royal_flush(self):
        result = evaluate_hand(_cards("Ts Js Qs Ks As"))
        assert result.category == "royal_flush"


class TestHandComparison:
    def test_pair_beats_high_card(self):
        pair = evaluate_hand(_cards("As Ah Qd Jc 9s"))
        high = evaluate_hand(_cards("As Kh Qd Jc 9s"))
        assert pair > high

    def test_higher_pair_wins(self):
        high_pair = evaluate_hand(_cards("As Ah Qd Jc 9s"))
        low_pair = evaluate_hand(_cards("Ks Kh Qd Jc 9s"))
        assert high_pair > low_pair

    def test_kicker_breaks_tie(self):
        better = evaluate_hand(_cards("As Ah Kd Jc 9s"))
        worse = evaluate_hand(_cards("As Ah Qd Jc 9s"))
        assert better > worse

    def test_equal_hands(self):
        h1 = evaluate_hand(_cards("As Ah Kd Jc 9s"))
        h2 = evaluate_hand(_cards("Ad Ac Kh Jd 9h"))
        assert h1 == h2

    def test_flush_beats_straight(self):
        flush = evaluate_hand(_cards("As Ks Qs Js 9s"))
        straight = evaluate_hand(_cards("5s 6h 7d 8c 9s"))
        assert flush > straight


class TestBestFiveCardHand:
    def test_picks_best_from_seven(self):
        seven = _cards("As Ah Ad Kc Ks 2d 3c")
        result = best_five_card_hand(seven)
        assert result.category == "full_house"

    def test_picks_flush_over_pair(self):
        seven = _cards("As Ks Qs Js 9s 2d 2c")
        result = best_five_card_hand(seven)
        assert result.category == "flush"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/engine/test_hand_eval.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/engine/hand_eval.py
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from poker_coach.engine.deck import Card


CATEGORY_RANKS = {
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


@dataclass
class HandRank:
    category: str
    tiebreakers: tuple[int, ...]

    @property
    def _sort_key(self) -> tuple[int, tuple[int, ...]]:
        return (CATEGORY_RANKS[self.category], self.tiebreakers)

    def __gt__(self, other: HandRank) -> bool:
        return self._sort_key > other._sort_key

    def __lt__(self, other: HandRank) -> bool:
        return self._sort_key < other._sort_key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandRank):
            return NotImplemented
        return self._sort_key == other._sort_key

    def __ge__(self, other: HandRank) -> bool:
        return self._sort_key >= other._sort_key

    def __le__(self, other: HandRank) -> bool:
        return self._sort_key <= other._sort_key


def evaluate_hand(cards: list[Card]) -> HandRank:
    """Evaluate exactly 5 cards and return a HandRank."""
    assert len(cards) == 5
    values = sorted([c.rank_value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    counts = Counter(values)

    is_flush = len(set(suits)) == 1

    # Check straight
    is_straight = False
    straight_high = 0
    if len(set(values)) == 5:
        if values[0] - values[4] == 4:
            is_straight = True
            straight_high = values[0]
        # Wheel: A-2-3-4-5
        elif values == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5  # 5-high straight

    if is_straight and is_flush:
        if straight_high == 14:
            return HandRank("royal_flush", (14,))
        return HandRank("straight_flush", (straight_high,))

    freq = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    if freq[0][1] == 4:
        quad_val = freq[0][0]
        kicker = freq[1][0]
        return HandRank("four_of_a_kind", (quad_val, kicker))

    if freq[0][1] == 3 and freq[1][1] == 2:
        return HandRank("full_house", (freq[0][0], freq[1][0]))

    if is_flush:
        return HandRank("flush", tuple(values))

    if is_straight:
        return HandRank("straight", (straight_high,))

    if freq[0][1] == 3:
        trips_val = freq[0][0]
        kickers = sorted([v for v in values if v != trips_val], reverse=True)
        return HandRank("three_of_a_kind", (trips_val, *kickers))

    if freq[0][1] == 2 and freq[1][1] == 2:
        high_pair = max(freq[0][0], freq[1][0])
        low_pair = min(freq[0][0], freq[1][0])
        kicker = [v for v in values if v != high_pair and v != low_pair][0]
        return HandRank("two_pair", (high_pair, low_pair, kicker))

    if freq[0][1] == 2:
        pair_val = freq[0][0]
        kickers = sorted([v for v in values if v != pair_val], reverse=True)
        return HandRank("pair", (pair_val, *kickers))

    return HandRank("high_card", tuple(values))


def best_five_card_hand(cards: list[Card]) -> HandRank:
    """Find the best 5-card hand from 5-7 cards."""
    assert 5 <= len(cards) <= 7
    best: HandRank | None = None
    for combo in combinations(cards, 5):
        rank = evaluate_hand(list(combo))
        if best is None or rank > best:
            best = rank
    assert best is not None
    return best
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_hand_eval.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/engine/hand_eval.py tests/engine/test_hand_eval.py
git commit -m "feat: hand evaluation with all rankings and 7-card best-hand selection"
```

---

### Task 4: Positions

**Files:**
- Create: `poker_coach/engine/positions.py`
- Create: `tests/engine/test_positions.py`

**Step 1: Write failing tests**

```python
# tests/engine/test_positions.py
from poker_coach.engine.positions import get_positions, rotate_button


class TestPositions:
    def test_two_players(self):
        positions = get_positions(2, button_index=0)
        assert positions == ["BTN", "BB"]

    def test_three_players(self):
        positions = get_positions(3, button_index=0)
        assert positions == ["BTN", "SB", "BB"]

    def test_six_players(self):
        positions = get_positions(6, button_index=0)
        assert positions == ["BTN", "SB", "BB", "UTG", "HJ", "CO"]

    def test_nine_players(self):
        positions = get_positions(9, button_index=0)
        assert positions == ["BTN", "SB", "BB", "UTG", "UTG+1", "MP", "MP+1", "HJ", "CO"]

    def test_button_rotation(self):
        positions = get_positions(6, button_index=1)
        # Seat 1 is now button, so positions shift
        assert positions[1] == "BTN"
        assert positions[2] == "SB"

    def test_rotate_button(self):
        assert rotate_button(0, 6) == 1
        assert rotate_button(5, 6) == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/engine/test_positions.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/engine/positions.py
from __future__ import annotations

# Position labels by table size (positions listed starting from BTN)
POSITION_LABELS: dict[int, list[str]] = {
    2: ["BTN", "BB"],
    3: ["BTN", "SB", "BB"],
    4: ["BTN", "SB", "BB", "UTG"],
    5: ["BTN", "SB", "BB", "UTG", "CO"],
    6: ["BTN", "SB", "BB", "UTG", "HJ", "CO"],
    7: ["BTN", "SB", "BB", "UTG", "MP", "HJ", "CO"],
    8: ["BTN", "SB", "BB", "UTG", "UTG+1", "MP", "HJ", "CO"],
    9: ["BTN", "SB", "BB", "UTG", "UTG+1", "MP", "MP+1", "HJ", "CO"],
}


def get_positions(num_players: int, button_index: int) -> list[str]:
    """Return position labels for each seat, with seat button_index as BTN."""
    labels = POSITION_LABELS[num_players]
    result = [""] * num_players
    for i, label in enumerate(labels):
        seat = (button_index + i) % num_players
        result[seat] = label
    return result


def rotate_button(current: int, num_players: int) -> int:
    """Advance button to the next seat."""
    return (current + 1) % num_players
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_positions.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/engine/positions.py tests/engine/test_positions.py
git commit -m "feat: position labels and button rotation"
```

---

### Task 5: Player and Game State Foundation

**Files:**
- Create: `poker_coach/engine/game_state.py`
- Create: `tests/engine/test_game_state.py`

**Step 1: Write failing tests**

```python
# tests/engine/test_game_state.py
import random

from poker_coach.engine.game_state import GameState, Player


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


class TestGameStateSetup:
    def _make_state(self, num_players=6, seed=42):
        players = []
        players.append(Player(seat=0, name="Hero", archetype="hero", stack=500))
        for i in range(1, num_players):
            players.append(Player(seat=i, name=f"NPC{i}", archetype="weak", stack=500))
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
        assert len(gs.community_cards) == 0

    def test_start_hand_deals_cards(self):
        gs = self._make_state()
        gs.start_hand()
        assert gs.hand_number == 1
        for p in gs.players:
            assert len(p.hole_cards) == 2

    def test_start_hand_posts_blinds(self):
        gs = self._make_state()
        gs.start_hand()
        # Button is seat 0, SB is seat 1, BB is seat 2
        assert gs.players[1].current_bet == 5
        assert gs.players[2].current_bet == 10
        assert gs.pot == 15

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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/engine/test_game_state.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/engine/game_state.py
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from poker_coach.engine.deck import Card, Deck
from poker_coach.engine.positions import get_positions, rotate_button


@dataclass
class Player:
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
        actual = min(amount, self.stack)
        self.stack -= actual
        self.current_bet += actual
        if self.stack == 0:
            self.is_all_in = True
        return actual

    def place_bet(self, amount: int) -> int:
        actual = min(amount, self.stack)
        self.stack -= actual
        self.current_bet += actual
        if self.stack == 0:
            self.is_all_in = True
        return actual

    def fold(self) -> None:
        self.has_folded = True
        self.is_active = False

    def reset_for_new_hand(self) -> None:
        self.hole_cards = []
        self.current_bet = 0
        self.is_active = self.stack > 0
        self.has_folded = False
        self.is_all_in = False


STREETS = ["preflop", "flop", "turn", "river", "showdown"]


class GameState:
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
        self.community_cards: list[Card] = []
        self.deck: Deck | None = None
        self.current_bet = 0  # highest bet on current street
        self.min_raise = big_blind

    def start_hand(self) -> None:
        self.hand_number += 1
        self.street = "preflop"
        self.pot = 0
        self.community_cards = []
        self.current_bet = 0

        for p in self.players:
            p.reset_for_new_hand()

        self.deck = Deck(self.rng)

        # Deal hole cards
        for p in self.players:
            if p.is_active:
                p.hole_cards = self.deck.deal(2)

        # Post blinds
        positions = get_positions(len(self.players), self.button_index)
        for i, pos in enumerate(positions):
            if pos == "SB":
                amount = self.players[i].post_blind(self.small_blind)
                self.pot += amount
            elif pos == "BB":
                amount = self.players[i].post_blind(self.big_blind)
                self.pot += amount
                self.current_bet = self.big_blind

        # For 2-player, BTN posts SB
        if len(self.players) == 2:
            btn_seat = self.button_index
            self.pot -= self.players[btn_seat].current_bet  # undo any previous
            self.players[btn_seat].current_bet = 0
            self.players[btn_seat].stack += self.small_blind  # refund
            amount = self.players[btn_seat].post_blind(self.small_blind)
            self.pot += amount

    def advance_street(self) -> None:
        idx = STREETS.index(self.street)
        self.street = STREETS[idx + 1]

        # Reset bets for new street
        for p in self.players:
            p.current_bet = 0
        self.current_bet = 0
        self.min_raise = self.big_blind

        # Deal community cards
        assert self.deck is not None
        if self.street == "flop":
            self.community_cards.extend(self.deck.deal(3))
        elif self.street in ("turn", "river"):
            self.community_cards.append(self.deck.deal_one())

    def get_active_players(self) -> list[Player]:
        return [p for p in self.players if p.is_active and not p.has_folded]

    def get_positions(self) -> list[str]:
        return get_positions(len(self.players), self.button_index)

    def advance_button(self) -> None:
        self.button_index = rotate_button(self.button_index, len(self.players))

    def to_dict(self, hero_seat: int) -> dict[str, Any]:
        hero = self.players[hero_seat]
        positions = self.get_positions()
        return {
            "hand_number": self.hand_number,
            "street": self.street,
            "hero_position": positions[hero_seat],
            "hero_cards": [str(c) for c in hero.hole_cards],
            "community_cards": [str(c) for c in self.community_cards],
            "pot": self.pot,
            "hero_stack": hero.stack,
            "players": [
                {
                    "seat": p.seat,
                    "name": p.name,
                    "archetype": p.archetype,
                    "position": positions[p.seat],
                    "stack": p.stack,
                    "status": "folded" if p.has_folded else ("all-in" if p.is_all_in else "active"),
                    "current_bet": p.current_bet,
                }
                for p in self.players
                if p.seat != hero_seat
            ],
            "current_bet": self.current_bet,
            "min_raise": self.min_raise,
        }
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_game_state.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/engine/game_state.py tests/engine/test_game_state.py
git commit -m "feat: Player and GameState with dealing, blinds, and street management"
```

---

### Task 6: NPC Action Resolution

**Files:**
- Create: `poker_coach/engine/npc.py`
- Create: `tests/engine/test_npc.py`

**Step 1: Write failing tests**

```python
# tests/engine/test_npc.py
import random

from poker_coach.engine.deck import Card
from poker_coach.engine.game_state import GameState, Player
from poker_coach.engine.npc import resolve_npc_action, NpcAction


class TestWeakNpcPreflop:
    def test_calls_small_raise(self):
        """Weak NPC calls raises up to 15% of stack."""
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=20,  # 4% of stack
            pot=35,
            community_cards=[],
            rng=random.Random(42),
        )
        assert action.action == "call"

    def test_folds_large_raise(self):
        """Weak NPC folds to raises > 15% of stack."""
        p = Player(seat=1, name="Fish1", archetype="weak", stack=500)
        p.hole_cards = [Card("7", "s"), Card("2", "d")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=100,  # 20% of stack
            pot=115,
            community_cards=[],
            rng=random.Random(42),
        )
        assert action.action == "fold"


class TestStrongNpcPreflop:
    def test_opens_premium_hand(self):
        """Strong NPC opens with premium hands."""
        p = Player(seat=1, name="Reg1", archetype="strong", stack=500)
        p.hole_cards = [Card("A", "s"), Card("K", "s")]
        action = resolve_npc_action(
            player=p,
            street="preflop",
            current_bet=10,  # just BB
            pot=15,
            community_cards=[],
            rng=random.Random(42),
            position="CO",
        )
        assert action.action == "raise"

    def test_folds_trash_utg(self):
        """Strong NPC folds trash from early position."""
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


class TestNpcAction:
    def test_action_has_amount(self):
        action = NpcAction(action="raise", amount=30)
        assert action.amount == 30

    def test_fold_has_no_amount(self):
        action = NpcAction(action="fold", amount=0)
        assert action.amount == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/engine/test_npc.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/engine/npc.py
from __future__ import annotations

import random
from dataclasses import dataclass

from poker_coach.engine.deck import Card


@dataclass
class NpcAction:
    action: str  # "fold", "call", "raise", "check"
    amount: int = 0


# Top 20% of starting hands (simplified — suited and pairs)
PREMIUM_HANDS = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88",
    "AKs", "AKo", "AQs", "AQo", "AJs", "ATs",
    "KQs", "KQo", "KJs", "QJs", "JTs",
}

# Top 8% for 3-betting
THREE_BET_HANDS = {
    "AA", "KK", "QQ", "JJ", "AKs", "AKo", "AQs",
}


def _hand_key(cards: list[Card]) -> str:
    """Convert two hole cards to a hand key like 'AKs' or 'AKo'."""
    c1, c2 = cards
    r1, r2 = c1.rank_value, c2.rank_value
    if r1 < r2:
        c1, c2 = c2, c1
    high, low = c1.rank, c2.rank
    if high == low:
        return f"{high}{low}"
    suited = "s" if c1.suit == c2.suit else "o"
    return f"{high}{low}{suited}"


def _has_top_pair_or_better(cards: list[Card], community: list[Card]) -> bool:
    """Check if player has top pair or better with community cards."""
    if not community:
        return False
    board_ranks = sorted([c.rank_value for c in community], reverse=True)
    player_ranks = [c.rank_value for c in cards]

    # Pairs or better in hand
    if player_ranks[0] == player_ranks[1]:
        return True

    # Top pair
    top_board = board_ranks[0]
    if top_board in player_ranks:
        return True

    return False


def _has_draw(cards: list[Card], community: list[Card]) -> bool:
    """Check if player has a flush or straight draw."""
    all_cards = cards + community
    # Flush draw: 4 of same suit
    suits = [c.suit for c in all_cards]
    for s in set(suits):
        if suits.count(s) >= 4:
            return True
    # Open-ended straight draw (simplified): 4 consecutive values
    values = sorted(set(c.rank_value for c in all_cards))
    for i in range(len(values) - 3):
        if values[i + 3] - values[i] <= 4:
            return True
    return False


def _has_two_pair_or_better(cards: list[Card], community: list[Card]) -> bool:
    """Check if player has two pair or better."""
    from collections import Counter
    all_values = [c.rank_value for c in cards + community]
    counts = Counter(all_values)
    pairs = sum(1 for v in counts.values() if v >= 2)
    has_trips = any(v >= 3 for v in counts.values())
    return pairs >= 2 or has_trips


def resolve_npc_action(
    player: Player,
    street: str,
    current_bet: int,
    pot: int,
    community_cards: list[Card],
    rng: random.Random,
    position: str = "MP",
) -> NpcAction:
    """Resolve an NPC's action based on archetype."""
    to_call = current_bet - player.current_bet

    if player.archetype == "weak":
        return _resolve_weak(player, street, current_bet, to_call, pot, community_cards, rng)
    elif player.archetype == "strong":
        return _resolve_strong(player, street, current_bet, to_call, pot, community_cards, rng, position)
    else:
        return NpcAction(action="fold")


def _resolve_weak(
    player: Player,
    street: str,
    current_bet: int,
    to_call: int,
    pot: int,
    community_cards: list[Card],
    rng: random.Random,
) -> NpcAction:
    if street == "preflop":
        if to_call == 0:
            return NpcAction(action="check")
        # Call raises up to 15% of stack
        if to_call <= player.stack * 0.15:
            return NpcAction(action="call", amount=to_call)
        return NpcAction(action="fold")
    else:
        # Postflop
        has_hand = _has_top_pair_or_better(player.hole_cards, community_cards)
        has_draw_hand = _has_draw(player.hole_cards, community_cards)
        has_strong = _has_two_pair_or_better(player.hole_cards, community_cards)

        if to_call == 0:
            # Check or bet
            if has_strong:
                bet_size = pot // 2
                return NpcAction(action="raise", amount=max(bet_size, current_bet))
            return NpcAction(action="check")

        # Facing a bet
        if has_hand:
            # Never fold top pair
            if has_strong:
                raise_size = to_call + pot // 2
                return NpcAction(action="raise", amount=raise_size)
            return NpcAction(action="call", amount=to_call)

        if has_draw_hand and to_call <= pot:
            return NpcAction(action="call", amount=to_call)

        # Random call 20% with air
        if to_call <= pot and rng.random() < 0.20:
            return NpcAction(action="call", amount=to_call)

        return NpcAction(action="fold")


def _resolve_strong(
    player: Player,
    street: str,
    current_bet: int,
    to_call: int,
    pot: int,
    community_cards: list[Card],
    rng: random.Random,
    position: str,
) -> NpcAction:
    hand_key = _hand_key(player.hole_cards)

    if street == "preflop":
        if to_call == 0 or (to_call <= player.current_bet):
            # Opening or checking
            if hand_key in PREMIUM_HANDS:
                raise_size = max(current_bet * 3, player.stack // 15)
                return NpcAction(action="raise", amount=raise_size)
            return NpcAction(action="fold" if to_call > 0 else "check")

        # Facing a raise
        if hand_key in THREE_BET_HANDS:
            raise_size = current_bet * 3
            return NpcAction(action="raise", amount=raise_size)
        if hand_key in PREMIUM_HANDS:
            return NpcAction(action="call", amount=to_call)
        return NpcAction(action="fold")
    else:
        # Postflop
        has_hand = _has_top_pair_or_better(player.hole_cards, community_cards)
        has_strong = _has_two_pair_or_better(player.hole_cards, community_cards)

        if to_call == 0:
            # C-bet 70% in position
            if rng.random() < 0.70 and has_hand:
                bet_size = pot * 2 // 3
                return NpcAction(action="raise", amount=max(bet_size, 1))
            if has_strong:
                bet_size = pot * 2 // 3
                return NpcAction(action="raise", amount=max(bet_size, 1))
            return NpcAction(action="check")

        # Facing a bet
        if has_strong:
            raise_size = to_call + pot
            return NpcAction(action="raise", amount=raise_size)
        if has_hand and to_call <= pot:
            return NpcAction(action="call", amount=to_call)
        return NpcAction(action="fold")


# Import here to avoid circular imports at module level
from poker_coach.engine.game_state import Player  # noqa: E402
```

Note: The circular import between `npc.py` and `game_state.py` needs a fix. We'll use a forward reference — move the `Player` import to the top and remove the `game_state` import since `Player` is the only thing needed. Actually, let's restructure: `Player` should be defined in its own file or `npc.py` should accept the player as a typed parameter. The simplest fix: put the import at the top since `npc.py` doesn't import from `game_state.py` — it only needs `Player`. But `Player` is in `game_state.py`. Let's move `Player` to its own module.

**Step 3b: Refactor — Extract Player to its own module**

Move `Player` class from `game_state.py` to a new file `poker_coach/engine/player.py` and import it in both `game_state.py` and `npc.py`.

Create: `poker_coach/engine/player.py`

```python
# poker_coach/engine/player.py
from __future__ import annotations

from dataclasses import dataclass, field

from poker_coach.engine.deck import Card


@dataclass
class Player:
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
        actual = min(amount, self.stack)
        self.stack -= actual
        self.current_bet += actual
        if self.stack == 0:
            self.is_all_in = True
        return actual

    def place_bet(self, amount: int) -> int:
        actual = min(amount, self.stack)
        self.stack -= actual
        self.current_bet += actual
        if self.stack == 0:
            self.is_all_in = True
        return actual

    def fold(self) -> None:
        self.has_folded = True
        self.is_active = False

    def reset_for_new_hand(self) -> None:
        self.hole_cards = []
        self.current_bet = 0
        self.is_active = self.stack > 0
        self.has_folded = False
        self.is_all_in = False
```

Then update `game_state.py` to import `Player` from `player.py` instead of defining it, and update `npc.py` to import from `player.py`.

Update tests accordingly — `test_game_state.py` imports `Player` from `poker_coach.engine.player`.

**Step 4: Run all tests to verify they pass**

Run: `uv run pytest tests/ -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/engine/player.py poker_coach/engine/npc.py poker_coach/engine/game_state.py tests/engine/test_npc.py tests/engine/test_game_state.py
git commit -m "feat: NPC action resolution with weak/strong archetypes, extract Player to own module"
```

---

### Task 7: Configuration

**Files:**
- Create: `poker_coach/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing tests**

```python
# tests/test_config.py
from poker_coach.config import SessionConfig


class TestSessionConfig:
    def test_defaults(self):
        config = SessionConfig()
        assert config.num_players == 6
        assert config.strong_players == 1
        assert config.num_hands == 20
        assert config.small_blind == 5
        assert config.big_blind == 10
        assert config.blind_structure == "fixed"
        assert config.show_archetypes is True

    def test_weak_players_computed(self):
        config = SessionConfig(num_players=6, strong_players=2)
        assert config.weak_players == 3  # 6 total - 1 hero - 2 strong

    def test_custom_values(self):
        config = SessionConfig(num_players=9, strong_players=3, num_hands=30)
        assert config.num_players == 9
        assert config.strong_players == 3
        assert config.weak_players == 5

    def test_fixed_stack(self):
        config = SessionConfig(stack_mode="fixed", starting_stack=1000)
        assert config.starting_stack == 1000

    def test_escalation_interval(self):
        config = SessionConfig(blind_structure="escalating", escalation_interval=5)
        assert config.escalation_interval == 5
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/config.py
from __future__ import annotations

import secrets
from dataclasses import dataclass, field


@dataclass
class SessionConfig:
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
        return self.num_players - 1 - self.strong_players
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/config.py tests/test_config.py
git commit -m "feat: session configuration with defaults"
```

---

### Task 8: Winner Resolution

**Files:**
- Modify: `poker_coach/engine/hand_eval.py`
- Create: `tests/engine/test_winner.py`

**Step 1: Write failing tests**

```python
# tests/engine/test_winner.py
from poker_coach.engine.deck import Card
from poker_coach.engine.player import Player
from poker_coach.engine.hand_eval import determine_winners


def _cards(s: str) -> list[Card]:
    return [Card(t[0], t[1]) for t in s.split()]


class TestDetermineWinners:
    def test_single_winner(self):
        p1 = Player(seat=0, name="P1", archetype="hero", stack=0)
        p1.hole_cards = _cards("As Ah")
        p2 = Player(seat=1, name="P2", archetype="weak", stack=0)
        p2.hole_cards = _cards("Ks Kh")
        community = _cards("2d 3c 4h 7s 9d")

        winners = determine_winners([p1, p2], community)
        assert len(winners) == 1
        assert winners[0].seat == 0

    def test_split_pot(self):
        p1 = Player(seat=0, name="P1", archetype="hero", stack=0)
        p1.hole_cards = _cards("As Kh")
        p2 = Player(seat=1, name="P2", archetype="weak", stack=0)
        p2.hole_cards = _cards("Ad Kc")
        community = _cards("2d 3c 4h 7s 9d")

        winners = determine_winners([p1, p2], community)
        assert len(winners) == 2

    def test_board_plays(self):
        """When the board is the best hand for both players."""
        p1 = Player(seat=0, name="P1", archetype="hero", stack=0)
        p1.hole_cards = _cards("2s 3h")
        p2 = Player(seat=1, name="P2", archetype="weak", stack=0)
        p2.hole_cards = _cards("4d 5c")
        community = _cards("As Ks Qs Js Ts")

        winners = determine_winners([p1, p2], community)
        assert len(winners) == 2  # Royal flush on board, split
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/engine/test_winner.py -v`
Expected: FAIL — cannot import determine_winners

**Step 3: Add determine_winners to hand_eval.py**

Append to `poker_coach/engine/hand_eval.py`:

```python
def determine_winners(players: list, community_cards: list[Card]) -> list:
    """Determine winner(s) from active players. Returns list (split pot if tied)."""
    from poker_coach.engine.player import Player

    best_rank: HandRank | None = None
    winners: list[Player] = []

    for player in players:
        all_cards = player.hole_cards + community_cards
        rank = best_five_card_hand(all_cards)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            winners = [player]
        elif rank == best_rank:
            winners.append(player)

    return winners
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/engine/test_winner.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/engine/hand_eval.py tests/engine/test_winner.py
git commit -m "feat: winner resolution with split pot support"
```

---

### Task 9: CLI Interface

**Files:**
- Create: `poker_coach/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write failing tests**

```python
# tests/test_cli.py
from click.testing import CliRunner

from poker_coach.cli import configure_session


class TestCLIConfig:
    def test_default_config(self):
        """Accepting all defaults produces a valid config."""
        runner = CliRunner()
        result = runner.invoke(configure_session, input="\n\n\n\n\n\n\n\n")
        assert result.exit_code == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — cannot import

**Step 3: Write implementation**

```python
# poker_coach/cli.py
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from poker_coach.config import SessionConfig
from poker_coach.engine.deck import Card

console = Console()

SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
SUIT_COLORS = {"s": "white", "h": "red", "d": "red", "c": "white"}


def format_card(card: Card) -> str:
    """Format a card with suit symbol for rich markup."""
    symbol = SUIT_SYMBOLS[card.suit]
    color = SUIT_COLORS[card.suit]
    return f"[{color}]{card.rank}{symbol}[/{color}]"


def format_cards(cards: list[Card]) -> str:
    return " ".join(format_card(c) for c in cards)


@click.command()
def configure_session() -> SessionConfig:
    """Interactively configure a poker session."""
    num_players = click.prompt("Number of players", default=6, type=int)
    strong_players = click.prompt("Strong players", default=1, type=int)
    starting_stack = click.prompt("Starting stack", default=500, type=int)
    num_hands = click.prompt("Number of hands", default=20, type=int)
    blind_structure = click.prompt(
        "Blind structure (fixed/escalating)", default="fixed", type=str
    )
    small_blind = click.prompt("Small blind", default=5, type=int)
    big_blind = click.prompt("Big blind", default=10, type=int)
    show_archetypes = click.prompt("Show archetypes", default=True, type=bool)

    config = SessionConfig(
        num_players=num_players,
        strong_players=strong_players,
        starting_stack=starting_stack,
        num_hands=num_hands,
        blind_structure=blind_structure,
        small_blind=small_blind,
        big_blind=big_blind,
        show_archetypes=show_archetypes,
    )

    display_table_setup(config)
    return config


def display_table_setup(config: SessionConfig) -> None:
    """Display the configured table as a rich table."""
    table = Table(title="Table Setup")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Players", str(config.num_players))
    table.add_row("Strong NPCs", str(config.strong_players))
    table.add_row("Weak NPCs", str(config.weak_players))
    table.add_row("Starting Stack", str(config.starting_stack))
    table.add_row("Hands", str(config.num_hands))
    table.add_row("Blinds", f"{config.small_blind}/{config.big_blind} ({config.blind_structure})")
    table.add_row("Show Archetypes", str(config.show_archetypes))
    table.add_row("Seed", config.seed)

    console.print(table)


def display_game_state(
    hero_cards: list[Card],
    community_cards: list[Card],
    pot: int,
    players_info: list[dict],
    hero_stack: int,
    hero_position: str,
    show_archetypes: bool,
) -> None:
    """Display the current game state."""
    console.print()

    # Player table
    table = Table(title="Table")
    table.add_column("Seat", style="cyan")
    table.add_column("Position", style="yellow")
    if show_archetypes:
        table.add_column("Type", style="magenta")
    table.add_column("Stack", style="green")
    table.add_column("Bet", style="red")
    table.add_column("Status")

    for p in players_info:
        row = [str(p["seat"]), p["position"]]
        if show_archetypes:
            row.append(p["archetype"])
        row.extend([str(p["stack"]), str(p["current_bet"]), p["status"]])
        table.add_row(*row)

    console.print(table)
    console.print(f"[bold]Pot:[/bold] {pot}")

    if community_cards:
        console.print(f"[bold]Board:[/bold] {format_cards(community_cards)}")

    console.print(f"[bold]Your cards ({hero_position}):[/bold] {format_cards(hero_cards)}")
    console.print(f"[bold]Your stack:[/bold] {hero_stack}")
    console.print()


def get_user_action() -> str:
    """Prompt user for their action."""
    return click.prompt(">", type=str)


def display_coach_message(message: str) -> None:
    """Display a coach message."""
    console.print(f"\n[bold blue]Coach:[/bold blue] {message}\n")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/cli.py tests/test_cli.py
git commit -m "feat: CLI interface with rich formatting and interactive config"
```

---

### Task 10: AI Coach — Prompt and Evaluator

**Files:**
- Create: `poker_coach/coach/prompt.py`
- Create: `poker_coach/coach/evaluator.py`
- Create: `tests/coach/test_prompt.py`
- Create: `tests/coach/test_evaluator.py`

**Step 1: Write failing tests for prompt**

```python
# tests/coach/test_prompt.py
from poker_coach.coach.prompt import build_system_prompt, format_state_for_coach


class TestBuildSystemPrompt:
    def test_contains_coaching_rules(self):
        prompt = build_system_prompt(show_archetypes=True)
        assert "pot odds" in prompt.lower()
        assert "sizing" in prompt.lower()
        assert "never agree with a bad play" in prompt.lower()

    def test_archetype_instructions_included(self):
        prompt = build_system_prompt(show_archetypes=True)
        assert "archetype" in prompt.lower()

    def test_archetype_instructions_excluded(self):
        prompt = build_system_prompt(show_archetypes=False)
        assert "do not reference archetypes" in prompt.lower() or "archetype" not in prompt.lower()


class TestFormatState:
    def test_format_state(self):
        state_dict = {
            "hand_number": 1,
            "street": "flop",
            "hero_position": "BTN",
            "hero_cards": ["Ah", "Kd"],
            "community_cards": ["9c", "3h", "Jd"],
            "pot": 145,
            "hero_stack": 480,
            "players": [
                {"seat": 1, "name": "NPC1", "archetype": "weak", "position": "SB", "stack": 420, "status": "active", "current_bet": 0},
            ],
            "current_bet": 0,
            "min_raise": 10,
        }
        result = format_state_for_coach(state_dict)
        assert "Ah" in result
        assert "flop" in result.lower()
        assert "145" in result
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/coach/test_prompt.py -v`
Expected: FAIL

**Step 3: Write prompt implementation**

```python
# poker_coach/coach/prompt.py
from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT_BASE = """\
You are a poker coach providing real-time feedback during a No Limit Hold'em session. \
You are direct, critical, and never sugarcoat mistakes.

RULES — follow these strictly:
- Never agree with a bad play to be encouraging
- Always correct terminology errors (bet vs raise vs c-bet etc.)
- Always show pot odds math when a call decision is involved
- Always count outs explicitly when a draw is involved
- Call out sizing leaks — name the correct size and explain why
- Track recurring mistakes and flag patterns
- When asked "what do you do and why?", wait for the user's answer before giving your recommendation

SCORING DIMENSIONS (track silently):
- Hand selection: preflop decisions relative to position
- Bet sizing: appropriate sizing for value/protection/draws
- Position awareness: adjusting based on position
- Hand reading: opponent range assessment
- Pot odds / math: correct call/fold decisions
- Discipline: folding when behind, avoiding tilt
- Aggression: semi-bluffs, value bets, pressure plays

Score each dimension A/B/C/D per hand. You will be asked for a final summary at session end.
"""

ARCHETYPE_INSTRUCTIONS = """
ARCHETYPES:
- Reference player archetypes by behavior (not seat number) when describing opponents
- Use archetype knowledge to inform coaching advice (e.g., "this player is a fish, size bigger for value")
"""

NO_ARCHETYPE_INSTRUCTIONS = """
Do not reference player archetypes directly. Describe opponent tendencies based on observed actions only.
"""


def build_system_prompt(show_archetypes: bool) -> str:
    base = SYSTEM_PROMPT_BASE
    if show_archetypes:
        base += ARCHETYPE_INSTRUCTIONS
    else:
        base += NO_ARCHETYPE_INSTRUCTIONS
    return base


def format_state_for_coach(state_dict: dict[str, Any]) -> str:
    """Format game state dict as a readable string for the coach prompt."""
    lines = [
        f"Hand #{state_dict['hand_number']} — {state_dict['street'].upper()}",
        f"Your position: {state_dict['hero_position']}",
        f"Your cards: {' '.join(state_dict['hero_cards'])}",
    ]

    if state_dict["community_cards"]:
        lines.append(f"Board: {' '.join(state_dict['community_cards'])}")

    lines.append(f"Pot: {state_dict['pot']}")
    lines.append(f"Your stack: {state_dict['hero_stack']}")
    lines.append("")
    lines.append("Opponents:")

    for p in state_dict["players"]:
        line = f"  Seat {p['seat']} ({p['position']}) — {p['archetype']} — stack: {p['stack']} — bet: {p['current_bet']} — {p['status']}"
        lines.append(line)

    lines.append(f"\nCurrent bet to match: {state_dict['current_bet']}")
    lines.append(f"Min raise: {state_dict['min_raise']}")

    return "\n".join(lines)
```

**Step 4: Write failing tests for evaluator**

```python
# tests/coach/test_evaluator.py
from poker_coach.coach.evaluator import SessionScorer


class TestSessionScorer:
    def test_initial_scores_empty(self):
        scorer = SessionScorer()
        assert scorer.hand_count == 0

    def test_record_hand_scores(self):
        scorer = SessionScorer()
        scorer.record_hand({
            "hand_selection": "B",
            "bet_sizing": "C",
            "position_awareness": "A",
            "hand_reading": "B",
            "pot_odds": "B",
            "discipline": "A",
            "aggression": "B",
        })
        assert scorer.hand_count == 1

    def test_final_grades(self):
        scorer = SessionScorer()
        for _ in range(3):
            scorer.record_hand({
                "hand_selection": "B",
                "bet_sizing": "C",
                "position_awareness": "A",
                "hand_reading": "B",
                "pot_odds": "B",
                "discipline": "A",
                "aggression": "B",
            })
        grades = scorer.final_grades()
        assert "hand_selection" in grades
        assert "bet_sizing" in grades
```

**Step 5: Write evaluator implementation**

```python
# poker_coach/coach/evaluator.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

GRADE_VALUES = {"A": 4, "B": 3, "C": 2, "D": 1}
VALUE_GRADES = {4: "A", 3: "B", 2: "C", 1: "D"}

DIMENSIONS = [
    "hand_selection",
    "bet_sizing",
    "position_awareness",
    "hand_reading",
    "pot_odds",
    "discipline",
    "aggression",
]


class SessionScorer:
    def __init__(self) -> None:
        self.scores: dict[str, list[str]] = defaultdict(list)
        self.hand_count = 0

    def record_hand(self, grades: dict[str, str]) -> None:
        self.hand_count += 1
        for dim in DIMENSIONS:
            if dim in grades:
                self.scores[dim].append(grades[dim])

    def final_grades(self) -> dict[str, str]:
        result = {}
        for dim in DIMENSIONS:
            if self.scores[dim]:
                avg = sum(GRADE_VALUES.get(g, 2) for g in self.scores[dim]) / len(self.scores[dim])
                rounded = round(avg)
                result[dim] = VALUE_GRADES.get(rounded, "C")
            else:
                result[dim] = "N/A"
        return result

    def overall_grade(self) -> str:
        grades = self.final_grades()
        values = [GRADE_VALUES.get(g, 2) for g in grades.values() if g != "N/A"]
        if not values:
            return "N/A"
        avg = sum(values) / len(values)
        return VALUE_GRADES.get(round(avg), "C")
```

**Step 6: Run all tests**

Run: `uv run pytest tests/coach/ -v`
Expected: all PASS

**Step 7: Commit**

```bash
git add poker_coach/coach/prompt.py poker_coach/coach/evaluator.py tests/coach/test_prompt.py tests/coach/test_evaluator.py
git commit -m "feat: AI coach system prompt, state formatter, and session scoring"
```

---

### Task 11: Session Log Writer

**Files:**
- Create: `poker_coach/coach/session_log.py`
- Create: `tests/coach/test_session_log.py`

**Step 1: Write failing tests**

```python
# tests/coach/test_session_log.py
import os
import tempfile

from poker_coach.coach.session_log import SessionLogger


class TestSessionLogger:
    def test_creates_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="abc123",
                starting_stack=500,
                config_summary={"players": 6, "blinds": "5/10"},
            )
            logger.add_hand_log(
                hand_number=1,
                position="BTN",
                hero_cards="A♠ K♦",
                log_text="Raised preflop, won pot.",
            )
            logger.set_final_results(
                ending_stack=600,
                grades={"hand_selection": "B", "bet_sizing": "C"},
                overall_grade="B",
                leaks=["Bet sizing too small"],
                strengths=["Good hand selection"],
            )
            path = logger.write()
            assert os.path.exists(path)
            assert "abc123" in path

    def test_log_contains_hand(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="abc123",
                starting_stack=500,
                config_summary={"players": 6, "blinds": "5/10"},
            )
            logger.add_hand_log(1, "BTN", "A♠ K♦", "Test hand log")
            logger.set_final_results(600, {}, "B", [], [])
            path = logger.write()

            with open(path) as f:
                content = f.read()
            assert "Hand 1" in content
            assert "Test hand log" in content
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/coach/test_session_log.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# poker_coach/coach/session_log.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class HandEntry:
    hand_number: int
    position: str
    hero_cards: str
    log_text: str


class SessionLogger:
    def __init__(
        self,
        output_dir: str,
        seed: str,
        starting_stack: int,
        config_summary: dict[str, Any],
    ) -> None:
        self.output_dir = output_dir
        self.seed = seed
        self.starting_stack = starting_stack
        self.config_summary = config_summary
        self.hands: list[HandEntry] = []
        self.ending_stack = 0
        self.grades: dict[str, str] = {}
        self.overall_grade = "N/A"
        self.leaks: list[str] = []
        self.strengths: list[str] = []

    def add_hand_log(
        self, hand_number: int, position: str, hero_cards: str, log_text: str
    ) -> None:
        self.hands.append(HandEntry(hand_number, position, hero_cards, log_text))

    def set_final_results(
        self,
        ending_stack: int,
        grades: dict[str, str],
        overall_grade: str,
        leaks: list[str],
        strengths: list[str],
    ) -> None:
        self.ending_stack = ending_stack
        self.grades = grades
        self.overall_grade = overall_grade
        self.leaks = leaks
        self.strengths = strengths

    def write(self) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        now = datetime.now()
        filename = f"{now.strftime('%Y-%m-%d_%H-%M')}_{self.seed}.md"
        path = os.path.join(self.output_dir, filename)

        net = self.ending_stack - self.starting_stack
        sign = "+" if net >= 0 else ""

        lines = [
            "# Poker Coach Session",
            f"**Date:** {now.strftime('%Y-%m-%d')}",
            f"**Hands played:** {len(self.hands)}",
            f"**Starting stack:** ${self.starting_stack}",
            f"**Ending stack:** ${self.ending_stack}",
            f"**Net:** {sign}${net}",
            f"**RNG Seed:** {self.seed}",
            "",
            "## Table Configuration",
        ]

        for key, value in self.config_summary.items():
            lines.append(f"- {key}: {value}")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Hand Log")
        lines.append("")

        for hand in self.hands:
            lines.append(f"### Hand {hand.hand_number}")
            lines.append(f"**Position:** {hand.position} | **Cards:** {hand.hero_cards}")
            lines.append("")
            lines.append(hand.log_text)
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## Session Review")
        lines.append("")
        lines.append("### Performance Summary")
        lines.append("")
        lines.append("| Dimension | Grade |")
        lines.append("|---|---|")
        for dim, grade in self.grades.items():
            lines.append(f"| {dim.replace('_', ' ').title()} | {grade} |")

        lines.append("")
        lines.append(f"### Overall Grade: {self.overall_grade}")
        lines.append("")

        if self.leaks:
            lines.append("### Key Leaks")
            for i, leak in enumerate(self.leaks, 1):
                lines.append(f"{i}. {leak}")
            lines.append("")

        if self.strengths:
            lines.append("### Strengths")
            for i, strength in enumerate(self.strengths, 1):
                lines.append(f"{i}. {strength}")
            lines.append("")

        with open(path, "w") as f:
            f.write("\n".join(lines))

        return path
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/coach/test_session_log.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/coach/session_log.py tests/coach/test_session_log.py
git commit -m "feat: session log writer with markdown output"
```

---

### Task 12: Game Loop Integration

**Files:**
- Modify: `poker_coach/main.py`
- Create: `poker_coach/game_loop.py`
- Create: `tests/test_game_loop.py`

This is the core integration task. The game loop orchestrates: config -> deal -> NPC actions -> hero prompt -> coach evaluation -> resolution -> next street/hand.

**Step 1: Write failing tests**

```python
# tests/test_game_loop.py
import random
from unittest.mock import MagicMock, patch

from poker_coach.config import SessionConfig
from poker_coach.game_loop import GameLoop


class TestGameLoop:
    def test_creates_players(self):
        config = SessionConfig(num_players=4, strong_players=1, seed="test123")
        loop = GameLoop(config)
        assert len(loop.game_state.players) == 4
        assert loop.game_state.players[0].archetype == "hero"
        # 1 strong + 2 weak
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_game_loop.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# poker_coach/game_loop.py
from __future__ import annotations

import random
from typing import Any

from poker_coach.config import SessionConfig
from poker_coach.engine.deck import Card
from poker_coach.engine.game_state import GameState
from poker_coach.engine.hand_eval import determine_winners
from poker_coach.engine.npc import resolve_npc_action
from poker_coach.engine.player import Player


class GameLoop:
    def __init__(self, config: SessionConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.hero_seat = 0

        # Build players
        players = [Player(seat=0, name="Hero", archetype="hero", stack=config.starting_stack)]
        npc_num = 1
        for _ in range(config.strong_players):
            stack = self._get_npc_stack()
            players.append(Player(seat=npc_num, name=f"NPC{npc_num}", archetype="strong", stack=stack))
            npc_num += 1
        for _ in range(config.weak_players):
            stack = self._get_npc_stack()
            players.append(Player(seat=npc_num, name=f"NPC{npc_num}", archetype="weak", stack=stack))
            npc_num += 1

        self.game_state = GameState(
            players=players,
            small_blind=config.small_blind,
            big_blind=config.big_blind,
            rng=self.rng,
        )

    def _get_npc_stack(self) -> int:
        if self.config.stack_mode == "range":
            return self.rng.randint(self.config.stack_range_min, self.config.stack_range_max)
        return self.config.starting_stack

    def start_hand(self) -> dict[str, Any]:
        """Start a new hand. Returns the game state dict for the coach."""
        self.game_state.start_hand()
        return self.game_state.to_dict(hero_seat=self.hero_seat)

    def get_preflop_action_order(self) -> list[int]:
        """Return seat indices in preflop action order (UTG first, BB last)."""
        positions = self.game_state.get_positions()
        num = len(self.game_state.players)

        # Find BB index
        bb_idx = positions.index("BB")
        # Action starts left of BB
        order = []
        for i in range(1, num):
            seat = (bb_idx + i) % num
            order.append(seat)
        order.append(bb_idx)  # BB acts last preflop
        return order

    def get_postflop_action_order(self) -> list[int]:
        """Return seat indices in postflop action order (SB first, BTN last)."""
        positions = self.game_state.get_positions()
        num = len(self.game_state.players)

        # Find SB (or BB for 2-player)
        if num == 2:
            btn_idx = positions.index("BTN")
            other = (btn_idx + 1) % num
            return [other, btn_idx]

        sb_idx = positions.index("SB")
        order = []
        for i in range(num):
            seat = (sb_idx + i) % num
            order.append(seat)
        return order

    def get_action_order(self) -> list[int]:
        if self.game_state.street == "preflop":
            return self.get_preflop_action_order()
        return self.get_postflop_action_order()

    def resolve_npc_actions_until_hero(self) -> list[dict[str, Any]]:
        """Resolve NPC actions in order until it's hero's turn. Returns action log."""
        order = self.get_action_order()
        actions = []
        positions = self.game_state.get_positions()

        for seat in order:
            player = self.game_state.players[seat]
            if player.has_folded or player.is_all_in:
                continue
            if seat == self.hero_seat:
                break  # Hero's turn

            action = resolve_npc_action(
                player=player,
                street=self.game_state.street,
                current_bet=self.game_state.current_bet,
                pot=self.game_state.pot,
                community_cards=self.game_state.community_cards,
                rng=self.rng,
                position=positions[seat],
            )

            self._apply_action(player, action.action, action.amount)
            actions.append({
                "seat": seat,
                "name": player.name,
                "action": action.action,
                "amount": action.amount,
            })

        return actions

    def resolve_npc_actions_after_hero(self) -> list[dict[str, Any]]:
        """Resolve remaining NPC actions after hero has acted."""
        order = self.get_action_order()
        actions = []
        positions = self.game_state.get_positions()

        hero_found = False
        for seat in order:
            player = self.game_state.players[seat]
            if seat == self.hero_seat:
                hero_found = True
                continue
            if not hero_found:
                continue
            if player.has_folded or player.is_all_in:
                continue

            action = resolve_npc_action(
                player=player,
                street=self.game_state.street,
                current_bet=self.game_state.current_bet,
                pot=self.game_state.pot,
                community_cards=self.game_state.community_cards,
                rng=self.rng,
                position=positions[seat],
            )

            self._apply_action(player, action.action, action.amount)
            actions.append({
                "seat": seat,
                "name": player.name,
                "action": action.action,
                "amount": action.amount,
            })

        return actions

    def apply_hero_action(self, action: str, amount: int = 0) -> None:
        """Apply the hero's chosen action."""
        hero = self.game_state.players[self.hero_seat]
        self._apply_action(hero, action, amount)

    def _apply_action(self, player: Player, action: str, amount: int) -> None:
        if action == "fold":
            player.fold()
        elif action == "call":
            to_call = self.game_state.current_bet - player.current_bet
            actual = player.place_bet(to_call)
            self.game_state.pot += actual
        elif action == "raise":
            # Amount is total bet size
            to_put_in = amount - player.current_bet
            actual = player.place_bet(to_put_in)
            self.game_state.pot += actual
            self.game_state.current_bet = player.current_bet
            self.game_state.min_raise = amount
        elif action == "check":
            pass

    def is_hand_over(self) -> bool:
        active = self.game_state.get_active_players()
        return len(active) <= 1

    def resolve_winners(self) -> list[Player]:
        active = self.game_state.get_active_players()
        if len(active) == 1:
            winner = active[0]
            winner.stack += self.game_state.pot
            return [winner]
        return determine_winners(active, self.game_state.community_cards)

    def advance_street(self) -> dict[str, Any]:
        self.game_state.advance_street()
        return self.game_state.to_dict(hero_seat=self.hero_seat)

    def end_hand(self) -> None:
        self.game_state.advance_button()

    def should_escalate_blinds(self) -> bool:
        if self.config.blind_structure != "escalating":
            return False
        return self.game_state.hand_number % self.config.escalation_interval == 0

    def escalate_blinds(self) -> None:
        self.game_state.small_blind *= 2
        self.game_state.big_blind *= 2
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_game_loop.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/game_loop.py tests/test_game_loop.py
git commit -m "feat: game loop with action ordering, NPC resolution, and street management"
```

---

### Task 13: Claude API Coach Integration

**Files:**
- Create: `poker_coach/coach/api.py`
- Create: `tests/coach/test_api.py`

**Step 1: Write failing tests**

```python
# tests/coach/test_api.py
from unittest.mock import MagicMock, patch

from poker_coach.coach.api import CoachClient


class TestCoachClient:
    def test_init(self):
        client = CoachClient(show_archetypes=True)
        assert client.conversation_history == []

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_narrate_calls_api(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Coach says hello")]
        mock_client.messages.create.return_value = mock_response

        client = CoachClient(show_archetypes=True)
        result = client.get_coaching(
            state_text="Hand #1 — PREFLOP\nYour cards: Ah Kd",
            user_message=None,
        )
        assert "Coach says hello" in result
        assert mock_client.messages.create.called

    def test_reset_hand_clears_history(self):
        client = CoachClient(show_archetypes=True)
        client.conversation_history = [{"role": "user", "content": "test"}]
        client.reset_hand()
        assert client.conversation_history == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/coach/test_api.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# poker_coach/coach/api.py
from __future__ import annotations

from typing import Any

import anthropic

from poker_coach.coach.prompt import build_system_prompt, format_state_for_coach


class CoachClient:
    def __init__(self, show_archetypes: bool, model: str = "claude-sonnet-4-20250514") -> None:
        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = build_system_prompt(show_archetypes)
        self.conversation_history: list[dict[str, str]] = []
        self.hand_summaries: list[str] = []

    def get_coaching(
        self,
        state_text: str,
        user_message: str | None = None,
    ) -> str:
        """Get coaching response. Streams to console and returns full text."""
        if user_message:
            content = f"Game state:\n{state_text}\n\nUser response: {user_message}"
        else:
            content = f"Game state:\n{state_text}\n\nNarrate the situation and ask what I would do and why."

        self.conversation_history.append({"role": "user", "content": content})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.conversation_history,
        )

        reply = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": reply})
        return reply

    def get_coaching_stream(
        self,
        state_text: str,
        user_message: str | None = None,
    ):
        """Get coaching response as a stream."""
        if user_message:
            content = f"Game state:\n{state_text}\n\nUser response: {user_message}"
        else:
            content = f"Game state:\n{state_text}\n\nNarrate the situation and ask what I would do and why."

        self.conversation_history.append({"role": "user", "content": content})

        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.conversation_history,
        ) as stream:
            full_text = ""
            for text in stream.text_stream:
                yield text
                full_text += text

        self.conversation_history.append({"role": "assistant", "content": full_text})

    def get_final_review(self, session_summary: str) -> str:
        """Get the final session review from the coach."""
        content = (
            f"The session is over. Here is the session summary:\n\n{session_summary}\n\n"
            "Please provide:\n"
            "1. A grade (A/B/C/D) for each scoring dimension with a one-line pattern summary\n"
            "2. An overall session grade\n"
            "3. Top 3 leaks\n"
            "4. Top 3 strengths\n"
            "Format as a clear, structured review."
        )
        self.conversation_history.append({"role": "user", "content": content})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=self.conversation_history,
        )

        reply = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": reply})
        return reply

    def reset_hand(self) -> None:
        """Reset conversation history between hands, keeping a summary."""
        if self.conversation_history:
            # Summarize the hand briefly
            last_assistant = [
                m["content"]
                for m in self.conversation_history
                if m["role"] == "assistant"
            ]
            if last_assistant:
                self.hand_summaries.append(last_assistant[-1][:200])
        self.conversation_history = []

        # Inject hand summaries as context
        if self.hand_summaries:
            summary = "Previous hands summary:\n" + "\n---\n".join(self.hand_summaries[-5:])
            self.conversation_history.append({"role": "user", "content": summary})
            self.conversation_history.append({"role": "assistant", "content": "Understood. I have context from the previous hands. Let's continue."})
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/coach/test_api.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add poker_coach/coach/api.py tests/coach/test_api.py
git commit -m "feat: Claude API coach client with streaming and session history"
```

---

### Task 14: Main Entry Point — Full Session

**Files:**
- Modify: `poker_coach/main.py`

**Step 1: Write the full main.py integration**

```python
# poker_coach/main.py
from __future__ import annotations

import sys

import click
from rich.console import Console

from poker_coach.cli import (
    configure_session,
    display_coach_message,
    display_game_state,
    display_table_setup,
    format_cards,
    get_user_action,
    console,
)
from poker_coach.coach.api import CoachClient
from poker_coach.coach.prompt import format_state_for_coach
from poker_coach.coach.session_log import SessionLogger
from poker_coach.config import SessionConfig
from poker_coach.game_loop import GameLoop


def parse_user_action(text: str, game_state_dict: dict) -> tuple[str, int]:
    """Parse natural language action into (action, amount)."""
    text = text.strip().lower()
    if text.startswith("fold"):
        return ("fold", 0)
    if text.startswith("check"):
        return ("check", 0)
    if text.startswith("call"):
        return ("call", game_state_dict["current_bet"])
    if text.startswith("raise") or text.startswith("bet"):
        parts = text.split()
        for part in parts:
            if part == "to":
                continue
            try:
                amount = int(part)
                return ("raise", amount)
            except ValueError:
                continue
        # Default raise to 2x current bet or min raise
        return ("raise", max(game_state_dict["current_bet"] * 2, game_state_dict["min_raise"] * 2))
    if text.startswith("all"):
        return ("raise", game_state_dict["hero_stack"] + game_state_dict["current_bet"])
    return ("check", 0)


def run_session(config: SessionConfig) -> None:
    """Run a complete poker coaching session."""
    loop = GameLoop(config)
    coach = CoachClient(show_archetypes=config.show_archetypes)
    logger = SessionLogger(
        output_dir="sessions",
        seed=config.seed,
        starting_stack=config.starting_stack,
        config_summary={
            "Players": f"{config.num_players} ({config.strong_players} strong, {config.weak_players} weak)",
            "Blinds": f"{config.small_blind}/{config.big_blind} ({config.blind_structure})",
            "Starting Stack": config.starting_stack,
        },
    )

    console.print(f"\n[bold green]Starting session with seed: {config.seed}[/bold green]\n")

    for hand_num in range(1, config.num_hands + 1):
        console.rule(f"[bold]Hand {hand_num} of {config.num_hands}[/bold]")

        # Check blind escalation
        if loop.should_escalate_blinds():
            loop.escalate_blinds()
            console.print(f"[yellow]Blinds escalated to {loop.game_state.small_blind}/{loop.game_state.big_blind}[/yellow]")

        # Start hand
        state_dict = loop.start_hand()
        hand_log_parts: list[str] = []

        # Process each street
        while loop.game_state.street != "showdown":
            # Resolve NPC actions before hero
            npc_actions = loop.resolve_npc_actions_until_hero()
            for a in npc_actions:
                action_text = f"{a['name']} {a['action']}s"
                if a['amount'] > 0:
                    action_text += f" to {a['amount']}"
                console.print(f"  {action_text}")
                hand_log_parts.append(action_text)

            # Check if hand is over (everyone folded)
            if loop.is_hand_over():
                break

            # Update state for coach
            state_dict = loop.game_state.to_dict(hero_seat=loop.hero_seat)

            # Display game state
            display_game_state(
                hero_cards=loop.game_state.players[loop.hero_seat].hole_cards,
                community_cards=loop.game_state.community_cards,
                pot=loop.game_state.pot,
                players_info=state_dict["players"],
                hero_stack=state_dict["hero_stack"],
                hero_position=state_dict["hero_position"],
                show_archetypes=config.show_archetypes,
            )

            # Get coach narration
            state_text = format_state_for_coach(state_dict)
            console.print("[bold blue]Coach:[/bold blue] ", end="")
            for chunk in coach.get_coaching_stream(state_text):
                console.print(chunk, end="")
            console.print()

            # Check if hero can act (might have folded or be all-in)
            hero = loop.game_state.players[loop.hero_seat]
            if hero.has_folded or hero.is_all_in:
                # Resolve remaining NPCs and advance
                loop.resolve_npc_actions_after_hero()
                if not loop.is_hand_over() and loop.game_state.street != "showdown":
                    loop.advance_street()
                continue

            # Get hero action
            user_input = get_user_action()
            action, amount = parse_user_action(user_input, state_dict)

            # Validate action
            hero = loop.game_state.players[loop.hero_seat]
            to_call = loop.game_state.current_bet - hero.current_bet
            if action == "check" and to_call > 0:
                console.print("[red]You can't check — there's a bet to you. Call, raise, or fold.[/red]")
                user_input = get_user_action()
                action, amount = parse_user_action(user_input, state_dict)

            # Apply hero action
            loop.apply_hero_action(action, amount)
            action_text = f"Hero {action}s"
            if amount > 0:
                action_text += f" to {amount}"
            hand_log_parts.append(action_text)

            # Get coach evaluation of hero's action
            state_dict = loop.game_state.to_dict(hero_seat=loop.hero_seat)
            state_text = format_state_for_coach(state_dict)
            console.print("[bold blue]Coach:[/bold blue] ", end="")
            for chunk in coach.get_coaching_stream(state_text, user_message=f"I {action} {f'to {amount}' if amount else ''}. {user_input}"):
                console.print(chunk, end="")
            console.print()

            # Resolve NPC actions after hero
            npc_actions = loop.resolve_npc_actions_after_hero()
            for a in npc_actions:
                action_text = f"{a['name']} {a['action']}s"
                if a['amount'] > 0:
                    action_text += f" to {a['amount']}"
                console.print(f"  {action_text}")
                hand_log_parts.append(action_text)

            if loop.is_hand_over():
                break

            # Advance to next street
            if loop.game_state.street != "showdown":
                state_dict = loop.advance_street()

        # Resolve winners
        winners = loop.resolve_winners()
        winner_names = ", ".join(w.name for w in winners)
        console.print(f"\n[bold green]Winner(s): {winner_names} — Pot: {loop.game_state.pot}[/bold green]")

        hero_stack = loop.game_state.players[loop.hero_seat].stack
        console.print(f"[bold]Your stack: {hero_stack}[/bold]\n")

        hero_cards = format_cards(loop.game_state.players[loop.hero_seat].hole_cards)
        logger.add_hand_log(
            hand_number=hand_num,
            position=state_dict.get("hero_position", "?"),
            hero_cards=hero_cards,
            log_text="\n".join(hand_log_parts),
        )

        # Reset coach for next hand
        coach.reset_hand()
        loop.end_hand()

    # Final review
    console.rule("[bold]Session Review[/bold]")
    hero_final_stack = loop.game_state.players[loop.hero_seat].stack
    session_summary = (
        f"Started with {config.starting_stack}, ended with {hero_final_stack}. "
        f"Net: {hero_final_stack - config.starting_stack}. "
        f"Played {config.num_hands} hands."
    )

    review = coach.get_final_review(session_summary)
    console.print(f"\n[bold blue]Coach:[/bold blue]\n{review}\n")

    # Write session log
    logger.set_final_results(
        ending_stack=hero_final_stack,
        grades={},
        overall_grade="",
        leaks=[],
        strengths=[],
    )
    log_path = logger.write()
    console.print(f"[green]Session log saved to: {log_path}[/green]")


@click.command()
@click.option("--seed", default=None, help="RNG seed for reproducibility")
def main(seed: str | None) -> None:
    """Poker Coach — AI-powered No Limit Hold'em training."""
    console.print("[bold]Welcome to Poker Coach![/bold]\n")

    # Get config interactively
    config = SessionConfig()

    # Override seed if provided
    if seed:
        config.seed = seed

    # Interactive configuration
    config.num_players = click.prompt("Number of players (2-9)", default=config.num_players, type=int)
    config.strong_players = click.prompt("Strong players", default=config.strong_players, type=int)
    config.starting_stack = click.prompt("Starting stack", default=config.starting_stack, type=int)
    config.num_hands = click.prompt("Number of hands (5-50)", default=config.num_hands, type=int)
    config.blind_structure = click.prompt("Blind structure (fixed/escalating)", default=config.blind_structure, type=str)
    config.small_blind = click.prompt("Small blind", default=config.small_blind, type=int)
    config.big_blind = click.prompt("Big blind", default=config.big_blind, type=int)
    config.show_archetypes = click.prompt("Show archetypes", default=config.show_archetypes, type=bool)

    display_table_setup(config)

    if not click.confirm("Start session?", default=True):
        console.print("Session cancelled.")
        return

    run_session(config)


if __name__ == "__main__":
    main()
```

**Step 2: Run smoke test**

Run: `uv run python -m poker_coach.main --help`
Expected: shows help text

**Step 3: Commit**

```bash
git add poker_coach/main.py
git commit -m "feat: full game session integration with coaching loop"
```

---

### Task 15: End-to-End Manual Test and Polish

**Step 1: Run the full test suite**

Run: `uv run pytest tests/ -v`
Expected: all PASS

**Step 2: Run a quick manual test** (requires ANTHROPIC_API_KEY)

Run: `uv run python -m poker_coach.main --seed test123`
Expected: interactive session starts, prompts for config, deals cards, coach responds

**Step 3: Fix any issues found during manual testing**

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: polish and bug fixes from manual testing"
```

---

## Dependency Graph

```
Task 1 (scaffolding)
  └── Task 2 (deck/card)
       ├── Task 3 (hand eval)
       │    └── Task 8 (winner resolution)
       └── Task 4 (positions)
            └── Task 5 (game state) ← also depends on Task 2
                 └── Task 6 (NPC) ← also depends on Task 2
                      └── Task 12 (game loop) ← depends on 3,5,6,7,8
  Task 7 (config) — independent after Task 1
  Task 9 (CLI) — depends on Task 2, Task 7
  Task 10 (coach prompt/eval) — independent after Task 1
  Task 11 (session log) — independent after Task 1
  Task 13 (coach API) — depends on Task 10
  Task 14 (main integration) — depends on ALL above
  Task 15 (polish) — depends on Task 14
```

Parallelizable groups:
- After Task 1: Tasks 7, 10, 11 can run in parallel
- After Task 2: Tasks 3, 4 can run in parallel
- After Task 5: Task 6 and Task 9 can run in parallel
