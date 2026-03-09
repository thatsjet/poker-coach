"""Position labels for poker tables of different sizes with button rotation."""

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
    """Return position labels for each seat, with seat ``button_index`` as BTN.

    Args:
        num_players: Number of players at the table (2-9).
        button_index: Seat index (0-based) that holds the button.

    Returns:
        A list of position label strings, one per seat, where the element at
        ``button_index`` is ``"BTN"`` and the remaining positions follow in
        clockwise order.

    Raises:
        ValueError: If ``num_players`` is not between 2 and 9, or
            ``button_index`` is out of range.
    """
    if num_players not in POSITION_LABELS:
        raise ValueError(
            f"num_players must be between 2 and 9, got {num_players}"
        )
    if not 0 <= button_index < num_players:
        raise ValueError(
            f"button_index must be between 0 and {num_players - 1}, "
            f"got {button_index}"
        )

    labels = POSITION_LABELS[num_players]
    positions = [""] * num_players
    for i, label in enumerate(labels):
        seat = (button_index + i) % num_players
        positions[seat] = label
    return positions


def rotate_button(current: int, num_players: int) -> int:
    """Advance the button to the next seat.

    Args:
        current: Current button seat index.
        num_players: Number of players at the table.

    Returns:
        The next button seat index, wrapping around to 0 if needed.
    """
    return (current + 1) % num_players
