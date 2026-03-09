"""Claude API wrapper for poker coaching interactions."""

import anthropic

from poker_coach.coach.prompt import build_system_prompt


class CoachClient:
    """Wraps the Anthropic Python SDK for coaching interactions.

    Manages conversation history and hand summaries across a coaching session.
    """

    def __init__(
        self, show_archetypes: bool, model: str = "claude-sonnet-4-20250514"
    ) -> None:
        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = build_system_prompt(show_archetypes)
        self.conversation_history: list[dict[str, str]] = []
        self.hand_summaries: list[str] = []

    def get_coaching(
        self, state_text: str, user_message: str | None = None
    ) -> str:
        """Get coaching response (non-streaming). Returns full text."""
        if user_message:
            content = (
                f"Game state:\n{state_text}\n\nUser response: {user_message}"
            )
        else:
            content = (
                f"Game state:\n{state_text}\n\n"
                "Narrate the situation and ask what I would do and why."
            )
        self.conversation_history.append({"role": "user", "content": content})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.conversation_history,
        )
        reply = response.content[0].text
        self.conversation_history.append(
            {"role": "assistant", "content": reply}
        )
        return reply

    def get_coaching_stream(
        self, state_text: str, user_message: str | None = None
    ):
        """Get coaching response as a stream. Yields text chunks."""
        if user_message:
            content = (
                f"Game state:\n{state_text}\n\nUser response: {user_message}"
            )
        else:
            content = (
                f"Game state:\n{state_text}\n\n"
                "Narrate the situation and ask what I would do and why."
            )
        self.conversation_history.append({"role": "user", "content": content})
        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.conversation_history,
        ) as stream:
            full_text = ""
            for text in stream.text_stream:
                yield text
                full_text += text
        self.conversation_history.append(
            {"role": "assistant", "content": full_text}
        )

    def get_final_review(self, session_summary: str) -> str:
        """Get final session review."""
        content = (
            f"The session is over. Here is the session summary:\n\n"
            f"{session_summary}\n\n"
            "Please provide:\n"
            "1. A grade (A/B/C/D) for each scoring dimension with a "
            "one-line pattern summary\n"
            "2. An overall session grade\n"
            "3. Top 3 leaks\n"
            "4. Top 3 strengths\n"
            "Format as a clear, structured review."
        )
        self.conversation_history.append({"role": "user", "content": content})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=self.conversation_history,
        )
        reply = response.content[0].text
        self.conversation_history.append(
            {"role": "assistant", "content": reply}
        )
        return reply

    def reset_hand(self) -> None:
        """Reset conversation history between hands, keeping summaries."""
        if self.conversation_history:
            last_assistant = [
                m["content"]
                for m in self.conversation_history
                if m["role"] == "assistant"
            ]
            if last_assistant:
                self.hand_summaries.append(last_assistant[-1][:200])
        self.conversation_history = []
        if self.hand_summaries:
            summary = "Previous hands summary:\n" + "\n---\n".join(
                self.hand_summaries[-5:]
            )
            self.conversation_history.append(
                {"role": "user", "content": summary}
            )
            self.conversation_history.append(
                {
                    "role": "assistant",
                    "content": "Understood. I have context from the previous "
                    "hands. Let's continue.",
                }
            )
