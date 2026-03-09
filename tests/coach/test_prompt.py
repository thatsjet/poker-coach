"""Tests for poker_coach.coach.prompt module."""

from poker_coach.coach.prompt import build_system_prompt, format_state_for_coach


class TestBuildSystemPrompt:
    def test_contains_coaching_rules(self):
        prompt = build_system_prompt(show_archetypes=False)
        prompt_lower = prompt.lower()
        assert "pot odds" in prompt_lower
        assert "sizing" in prompt_lower
        assert "never agree with a bad play" in prompt_lower

    def test_archetype_instructions_included(self):
        prompt = build_system_prompt(show_archetypes=True)
        assert "archetype" in prompt.lower()

    def test_archetype_instructions_excluded(self):
        prompt = build_system_prompt(show_archetypes=False)
        # When archetypes are off, should instruct not to reference them
        assert "do not reference archetype" in prompt.lower() or "not to reference archetype" in prompt.lower()


class TestFormatStateForCoach:
    def test_format_state(self):
        state = {
            "hand_number": 5,
            "street": "flop",
            "position": "BTN",
            "hole_cards": ["Ah", "Kd"],
            "board": ["Qs", "Jh", "Tc"],
            "pot": 120,
            "stack": 980,
            "opponent_stack": 900,
            "current_bet": 40,
            "min_raise": 80,
        }
        result = format_state_for_coach(state)
        assert "Ah" in result
        assert "Kd" in result
        assert "flop" in result.lower()
        assert "120" in result
        assert "BTN" in result
        assert "Qs" in result
