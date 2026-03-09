import os
import tempfile

from poker_coach.coach.session_log import HandEntry, SessionLogger


class TestHandEntry:
    def test_dataclass_fields(self):
        entry = HandEntry(hand_number=1, position="BTN", hero_cards="A♠ K♦", log_text="Raised preflop.")
        assert entry.hand_number == 1
        assert entry.position == "BTN"
        assert entry.hero_cards == "A♠ K♦"
        assert entry.log_text == "Raised preflop."


class TestSessionLogger:
    def test_creates_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="abc123",
                starting_stack=500,
                config_summary={"players": 6, "blinds": "5/10"},
            )
            logger.add_hand_log(1, "BTN", "A♠ K♦", "Raised preflop, won pot.")
            logger.set_final_results(600, {"hand_selection": "B"}, "B", ["sizing"], ["reads"])
            path = logger.write()
            assert os.path.exists(path)
            assert "abc123" in path

    def test_log_contains_hand(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="abc123",
                starting_stack=500,
                config_summary={"players": 6, "blinds": "5/10"},
            )
            logger.add_hand_log(1, "BTN", "A♠ K♦", "Test hand log")
            logger.set_final_results(600, {}, "B", [], [])
            path = logger.write()
            with open(path) as f:
                content = f.read()
            assert "Hand 1" in content
            assert "Test hand log" in content

    def test_filename_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="xyz789",
                starting_stack=1000,
                config_summary={"players": 9},
            )
            logger.add_hand_log(1, "CO", "Q♠ Q♦", "All in.")
            logger.set_final_results(1200, {}, "A", [], [])
            path = logger.write()
            filename = os.path.basename(path)
            assert filename.endswith("_xyz789.md")
            # Should have date/time prefix: YYYY-MM-DD_HH-MM
            parts = filename.replace("_xyz789.md", "")
            assert len(parts.split("_")) == 2  # date_time

    def test_log_contains_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="meta1",
                starting_stack=500,
                config_summary={"players": 6, "blinds": "5/10"},
            )
            logger.add_hand_log(1, "BTN", "A♠ K♦", "Won.")
            logger.set_final_results(600, {"hand_selection": "A"}, "A", [], ["aggression"])
            path = logger.write()
            with open(path) as f:
                content = f.read()
            assert "meta1" in content
            assert "500" in content
            assert "600" in content
            assert "+100" in content

    def test_log_contains_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="cfg1",
                starting_stack=500,
                config_summary={"players": 6, "blinds": "5/10"},
            )
            logger.add_hand_log(1, "SB", "2♠ 7♦", "Folded.")
            logger.set_final_results(490, {}, "C", [], [])
            path = logger.write()
            with open(path) as f:
                content = f.read()
            assert "players" in content
            assert "6" in content
            assert "blinds" in content

    def test_log_contains_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="rev1",
                starting_stack=500,
                config_summary={},
            )
            logger.add_hand_log(1, "BTN", "A♠ A♦", "Won big.")
            logger.set_final_results(
                800,
                {"hand_selection": "A", "bet_sizing": "B"},
                "A-",
                ["tilt_control"],
                ["reads", "aggression"],
            )
            path = logger.write()
            with open(path) as f:
                content = f.read()
            assert "A-" in content
            assert "hand_selection" in content
            assert "tilt_control" in content
            assert "reads" in content
            assert "aggression" in content

    def test_multiple_hands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="multi",
                starting_stack=500,
                config_summary={},
            )
            logger.add_hand_log(1, "BTN", "A♠ K♦", "Hand one log.")
            logger.add_hand_log(2, "SB", "Q♠ Q♦", "Hand two log.")
            logger.add_hand_log(3, "BB", "7♠ 2♦", "Hand three log.")
            logger.set_final_results(550, {}, "B", [], [])
            path = logger.write()
            with open(path) as f:
                content = f.read()
            assert "Hand 1" in content
            assert "Hand 2" in content
            assert "Hand 3" in content
            assert "Hand one log." in content
            assert "Hand two log." in content
            assert "Hand three log." in content

    def test_negative_net(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(
                output_dir=tmpdir,
                seed="neg1",
                starting_stack=500,
                config_summary={},
            )
            logger.add_hand_log(1, "BTN", "A♠ K♦", "Lost.")
            logger.set_final_results(300, {}, "D", ["everything"], [])
            path = logger.write()
            with open(path) as f:
                content = f.read()
            assert "-200" in content
