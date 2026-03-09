"""Tests for the CoachClient API wrapper."""

from unittest.mock import MagicMock, patch

from poker_coach.coach.api import CoachClient


class TestCoachClient:
    """Tests for CoachClient."""

    def test_init(self) -> None:
        with patch("poker_coach.coach.api.anthropic.Anthropic"):
            client = CoachClient(show_archetypes=True)
            assert client.conversation_history == []

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_get_coaching_calls_api(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Coach says hello")]
        mock_client.messages.create.return_value = mock_response

        client = CoachClient(show_archetypes=True)
        result = client.get_coaching(state_text="Hand #1 — PREFLOP\nYour cards: Ah Kd")
        assert "Coach says hello" in result
        assert mock_client.messages.create.called

    def test_reset_hand_clears_history(self) -> None:
        with patch("poker_coach.coach.api.anthropic.Anthropic"):
            client = CoachClient(show_archetypes=True)
            client.conversation_history = [{"role": "user", "content": "test"}]
            client.reset_hand()
            # After reset with no assistant messages, history should be empty
            assert len(client.conversation_history) == 0 or client.conversation_history[0]["role"] == "user"

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_conversation_history_grows(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response

        client = CoachClient(show_archetypes=True)
        client.get_coaching("state1")
        assert len(client.conversation_history) == 2  # user + assistant
        client.get_coaching("state2", user_message="I raise to 30")
        assert len(client.conversation_history) == 4

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_get_coaching_with_user_message(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Good raise")]
        mock_client.messages.create.return_value = mock_response

        client = CoachClient(show_archetypes=True)
        result = client.get_coaching("state", user_message="I raise")
        assert result == "Good raise"
        # Verify the user message was included in the content
        call_args = mock_client.messages.create.call_args
        sent_messages = call_args.kwargs["messages"]
        assert "User response: I raise" in sent_messages[0]["content"]

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_get_final_review(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Session Grade: B")]
        mock_client.messages.create.return_value = mock_response

        client = CoachClient(show_archetypes=True)
        result = client.get_final_review("Hand 1: folded preflop")
        assert "Session Grade: B" in result
        assert mock_client.messages.create.called
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 2048

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_get_coaching_stream(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_stream = MagicMock()
        mock_stream.text_stream = iter(["Hello ", "world"])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_client.messages.stream.return_value = mock_stream

        client = CoachClient(show_archetypes=True)
        chunks = list(client.get_coaching_stream("state"))
        assert chunks == ["Hello ", "world"]
        assert len(client.conversation_history) == 2
        assert client.conversation_history[1]["content"] == "Hello world"

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_reset_hand_preserves_summaries(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        client = CoachClient(show_archetypes=True)
        client.conversation_history = [
            {"role": "user", "content": "state"},
            {"role": "assistant", "content": "You should fold here."},
        ]
        client.reset_hand()
        assert len(client.hand_summaries) == 1
        assert "You should fold here." in client.hand_summaries[0]
        # After reset with summaries, history has summary context
        assert len(client.conversation_history) == 2
        assert "Previous hands summary" in client.conversation_history[0]["content"]

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_default_model(self, mock_anthropic_cls: MagicMock) -> None:
        client = CoachClient(show_archetypes=False)
        assert client.model == "claude-sonnet-4-20250514"

    @patch("poker_coach.coach.api.anthropic.Anthropic")
    def test_custom_model(self, mock_anthropic_cls: MagicMock) -> None:
        client = CoachClient(show_archetypes=False, model="claude-haiku-4-20250514")
        assert client.model == "claude-haiku-4-20250514"
