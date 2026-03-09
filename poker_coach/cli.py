"""CLI interface for poker coach using click and rich."""

import click
from rich.console import Console
from rich.table import Table

from poker_coach.config import SessionConfig
from poker_coach.engine.deck import Card

console = Console()

SUIT_SYMBOLS = {"s": "\u2660", "h": "\u2665", "d": "\u2666", "c": "\u2663"}
SUIT_COLORS = {"s": "white", "h": "red", "d": "red", "c": "white"}


def format_card(card: Card) -> str:
    symbol = SUIT_SYMBOLS[card.suit]
    color = SUIT_COLORS[card.suit]
    return f"[{color}]{card.rank}{symbol}[/{color}]"


def format_cards(cards: list[Card]) -> str:
    return " ".join(format_card(c) for c in cards)


def display_table_setup(config: SessionConfig) -> None:
    """Display configured table as a rich table."""
    table = Table(title="Table Setup")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Players", str(config.num_players))
    table.add_row("Strong NPCs", str(config.strong_players))
    table.add_row("Weak NPCs", str(config.weak_players))
    table.add_row("Starting Stack", str(config.starting_stack))
    table.add_row("Hands", str(config.num_hands))
    table.add_row(
        "Blinds",
        f"{config.small_blind}/{config.big_blind} ({config.blind_structure})",
    )
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
    """Display current game state with player table, pot, board, hero cards."""
    console.print()
    table = Table(title="Table")
    table.add_column("Seat", style="cyan")
    table.add_column("Player")
    table.add_column("Position", style="yellow")
    if show_archetypes:
        table.add_column("Type", style="magenta")
    table.add_column("Stack", style="green")
    table.add_column("Bet", style="red")
    table.add_column("Status")

    for p in players_info:
        is_hero = p.get("is_hero", False)
        name = "★ Hero" if is_hero else p.get("name", "")
        row = [str(p["seat"]), name, p["position"]]
        if show_archetypes:
            row.append("—" if is_hero else p["archetype"])
        row.extend([str(p["stack"]), str(p["current_bet"]), p["status"]])
        style = "bold white" if is_hero else None
        table.add_row(*row, style=style)

    console.print(table)
    console.print(f"[bold]Pot:[/bold] {pot}")
    if community_cards:
        console.print(f"[bold]Board:[/bold] {format_cards(community_cards)}")
    console.print(
        f"[bold]Your cards ({hero_position}):[/bold] {format_cards(hero_cards)}"
    )
    console.print(f"[bold]Your stack:[/bold] {hero_stack}")
    console.print()


def get_user_action() -> str:
    return click.prompt(">", type=str)


def display_coach_message(message: str) -> None:
    console.print(f"\n[bold blue]Coach:[/bold blue] {message}\n")
