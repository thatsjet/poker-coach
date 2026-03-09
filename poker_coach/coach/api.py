"""Claude API wrapper for poker coaching interactions."""

import json

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

    def parse_action(self, user_input: str, game_state_dict: dict) -> tuple[str, int]:
        """Use Claude to parse natural language into a structured poker action.

        Returns (action, amount) where action is fold/check/call/raise.
        """
        prompt = (
            "Extract the poker action from the user's input. Return ONLY valid JSON, no other text.\n\n"
            f"Game state: pot={game_state_dict['pot']}, current_bet={game_state_dict['current_bet']}, "
            f"hero_stack={game_state_dict['hero_stack']}, min_raise={game_state_dict['min_raise']}\n\n"
            f"User said: \"{user_input}\"\n\n"
            "Return JSON: {\"action\": \"fold|check|call|raise\", \"amount\": <int>}\n"
            "Rules:\n"
            "- fold/check: amount=0\n"
            "- call: amount=current_bet\n"
            "- raise/bet: amount=total bet size (e.g. 'bet the pot' means amount=pot size, "
            "'raise to 60' means amount=60, 'bet half pot' means amount=pot/2, "
            "'all in'/'shove'/'jam' means amount=hero_stack+current_bet)\n"
            "- If sizing is ambiguous, pick the most standard interpretation"
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            result = json.loads(text)
            return (result["action"], int(result.get("amount", 0)))
        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback to local parser
            return self._fallback_parse(user_input, game_state_dict)

    @staticmethod
    def _fallback_parse(text: str, state: dict) -> tuple[str, int]:
        """Simple fallback parser if AI parsing fails."""
        text = text.strip().lower()
        if "fold" in text:
            return ("fold", 0)
        if "check" in text:
            return ("check", 0)
        if "call" in text:
            return ("call", state["current_bet"])
        if "all in" in text or "shove" in text or "jam" in text:
            return ("raise", state["hero_stack"] + state["current_bet"])
        # Default to check
        return ("check", 0)

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
