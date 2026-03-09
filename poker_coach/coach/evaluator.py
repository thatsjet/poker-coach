"""Session scoring and grade evaluation for the AI poker coach."""

from __future__ import annotations


class SessionScorer:
    """Tracks per-hand grades across multiple scoring dimensions and computes
    final session grades."""

    DIMENSIONS = [
        "hand_selection",
        "bet_sizing",
        "position_awareness",
        "hand_reading",
        "pot_odds",
        "discipline",
        "aggression",
    ]

    GRADE_VALUES: dict[str, int] = {"A": 4, "B": 3, "C": 2, "D": 1}
    VALUE_GRADES: dict[int, str] = {4: "A", 3: "B", 2: "C", 1: "D"}

    def __init__(self) -> None:
        self._records: list[dict[str, str]] = []

    @property
    def hand_count(self) -> int:
        """Number of hands recorded so far."""
        return len(self._records)

    def record_hand(self, grades: dict[str, str]) -> None:
        """Record letter grades for a single hand.

        Args:
            grades: Mapping of dimension name to letter grade (A/B/C/D).
        """
        self._records.append(dict(grades))

    def final_grades(self) -> dict[str, str]:
        """Compute the average grade per dimension across all recorded hands.

        Returns:
            Mapping of dimension name to averaged letter grade.
        """
        result: dict[str, str] = {}
        for dim in self.DIMENSIONS:
            values = [self.GRADE_VALUES[r[dim]] for r in self._records if dim in r]
            if values:
                avg = sum(values) / len(values)
                rounded = round(avg)
                # Clamp to valid range
                rounded = max(1, min(4, rounded))
                result[dim] = self.VALUE_GRADES[rounded]
            else:
                result[dim] = "D"
        return result

    def overall_grade(self) -> str:
        """Compute a single overall grade by averaging all dimension grades.

        Returns:
            A single letter grade representing overall performance.
        """
        finals = self.final_grades()
        values = [self.GRADE_VALUES[g] for g in finals.values()]
        avg = sum(values) / len(values)
        rounded = round(avg)
        rounded = max(1, min(4, rounded))
        return self.VALUE_GRADES[rounded]
