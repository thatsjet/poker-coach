"""System prompt construction and game state formatting for the AI poker coach."""


def build_system_prompt(show_archetypes: bool) -> str:
    """Build the system prompt for the AI coach.

    Args:
        show_archetypes: When True, include archetype reference instructions.
            When False, instruct the model not to reference archetypes.

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

    return base + archetype_section


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

    if "pot" in state_dict:
        lines.append(f"Pot: {state_dict['pot']}")

    stack = state_dict.get("hero_stack") or state_dict.get("stack")
    if stack is not None:
        lines.append(f"Your Stack: {stack}")

    if "players" in state_dict:
        lines.append("\nOpponents:")
        for p in state_dict["players"]:
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
