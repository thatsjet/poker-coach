"""Poker Coach — AI-powered No Limit Hold'em training."""

from __future__ import annotations

import click
from rich.console import Console

from poker_coach.cli import (
    console,
    display_coach_message,
    display_game_state,
    display_table_setup,
    format_cards,
    get_user_action,
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
        pot = game_state_dict["pot"]
        # Handle fractional pot sizing — "half pot", "1/2 pot", "2/3 pot", "3/4 pot"
        if "half" in parts:
            return ("raise", pot // 2)
        for part in parts:
            if "/" in part:
                try:
                    num, den = part.split("/")
                    frac = int(num) / int(den)
                    return ("raise", int(pot * frac))
                except (ValueError, ZeroDivisionError):
                    pass
        # Handle bare "pot" keyword — bet/raise the full pot
        if "pot" in parts:
            return ("raise", pot)
        for part in parts:
            if part in ("raise", "bet", "to"):
                continue
            try:
                amount = int(part)
                return ("raise", amount)
            except ValueError:
                continue
        # Default: 2.5x current bet or min raise
        default = max(
            int(game_state_dict["current_bet"] * 2.5),
            game_state_dict["min_raise"] * 2,
        )
        return ("raise", default)
    if text.startswith("all") or text == "shove" or text == "jam":
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
            console.print(
                f"[yellow]Blinds escalated to "
                f"{loop.game_state.small_blind}/{loop.game_state.big_blind}[/yellow]"
            )

        # Start hand
        state_dict = loop.start_hand()
        hand_log_parts: list[str] = []

        # Process each street
        while loop.game_state.street != "showdown":
            # Resolve NPC actions before hero
            npc_actions = loop.resolve_npc_actions_until_hero()
            for a in npc_actions:
                action_text = f"{a['name']} {a['action']}s"
                if a["amount"] > 0:
                    action_text += f" to {a['amount']}"
                console.print(f"  {action_text}")
                hand_log_parts.append(action_text)

            # Check if hand is over (everyone folded to hero)
            if loop.is_hand_over():
                break

            # Update state for display and coach
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

            # Get coach narration (streaming)
            state_text = format_state_for_coach(state_dict)
            console.print("[bold blue]Coach:[/bold blue] ", end="")
            coach_full = ""
            for chunk in coach.get_coaching_stream(state_text):
                console.print(chunk, end="")
                coach_full += chunk
            console.print()

            # Check if hero can act
            hero = loop.game_state.players[loop.hero_seat]
            if hero.has_folded or hero.is_all_in:
                # Hero can't act — resolve rest of NPCs and advance
                npc_actions = loop.resolve_full_betting_round_npcs_only()
                for a in npc_actions:
                    action_text = f"{a['name']} {a['action']}s"
                    if a["amount"] > 0:
                        action_text += f" to {a['amount']}"
                    console.print(f"  {action_text}")
                    hand_log_parts.append(action_text)
                if not loop.is_hand_over() and loop.game_state.street != "showdown":
                    loop.advance_street()
                continue

            # Hero action loop — handles re-raises requiring hero response
            while True:
                # Get hero action — AI parses natural language
                while True:
                    user_input = get_user_action()
                    action, amount = coach.parse_action(user_input, state_dict)
                    console.print(
                        f"[dim]→ {action}"
                        f"{f' to {amount}' if amount > 0 and action not in ('fold', 'check') else ''}"
                        f"[/dim]"
                    )

                    to_call = loop.game_state.current_bet - hero.current_bet
                    if action == "check" and to_call > 0:
                        console.print(
                            "[red]You can't check — there's a bet to you. "
                            "Call, raise, or fold.[/red]"
                        )
                        continue
                    break

                # Apply hero action
                loop.apply_hero_action(action, amount)
                action_desc = f"Hero {action}s"
                if amount > 0 and action != "fold":
                    action_desc += f" to {amount}"
                hand_log_parts.append(action_desc)

                # If hero folded, get brief coach comment and end the hand
                if action == "fold":
                    state_dict = loop.game_state.to_dict(hero_seat=loop.hero_seat)
                    state_text = format_state_for_coach(state_dict)
                    user_msg = f"I fold. {user_input}"
                    console.print("[bold blue]Coach:[/bold blue] ", end="")
                    for chunk in coach.get_coaching_stream(state_text, user_message=user_msg):
                        console.print(chunk, end="")
                    console.print()
                    break

                # Get coach evaluation (streaming)
                state_dict = loop.game_state.to_dict(hero_seat=loop.hero_seat)
                state_text = format_state_for_coach(state_dict)
                user_msg = f"I {action}"
                if amount > 0 and action != "fold":
                    user_msg += f" to {amount}"
                user_msg += f". {user_input}"

                console.print("[bold blue]Coach:[/bold blue] ", end="")
                for chunk in coach.get_coaching_stream(state_text, user_message=user_msg):
                    console.print(chunk, end="")
                console.print()

                if loop.is_hand_over():
                    break

                # Resolve NPC actions after hero
                npc_actions = loop.resolve_npc_actions_after_hero()
                for a in npc_actions:
                    action_text = f"{a['name']} {a['action']}s"
                    if a["amount"] > 0:
                        action_text += f" to {a['amount']}"
                    console.print(f"  {action_text}")
                    hand_log_parts.append(action_text)

                if loop.is_hand_over():
                    break

                # Check if hero needs to respond to a re-raise
                if loop.check_needs_hero_response():
                    state_dict = loop.game_state.to_dict(hero_seat=loop.hero_seat)
                    display_game_state(
                        hero_cards=loop.game_state.players[loop.hero_seat].hole_cards,
                        community_cards=loop.game_state.community_cards,
                        pot=loop.game_state.pot,
                        players_info=state_dict["players"],
                        hero_stack=state_dict["hero_stack"],
                        hero_position=state_dict["hero_position"],
                        show_archetypes=config.show_archetypes,
                    )
                    console.print("[yellow]Action is back to you.[/yellow]")
                    continue
                else:
                    break

            # If hero folded, let NPCs play out remaining streets
            if hero.has_folded:
                while not loop.is_hand_over() and loop.game_state.street != "showdown":
                    npc_actions = loop.resolve_full_betting_round_npcs_only()
                    for a in npc_actions:
                        action_text = f"{a['name']} {a['action']}s"
                        if a["amount"] > 0:
                            action_text += f" to {a['amount']}"
                        console.print(f"  {action_text}")
                    if not loop.is_hand_over():
                        loop.advance_street()
                break

            if loop.is_hand_over():
                break

            # Advance to next street
            if loop.game_state.street != "showdown":
                state_dict = loop.advance_street()

        # Resolve winners
        winners = loop.resolve_winners()
        winner_names = ", ".join(w.name for w in winners)
        console.print(
            f"\n[bold green]Winner(s): {winner_names} — Pot: {loop.game_state.pot}[/bold green]"
        )

        hero_stack = loop.game_state.players[loop.hero_seat].stack
        console.print(f"[bold]Your stack: {hero_stack}[/bold]\n")

        hero_cards_str = format_cards(loop.game_state.players[loop.hero_seat].hole_cards)
        logger.add_hand_log(
            hand_number=hand_num,
            position=state_dict.get("hero_position", "?"),
            hero_cards=hero_cards_str,
            log_text="\n".join(hand_log_parts),
        )

        # Reset coach for next hand
        coach.reset_hand()
        loop.end_hand()

    # Final review
    console.rule("[bold]Session Review[/bold]")
    hero_final_stack = loop.game_state.players[loop.hero_seat].stack
    net = hero_final_stack - config.starting_stack
    session_summary = (
        f"Started with {config.starting_stack}, ended with {hero_final_stack}. "
        f"Net: {'+' if net >= 0 else ''}{net}. "
        f"Played {config.num_hands} hands."
    )

    console.print("[bold blue]Coach:[/bold blue] ", end="")
    review = ""
    for chunk in coach.get_coaching_stream(
        session_summary,
        user_message="Please provide your final session review with grades, leaks, and strengths.",
    ):
        console.print(chunk, end="")
        review += chunk
    console.print("\n")

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

    config = SessionConfig()
    if seed:
        config.seed = seed

    # Interactive configuration
    config.num_players = click.prompt("Number of players (2-9)", default=config.num_players, type=int)
    config.strong_players = click.prompt("Strong players", default=config.strong_players, type=int)
    config.starting_stack = click.prompt("Starting stack", default=config.starting_stack, type=int)
    config.num_hands = click.prompt("Number of hands (5-50)", default=config.num_hands, type=int)
    config.blind_structure = click.prompt(
        "Blind structure (fixed/escalating)", default=config.blind_structure, type=str
    )
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
