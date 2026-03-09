"""System prompt construction and game state formatting for the AI poker coach."""

from poker_coach.engine.deck import Card
from poker_coach.engine.hand_eval import best_five_card_hand

RANK_NAMES = {
    14: "ace", 13: "king", 12: "queen", 11: "jack", 10: "ten",
    9: "nine", 8: "eight", 7: "seven", 6: "six", 5: "five",
    4: "four", 3: "three", 2: "two",
}

CATEGORY_LABELS = {
    "high_card": "high card",
    "pair": "a pair",
    "two_pair": "two pair",
    "three_of_a_kind": "three of a kind",
    "straight": "a straight",
    "flush": "a flush",
    "full_house": "a full house",
    "four_of_a_kind": "four of a kind",
    "straight_flush": "a straight flush",
    "royal_flush": "a royal flush",
}


def describe_hand_rank(hero_cards: list[Card], community_cards: list[Card]) -> str:
    """Return a human-readable description of the hero's best hand."""
    all_cards = hero_cards + community_cards
    if len(all_cards) < 5:
        return ""
    rank = best_five_card_hand(all_cards)
    label = CATEGORY_LABELS.get(rank.category, rank.category)
    top = rank.tiebreakers[0] if rank.tiebreakers else 0
    top_name = RANK_NAMES.get(top, str(top))

    if rank.category == "high_card":
        return f"{top_name}-high (no made hand)"
    if rank.category == "pair":
        return f"{label} of {top_name}s"
    if rank.category == "two_pair":
        second = RANK_NAMES.get(rank.tiebreakers[1], str(rank.tiebreakers[1]))
        return f"{label}, {top_name}s and {second}s"
    if rank.category in ("three_of_a_kind", "four_of_a_kind"):
        return f"{label}, {top_name}s"
    if rank.category in ("straight", "straight_flush"):
        return f"{label}, {top_name}-high"
    if rank.category == "flush":
        return f"{label}, {top_name}-high"
    if rank.category == "full_house":
        second = RANK_NAMES.get(rank.tiebreakers[1], str(rank.tiebreakers[1]))
        return f"{label}, {top_name}s full of {second}s"
    if rank.category == "royal_flush":
        return label
    return label


def build_system_prompt(show_archetypes: bool, num_players: int = 6) -> str:
    """Build the system prompt for the AI coach.

    Args:
        show_archetypes: When True, include archetype reference instructions.
            When False, instruct the model not to reference archetypes.
        num_players: Number of players at the table.

    Returns:
        The full system prompt string.
    """
    base = (
        "You are an expert poker coach. Your job is to evaluate the player's decisions "
        "honestly and help them improve.\n\n"
        "## Core Rules\n"
        "- Always evaluate pot odds when the player faces a bet or decides to call.\n"
        "- Critique bet sizing — explain when a size is too small, too large, or appropriate "
        "relative to the pot and board texture.\n"
        "- Never agree with a bad play. If the player makes a mistake, say so clearly and "
        "explain why it was wrong.\n"
        "- Evaluate each hand across these scoring dimensions: hand selection, bet sizing, "
        "position awareness, hand reading, pot odds usage, discipline, and aggression.\n"
        "- Provide a letter grade (A/B/C/D) for each dimension after every hand.\n"
        "- The game state includes a computed 'Hero's Current Hand' field that is always correct. "
        "Trust this evaluation — do not attempt to evaluate the hand yourself.\n"
    )

    if show_archetypes:
        archetype_section = (
            "\n## Archetype References\n"
            "When relevant, reference the player's archetype to contextualize advice. "
            "Use archetype tendencies to highlight leaks and suggest adjustments.\n"
        )
    else:
        archetype_section = (
            "\n## Archetype Policy\n"
            "Do not reference archetypes in your feedback. Focus only on the specific "
            "hand actions and fundamental poker strategy.\n"
        )

    prompt = base + archetype_section

    if num_players == 2:
        prompt += (
            "\n## Heads-Up Context\n"
            "This is a heads-up match (2 players only). Adjust all coaching accordingly:\n"
            "- Only two positions exist: BTN/SB and BB. The BTN posts the small blind, "
            "acts first preflop, and acts last postflop.\n"
            "- Ranges should be dramatically wider than full-ring — playing most hands is correct. "
            "Folding too many hands is a major leak heads-up.\n"
            "- Aggression is paramount. Stealing and defending blinds is the core dynamic.\n"
            "- There are no multi-way pots. Never use terms like 'checked around' or reference "
            "multiple opponents — there is only one.\n"
            "- Position is simpler but matters even more since the BTN has postflop advantage "
            "on every hand.\n"
            "- Evaluate decisions through a heads-up lens, not a full-ring one.\n"
        )

    return prompt


def format_state_for_coach(state_dict: dict) -> str:
    """Format a game state dict into readable text for the coach.

    Supports both direct key format (position, hole_cards, board, stack)
    and GameState.to_dict() format (hero_position, hero_cards, community_cards, hero_stack).
    """
    lines = []

    if "hand_number" in state_dict:
        lines.append(f"Hand #{state_dict['hand_number']}")

    if "street" in state_dict:
        lines.append(f"Street: {state_dict['street']}")

    position = state_dict.get("hero_position") or state_dict.get("position")
    if position:
        lines.append(f"Position: {position}")

    hero_cards = state_dict.get("hero_cards") or state_dict.get("hole_cards")
    if hero_cards:
        cards = " ".join(hero_cards)
        lines.append(f"Hole Cards: {cards}")

    board = state_dict.get("community_cards") or state_dict.get("board")
    if board is not None:
        board_str = " ".join(board) if board else "(none)"
        lines.append(f"Board: {board_str}")

    # Include computed hand evaluation so the coach doesn't have to guess
    if hero_cards and board:
        try:
            hero_card_objs = [Card(s[:-1], s[-1]) for s in hero_cards]
            board_card_objs = [Card(s[:-1], s[-1]) for s in board]
            hand_desc = describe_hand_rank(hero_card_objs, board_card_objs)
            if hand_desc:
                lines.append(f"Hero's Current Hand: {hand_desc}")
        except (ValueError, IndexError):
            pass  # Skip if cards can't be parsed

    if "pot" in state_dict:
        lines.append(f"Pot: {state_dict['pot']}")

    stack = state_dict.get("hero_stack") or state_dict.get("stack")
    if stack is not None:
        lines.append(f"Your Stack: {stack}")

    if "players" in state_dict:
        lines.append("\nOpponents:")
        for p in state_dict["players"]:
            if p.get("is_hero"):
                continue
            name = p.get("name", f"Seat {p['seat']}")
            pos = p.get("position", "?")
            archetype = p.get("archetype", "?")
            pstack = p.get("stack", "?")
            bet = p.get("current_bet", 0)
            status = p.get("status", "?")
            lines.append(f"  {name} ({pos}) — {archetype} — stack: {pstack} — bet: {bet} — {status}")
    elif "opponent_stack" in state_dict:
        lines.append(f"Opponent Stack: {state_dict['opponent_stack']}")

    if "current_bet" in state_dict:
        lines.append(f"Current Bet: {state_dict['current_bet']}")

    if "min_raise" in state_dict:
        lines.append(f"Min Raise: {state_dict['min_raise']}")

    return "\n".join(lines)
