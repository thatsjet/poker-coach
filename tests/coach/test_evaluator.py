"""Tests for poker_coach.coach.evaluator module."""

from poker_coach.coach.evaluator import SessionScorer


class TestSessionScorer:
    def test_initial_scores_empty(self):
        scorer = SessionScorer()
        assert scorer.hand_count == 0

    def test_record_hand_scores(self):
        scorer = SessionScorer()
        grades = {
            "hand_selection": "A",
            "bet_sizing": "B",
            "position_awareness": "A",
            "hand_reading": "C",
            "pot_odds": "B",
            "discipline": "A",
            "aggression": "B",
        }
        scorer.record_hand(grades)
        assert scorer.hand_count == 1

    def test_final_grades(self):
        scorer = SessionScorer()
        # Hand 1: all A's (4)
        scorer.record_hand({d: "A" for d in SessionScorer.DIMENSIONS})
        # Hand 2: all B's (3)
        scorer.record_hand({d: "B" for d in SessionScorer.DIMENSIONS})
        # Hand 3: all D's (1)
        scorer.record_hand({d: "D" for d in SessionScorer.DIMENSIONS})

        # Average: (4 + 3 + 1) / 3 = 2.666... rounds to 3 => "B"
        finals = scorer.final_grades()
        for dim in SessionScorer.DIMENSIONS:
            assert finals[dim] == "B"

    def test_overall_grade(self):
        scorer = SessionScorer()
        scorer.record_hand({d: "A" for d in SessionScorer.DIMENSIONS})
        scorer.record_hand({d: "C" for d in SessionScorer.DIMENSIONS})
        # Average: (4 + 2) / 2 = 3.0 => "B"
        assert scorer.overall_grade() == "B"
