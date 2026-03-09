"""Tests for SessionConfig dataclass."""

from poker_coach.config import SessionConfig


class TestSessionConfig:
    def test_defaults(self):
        config = SessionConfig()
        assert config.num_players == 6
        assert config.strong_players == 1
        assert config.num_hands == 20
        assert config.small_blind == 5
        assert config.big_blind == 10
        assert config.blind_structure == "fixed"
        assert config.show_archetypes is True

    def test_weak_players_computed(self):
        config = SessionConfig(num_players=6, strong_players=2)
        assert config.weak_players == 3

    def test_custom_values(self):
        config = SessionConfig(num_players=9, strong_players=3, num_hands=30)
        assert config.num_players == 9
        assert config.strong_players == 3
        assert config.weak_players == 5

    def test_fixed_stack(self):
        config = SessionConfig(stack_mode="fixed", starting_stack=1000)
        assert config.starting_stack == 1000

    def test_escalation_interval(self):
        config = SessionConfig(blind_structure="escalating", escalation_interval=5)
        assert config.escalation_interval == 5

    def test_seed_auto_generated(self):
        config1 = SessionConfig()
        config2 = SessionConfig()
        assert isinstance(config1.seed, str)
        assert len(config1.seed) == 16  # token_hex(8) produces 16 hex chars
        assert config1.seed != config2.seed

    def test_stack_range_defaults(self):
        config = SessionConfig(stack_mode="range")
        assert config.stack_range_min == 300
        assert config.stack_range_max == 700
