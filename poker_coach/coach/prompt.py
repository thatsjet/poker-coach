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

    Args:
        state_dict: Dictionary containing game state fields such as hand_number,
            street, position, hole_cards, board, pot, stack, opponent_stack,
            current_bet, and min_raise.

    Returns:
        A human-readable string describing the current game state.
    """
    lines = []

    if "hand_number" in state_dict:
        lines.append(f"Hand #{state_dict['hand_number']}")

    if "street" in state_dict:
        lines.append(f"Street: {state_dict['street']}")

    if "position" in state_dict:
        lines.append(f"Position: {state_dict['position']}")

    if "hole_cards" in state_dict:
        cards = " ".join(state_dict["hole_cards"])
        lines.append(f"Hole Cards: {cards}")

    if "board" in state_dict:
        board = " ".join(state_dict["board"]) if state_dict["board"] else "(none)"
        lines.append(f"Board: {board}")

    if "pot" in state_dict:
        lines.append(f"Pot: {state_dict['pot']}")

    if "stack" in state_dict:
        lines.append(f"Your Stack: {state_dict['stack']}")

    if "opponent_stack" in state_dict:
        lines.append(f"Opponent Stack: {state_dict['opponent_stack']}")

    if "current_bet" in state_dict:
        lines.append(f"Current Bet: {state_dict['current_bet']}")

    if "min_raise" in state_dict:
        lines.append(f"Min Raise: {state_dict['min_raise']}")

    return "\n".join(lines)
