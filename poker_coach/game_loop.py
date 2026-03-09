"""Game loop orchestration for poker coaching sessions."""

import random
from typing import Any

from poker_coach.config import SessionConfig
from poker_coach.engine.game_state import GameState
from poker_coach.engine.hand_eval import determine_winners
from poker_coach.engine.npc import resolve_npc_action
from poker_coach.engine.player import Player


class GameLoop:
    """Orchestrates a poker session: player creation, hand flow, NPC actions,
    hero actions, street advancement, winner resolution, and blind escalation."""

    def __init__(self, config: SessionConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.hero_seat = 0

        # Build players: hero at seat 0, then strong NPCs, then weak NPCs
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
        """Start a new hand and return the game state dict."""
        self.game_state.start_hand()
        return self.game_state.to_dict(hero_seat=self.hero_seat)

    def get_preflop_action_order(self) -> list[int]:
        """Preflop: UTG first, BB last."""
        positions = self.game_state.get_positions()
        num = len(self.game_state.players)
        bb_idx = positions.index("BB")
        order = []
        for i in range(1, num):
            seat = (bb_idx + i) % num
            order.append(seat)
        order.append(bb_idx)
        return order

    def get_postflop_action_order(self) -> list[int]:
        """Postflop: SB first (or BB for heads-up), BTN last."""
        positions = self.game_state.get_positions()
        num = len(self.game_state.players)
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
        """Return the action order for the current street."""
        if self.game_state.street == "preflop":
            return self.get_preflop_action_order()
        return self.get_postflop_action_order()

    def _can_act(self, player: Player) -> bool:
        """Check if a player can act (active, not folded, not all-in, has cards)."""
        return (
            player.is_active
            and not player.has_folded
            and not player.is_all_in
            and len(player.hole_cards) > 0
        )

    def _resolve_single_npc(self, seat: int) -> dict[str, Any] | None:
        """Resolve a single NPC action. Returns action dict or None if skipped."""
        player = self.game_state.players[seat]
        if not self._can_act(player) or seat == self.hero_seat:
            return None
        positions = self.game_state.get_positions()
        action = resolve_npc_action(
            player=player,
            street=self.game_state.street,
            current_bet=self.game_state.current_bet,
            pot=self.game_state.pot,
            community_cards=self.game_state.community_cards,
            rng=self.rng,
            position=positions[seat],
            big_blind=self.game_state.big_blind,
        )
        self._apply_action(player, action.action, action.amount)
        return {
            "seat": seat,
            "name": player.name,
            "action": action.action,
            "amount": action.amount,
        }

    def resolve_npc_actions_until_hero(self) -> list[dict[str, Any]]:
        """Resolve NPC actions in order until hero's turn. Returns action log."""
        order = self.get_action_order()
        actions: list[dict[str, Any]] = []
        for seat in order:
            if seat == self.hero_seat:
                break
            result = self._resolve_single_npc(seat)
            if result:
                actions.append(result)
        return actions

    def resolve_npc_actions_after_hero(self) -> list[dict[str, Any]]:
        """Resolve remaining NPC actions after hero acts.

        Loops through all NPCs (starting after hero, wrapping around) until
        every NPC has matched the current bet or folded. Handles re-raise wars
        between NPCs within a single betting round.
        """
        order = self.get_action_order()
        actions: list[dict[str, Any]] = []

        # Build full-circle order starting after hero
        hero_idx = order.index(self.hero_seat)
        rotated = order[hero_idx + 1:] + order[:hero_idx]

        has_acted: set[int] = set()
        max_iterations = 20  # Safety valve
        for _ in range(max_iterations):
            acted_this_round = False
            for seat in rotated:
                player = self.game_state.players[seat]
                if not self._can_act(player):
                    continue
                # Skip if already acted and has matched the current bet
                if seat in has_acted and player.current_bet >= self.game_state.current_bet:
                    continue
                result = self._resolve_single_npc(seat)
                if result:
                    actions.append(result)
                    has_acted.add(seat)
                    if result["action"] == "raise":
                        acted_this_round = True
            if not acted_this_round:
                break

        return actions

    def resolve_full_betting_round_npcs_only(self) -> list[dict[str, Any]]:
        """Resolve a complete NPC-only betting round (when hero has folded or is all-in).

        Loops until all active players have matched the current bet or checked.
        """
        actions: list[dict[str, Any]] = []
        max_iterations = 20  # Safety valve
        for _ in range(max_iterations):
            acted_this_round = False
            order = self.get_action_order()
            for seat in order:
                player = self.game_state.players[seat]
                if not self._can_act(player):
                    continue
                if seat == self.hero_seat:
                    continue
                # Skip if already matched current bet and has acted
                if player.current_bet == self.game_state.current_bet:
                    continue
                result = self._resolve_single_npc(seat)
                if result and result["action"] in ("raise", "call"):
                    actions.append(result)
                    acted_this_round = True
                elif result:
                    actions.append(result)
            if not acted_this_round:
                break
        return actions

    def check_needs_hero_response(self) -> bool:
        """Check if the hero needs to respond to a raise after them."""
        hero = self.game_state.players[self.hero_seat]
        if not self._can_act(hero):
            return False
        return hero.current_bet < self.game_state.current_bet

    def apply_hero_action(self, action: str, amount: int = 0) -> None:
        """Apply the hero's chosen action."""
        hero = self.game_state.players[self.hero_seat]
        self._apply_action(hero, action, amount)

    def _apply_action(self, player: Player, action: str, amount: int) -> None:
        """Apply an action to a player, updating game state."""
        if action == "fold":
            player.fold()
        elif action == "call":
            to_call = self.game_state.current_bet - player.current_bet
            actual = player.place_bet(to_call)
            self.game_state.pot += actual
        elif action == "raise":
            to_put_in = amount - player.current_bet
            actual = player.place_bet(to_put_in)
            self.game_state.pot += actual
            # Only update current_bet upward — an all-in for less
            # shouldn't reduce the bet others face
            if player.current_bet > self.game_state.current_bet:
                self.game_state.current_bet = player.current_bet
                self.game_state.min_raise = amount
        elif action == "check":
            pass

    def is_hand_over(self) -> bool:
        """Check if the hand is over (1 or fewer active players)."""
        active = self.game_state.get_active_players()
        return len(active) <= 1

    def resolve_winners(self) -> list[Player]:
        """Determine and pay winners with side pot support."""
        active = self.game_state.get_active_players()
        if len(active) == 1:
            active[0].stack += self.game_state.pot
            return active

        side_pots = self._calculate_side_pots()
        all_winners: list[Player] = []

        for pot_amount, eligible in side_pots:
            winners = determine_winners(eligible, self.game_state.community_cards)
            share = pot_amount // len(winners)
            for w in winners:
                w.stack += share
                if w not in all_winners:
                    all_winners.append(w)

        return all_winners

    def _calculate_side_pots(self) -> list[tuple[int, list[Player]]]:
        """Calculate side pots based on each player's total investment.

        Returns list of (pot_amount, eligible_players) where eligible_players
        are those who can win that pot (not folded, invested enough).
        """
        all_players = self.game_state.players
        # Players who can win: not folded (includes all-in players)
        not_folded = [p for p in all_players if not p.has_folded and p.total_invested > 0]

        # Get unique investment levels from non-folded players
        investment_levels = sorted(set(p.total_invested for p in not_folded))

        pots: list[tuple[int, list[Player]]] = []
        prev_level = 0
        for level in investment_levels:
            if level <= prev_level:
                continue
            # Each player contributes up to this level
            pot_amount = 0
            for p in all_players:
                contribution = min(p.total_invested, level) - min(p.total_invested, prev_level)
                pot_amount += contribution

            # Only non-folded players who invested at least this level can win
            eligible = [p for p in not_folded if p.total_invested >= level]

            if pot_amount > 0 and eligible:
                pots.append((pot_amount, eligible))
            prev_level = level

        return pots

    def advance_street(self) -> dict[str, Any]:
        """Advance to the next street and return updated game state."""
        self.game_state.advance_street()
        return self.game_state.to_dict(hero_seat=self.hero_seat)

    def end_hand(self) -> None:
        """End the current hand by advancing the button."""
        self.game_state.advance_button()

    def should_escalate_blinds(self) -> bool:
        """Check if blinds should escalate based on config and hand number."""
        if self.config.blind_structure != "escalating":
            return False
        return self.game_state.hand_number % self.config.escalation_interval == 0

    def escalate_blinds(self) -> None:
        """Double the blinds."""
        self.game_state.small_blind *= 2
        self.game_state.big_blind *= 2
