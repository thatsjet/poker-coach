"""Session log writer that produces markdown session log files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class HandEntry:
    hand_number: int
    position: str
    hero_cards: str
    log_text: str


@dataclass
class _FinalResults:
    ending_stack: int
    grades: dict[str, str]
    overall_grade: str
    leaks: list[str]
    strengths: list[str]


class SessionLogger:
    def __init__(
        self,
        output_dir: str,
        seed: str,
        starting_stack: int,
        config_summary: dict[str, Any],
    ) -> None:
        self._output_dir = output_dir
        self._seed = seed
        self._starting_stack = starting_stack
        self._config_summary = config_summary
        self._hands: list[HandEntry] = []
        self._results: _FinalResults | None = None

    def add_hand_log(
        self,
        hand_number: int,
        position: str,
        hero_cards: str,
        log_text: str,
    ) -> None:
        """Append a hand entry to the session log."""
        self._hands.append(
            HandEntry(
                hand_number=hand_number,
                position=position,
                hero_cards=hero_cards,
                log_text=log_text,
            )
        )

    def set_final_results(
        self,
        ending_stack: int,
        grades: dict[str, str],
        overall_grade: str,
        leaks: list[str],
        strengths: list[str],
    ) -> None:
        """Store final session results."""
        self._results = _FinalResults(
            ending_stack=ending_stack,
            grades=grades,
            overall_grade=overall_grade,
            leaks=leaks,
            strengths=strengths,
        )

    def write(self) -> str:
        """Write markdown file and return the file path."""
        now = datetime.now()
        filename = f"{now.strftime('%Y-%m-%d_%H-%M')}_{self._seed}.md"
        path = os.path.join(self._output_dir, filename)

        lines: list[str] = []

        # Header / metadata
        ending_stack = self._results.ending_stack if self._results else self._starting_stack
        net = ending_stack - self._starting_stack
        net_str = f"+{net}" if net >= 0 else str(net)

        lines.append(f"# Session Log")
        lines.append("")
        lines.append(f"- **Date:** {now.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"- **Hands played:** {len(self._hands)}")
        lines.append(f"- **Starting stack:** {self._starting_stack}")
        lines.append(f"- **Ending stack:** {ending_stack}")
        lines.append(f"- **Net:** {net_str}")
        lines.append(f"- **Seed:** {self._seed}")
        lines.append("")

        # Table configuration
        if self._config_summary:
            lines.append("## Table Configuration")
            lines.append("")
            for key, value in self._config_summary.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        # Hand log
        if self._hands:
            lines.append("## Hand Log")
            lines.append("")
            for hand in self._hands:
                lines.append(f"### Hand {hand.hand_number} — {hand.position} — {hand.hero_cards}")
                lines.append("")
                lines.append(hand.log_text)
                lines.append("")

        # Session review
        if self._results:
            lines.append("## Session Review")
            lines.append("")

            if self._results.grades:
                lines.append("### Performance Grades")
                lines.append("")
                lines.append("| Category | Grade |")
                lines.append("|----------|-------|")
                for category, grade in self._results.grades.items():
                    lines.append(f"| {category} | {grade} |")
                lines.append("")

            lines.append(f"**Overall Grade:** {self._results.overall_grade}")
            lines.append("")

            if self._results.leaks:
                lines.append("### Leaks")
                lines.append("")
                for leak in self._results.leaks:
                    lines.append(f"- {leak}")
                lines.append("")

            if self._results.strengths:
                lines.append("### Strengths")
                lines.append("")
                for strength in self._results.strengths:
                    lines.append(f"- {strength}")
                lines.append("")

        os.makedirs(self._output_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write("\n".join(lines))

        return path
