from __future__ import annotations

from poker_coach.engine.deck import Card
from poker_coach.engine.hand_eval import HandRank, evaluate_hand, best_five_card_hand


def _cards(s: str) -> list[Card]:
    return [Card(t[0], t[1]) for t in s.split()]


# ---------------------------------------------------------------------------
# HandRank comparison
# ---------------------------------------------------------------------------

class TestHandRankComparison:
    def test_higher_category_wins(self):
        pair = HandRank("pair", (1, 14, 13, 12))
        trips = HandRank("three_of_a_kind", (10, 5, 4))
        assert trips > pair
        assert pair < trips

    def test_same_category_tiebreaker(self):
        pair_kings = HandRank("pair", (13, 12, 11, 10))
        pair_queens = HandRank("pair", (12, 14, 11, 10))
        assert pair_kings > pair_queens

    def test_equal_hands(self):
        h1 = HandRank("pair", (10, 9, 8, 7))
        h2 = HandRank("pair", (10, 9, 8, 7))
        assert h1 == h2
        assert h1 >= h2
        assert h1 <= h2

    def test_ge_le(self):
        high = HandRank("flush", (14, 13, 12, 11, 9))
        low = HandRank("flush", (14, 13, 12, 11, 8))
        assert high >= low
        assert low <= high


# ---------------------------------------------------------------------------
# evaluate_hand – every category
# ---------------------------------------------------------------------------

class TestEvaluateHand:
    def test_high_card(self):
        hand = _cards("As Kd Jh 9c 7s")
        result = evaluate_hand(hand)
        assert result.category == "high_card"
        assert result.tiebreakers == (14, 13, 11, 9, 7)

    def test_pair(self):
        hand = _cards("Ts Td Ah 9c 7s")
        result = evaluate_hand(hand)
        assert result.category == "pair"
        assert result.tiebreakers == (10, 14, 9, 7)

    def test_two_pair(self):
        hand = _cards("Ks Kd 9h 9c 7s")
        result = evaluate_hand(hand)
        assert result.category == "two_pair"
        assert result.tiebreakers == (13, 9, 7)

    def test_three_of_a_kind(self):
        hand = _cards("8s 8d 8h Ac 7s")
        result = evaluate_hand(hand)
        assert result.category == "three_of_a_kind"
        assert result.tiebreakers == (8, 14, 7)

    def test_straight(self):
        hand = _cards("9s 8d 7h 6c 5s")
        result = evaluate_hand(hand)
        assert result.category == "straight"
        assert result.tiebreakers == (9,)

    def test_wheel_straight(self):
        hand = _cards("As 2d 3h 4c 5s")
        result = evaluate_hand(hand)
        assert result.category == "straight"
        assert result.tiebreakers == (5,)

    def test_flush(self):
        hand = _cards("As Ks Js 9s 7s")
        result = evaluate_hand(hand)
        assert result.category == "flush"
        assert result.tiebreakers == (14, 13, 11, 9, 7)

    def test_full_house(self):
        hand = _cards("Qs Qd Qh 9c 9s")
        result = evaluate_hand(hand)
        assert result.category == "full_house"
        assert result.tiebreakers == (12, 9)

    def test_four_of_a_kind(self):
        hand = _cards("6s 6d 6h 6c As")
        result = evaluate_hand(hand)
        assert result.category == "four_of_a_kind"
        assert result.tiebreakers == (6, 14)

    def test_straight_flush(self):
        hand = _cards("9s 8s 7s 6s 5s")
        result = evaluate_hand(hand)
        assert result.category == "straight_flush"
        assert result.tiebreakers == (9,)

    def test_royal_flush(self):
        hand = _cards("As Ks Qs Js Ts")
        result = evaluate_hand(hand)
        assert result.category == "royal_flush"
        assert result.tiebreakers == (14,)


# ---------------------------------------------------------------------------
# Comparisons between evaluated hands
# ---------------------------------------------------------------------------

class TestHandComparisons:
    def test_pair_beats_high_card(self):
        pair = evaluate_hand(_cards("2s 2d 5h 7c 9s"))
        high = evaluate_hand(_cards("As Kd Qh Jc 9s"))
        assert pair > high

    def test_higher_pair_wins(self):
        pair_a = evaluate_hand(_cards("Ks Kd 5h 7c 9s"))
        pair_b = evaluate_hand(_cards("Qs Qd Ah Jc 9s"))
        assert pair_a > pair_b

    def test_kicker_breaks_tie(self):
        h1 = evaluate_hand(_cards("Ks Kd Ah 7c 9s"))
        h2 = evaluate_hand(_cards("Ks Kd Qh 7c 9s"))
        assert h1 > h2

    def test_equal_evaluated_hands(self):
        h1 = evaluate_hand(_cards("Ks Kd Ah 7c 9s"))
        h2 = evaluate_hand(_cards("Kh Kc Ad 7s 9h"))
        assert h1 == h2

    def test_wheel_loses_to_six_high_straight(self):
        wheel = evaluate_hand(_cards("As 2d 3h 4c 5s"))
        six_high = evaluate_hand(_cards("6s 5d 4h 3c 2s"))
        assert six_high > wheel


# ---------------------------------------------------------------------------
# best_five_card_hand
# ---------------------------------------------------------------------------

class TestBestFiveCardHand:
    def test_picks_best_from_seven(self):
        # 7 cards containing a flush in spades
        cards = _cards("As Ks Qs Js 9s 2d 3h")
        result = best_five_card_hand(cards)
        assert result.category == "flush"
        assert result.tiebreakers == (14, 13, 12, 11, 9)

    def test_picks_best_from_six(self):
        # 6 cards with a pair of aces being best
        cards = _cards("As Ad 3h 7c 9s Kd")
        result = best_five_card_hand(cards)
        assert result.category == "pair"
        assert result.tiebreakers == (14, 13, 9, 7)

    def test_five_cards_passthrough(self):
        cards = _cards("As Ks Qs Js Ts")
        result = best_five_card_hand(cards)
        assert result.category == "royal_flush"

    def test_full_house_from_seven(self):
        cards = _cards("Qs Qd Qh 9c 9s 2d 3h")
        result = best_five_card_hand(cards)
        assert result.category == "full_house"
        assert result.tiebreakers == (12, 9)
