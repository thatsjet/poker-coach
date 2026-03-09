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
