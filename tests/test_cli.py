from poker_coach.cli import format_card, format_cards, display_table_setup
from poker_coach.engine.deck import Card
from poker_coach.config import SessionConfig


class TestFormatCard:
    def test_spade(self):
        result = format_card(Card("A", "s"))
        assert "A" in result
        assert "\u2660" in result

    def test_heart(self):
        result = format_card(Card("K", "h"))
        assert "K" in result
        assert "\u2665" in result

    def test_format_cards_multiple(self):
        cards = [Card("A", "s"), Card("K", "h")]
        result = format_cards(cards)
        assert "\u2660" in result
        assert "\u2665" in result


class TestDisplayTableSetup:
    def test_does_not_error(self):
        config = SessionConfig(seed="test")
        display_table_setup(config)  # Should not raise
