from poker_coach.engine.deck import Card
from poker_coach.engine.hand_eval import determine_winners


def _cards(s: str) -> list[Card]:
    return [Card(t[0], t[1]) for t in s.split()]


class FakePlayer:
    def __init__(self, seat, hole_cards):
        self.seat = seat
        self.hole_cards = hole_cards


class TestDetermineWinners:
    def test_single_winner(self):
        p1 = FakePlayer(0, _cards("As Ah"))
        p2 = FakePlayer(1, _cards("Ks Kh"))
        community = _cards("2d 3c 4h 7s 9d")
        winners = determine_winners([p1, p2], community)
        assert len(winners) == 1
        assert winners[0].seat == 0

    def test_split_pot(self):
        p1 = FakePlayer(0, _cards("As Kh"))
        p2 = FakePlayer(1, _cards("Ad Kc"))
        community = _cards("2d 3c 4h 7s 9d")
        winners = determine_winners([p1, p2], community)
        assert len(winners) == 2

    def test_board_plays(self):
        p1 = FakePlayer(0, _cards("2s 3h"))
        p2 = FakePlayer(1, _cards("4d 5c"))
        community = _cards("As Ks Qs Js Ts")
        winners = determine_winners([p1, p2], community)
        assert len(winners) == 2  # Royal flush on board
