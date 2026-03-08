# Poker Coach — Design Document

**Date:** 2026-03-08
**Status:** Approved

---

## Architecture

Monolithic Python CLI. Single package, single process. `click` for CLI prompts and flags, `rich` for terminal formatting. Run via `uv run main.py`.

### Project Structure

```
poker_coach/
├── engine/
│   ├── deck.py          # Deck, shuffle, deal
│   ├── hand_eval.py     # Hand ranking and winner resolution
│   ├── game_state.py    # State object, pot tracking, street management
│   ├── npc.py           # Archetype-based NPC action resolver
│   └── positions.py     # Button rotation, blind assignment
├── coach/
│   ├── prompt.py        # System prompt + state-to-prompt formatter
│   ├── evaluator.py     # Scores user decisions, tracks session metrics
│   └── session_log.py   # Writes markdown session files
├── cli.py               # Click-based terminal interface
├── config.py            # Session configuration + defaults
├── sessions/            # Output folder for session logs
└── main.py              # Entry point
```

### Dependencies

- `click` — CLI prompts, `--seed` flag
- `rich` — colored card display, tables, formatted output
- `anthropic` — Claude API (Python SDK)

### Entry Point

```
uv run main.py
uv run main.py --seed abc123
```

---

## Configuration

Interactive prompts at startup with defaults. All parameters configurable per session.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| Number of players | int | 6 | Range: 2-9 |
| Strong players | int | 1 | Must be <= total players |
| Weak players | int | remaining | Fills remainder |
| Starting stack mode | enum | fixed | fixed or range |
| Starting stack (fixed) | int | 500 | In chips |
| Starting stack (range) | int, int | 300, 700 | Min and max |
| Number of hands | int | 20 | Range: 5-50 |
| Blind structure | enum | fixed | fixed or escalating |
| Small blind | int | 5 | — |
| Big blind | int | 10 | — |
| Escalation interval | int | 5 | Hands between blind increases (escalating only) |
| Show archetypes | bool | true | Show/hide NPC types in coach narration |
| RNG seed | str | auto | Auto-generated via `secrets.token_hex(8)`, or user-provided via `--seed` |

---

## Game Engine

### Deck & Dealing

- Standard 52-card deck
- RNG: `random.Random(seed)` with seed from `secrets.token_hex(8)` by default or user-provided `--seed`
- Seed logged in session file for full reproducibility

### Game State

Central `GameState` class tracks all game data:
- Deck, players, pot, community cards, button position, blinds, street, hand number
- `to_dict()` method produces the JSON structure sent to the coach
- Handles blind posting, street transitions, pot collection, side pots

### Positions

- Standard rotation: BTN, SB, BB, UTG, etc.
- Labels adapt to table size (e.g., 2-player is just BTN/BB)
- Button advances each hand

### Hand Evaluation

- Standard poker hierarchy: royal flush down to high card
- Kicker comparison for tiebreaking
- Split pot support

### NPC Action Resolution

NPCs are assigned archetypes at session start. Actions resolved by the engine, not the AI coach.

**Weak (fish):**
- Preflop: call any raise up to 15% of stack with any two cards; fold otherwise
- Postflop: call any bet <= pot with top pair+, any draw, or randomly 20% with air
- Never raise without two pair or better
- Never fold top pair regardless of bet size

**Strong:**
- Preflop: open top 20% by position; 3-bet top 8%; fold to 4-bets without premiums
- Postflop: c-bet 70% of flops in position; fold to raises without strong equity
- Pressure hero when hero is out of position
- 3-bet hero's opens from late position at 15% frequency

### Blind Structure

- **Fixed:** blinds stay constant throughout session
- **Escalating:** blinds double every N hands (configurable, default every 5 hands)

---

## AI Coach

### API Integration

- Anthropic Python SDK, Claude Sonnet model
- One API call per decision point
- Full game state JSON embedded in system prompt at each call
- Conversation history maintained per hand, summarized between hands
- Streaming responses to terminal

### System Prompt Constraints

- Never agree with a bad play to be encouraging
- Always correct terminology errors
- Always show pot odds math when a call decision is involved
- Always count outs explicitly when a draw is involved
- Call out sizing leaks — name the correct size and explain why
- Reference player archetypes by behavior (not seat number) when `show_archetypes` is true
- Track recurring mistakes across the session

### Per-Hand Flow

1. Engine deals, posts blinds, resolves NPC actions up to hero's turn
2. Coach narrates the situation (position, cards, action so far)
3. Coach asks "What do you do and why?"
4. User responds via CLI
5. Coach evaluates — gives recommendation, explains why, critiques user reasoning
6. Engine resolves remaining actions, coach narrates results
7. Repeat for each street until hand completes
8. Hand summary with key takeaway and stack update

### Scoring

Seven dimensions scored silently per hand:

| Dimension | What it measures |
|---|---|
| Hand selection | Correct preflop decisions relative to position and field |
| Bet sizing | Appropriate sizing for value, protection, and draws |
| Position awareness | Adjusting decisions based on position correctly |
| Hand reading | Accuracy of opponent range assessment |
| Pot odds / math | Correct call/fold decisions based on equity |
| Discipline | Folding correctly when behind; avoiding tilt plays |
| Aggression | Appropriate semi-bluffs, value bets, and pressure plays |

Final grade per dimension: A / B / C / D with one-line pattern summary.
Overall session grade with top 3 leaks and top 3 strengths.

---

## CLI Experience

### Startup

- Interactive prompts with defaults for all config parameters
- `rich` table showing final table setup before play begins

### During Play

- Cards with suit symbols and color (red/black) via `rich`
- Compact table showing: seat, archetype (if visible), stack, status, current bet
- Pot and community cards displayed prominently
- Coach output streamed as it arrives
- User input via `> ` prompt — natural language ("raise to 40", "call", "fold")
- Engine validates action legality; re-prompts if illegal (no API call wasted)

### End of Session

- Coach delivers scored final review to terminal
- Session log written to `sessions/YYYY-MM-DD_HH-MM_<seed>.md`
- File path printed to terminal

---

## Session Log

### File Naming

```
sessions/YYYY-MM-DD_HH-MM_<seed>.md
```

### Contents

- Session metadata (date, hands played, starting/ending stack, net, seed)
- Table configuration
- Full hand log with all streets, user actions, coach feedback
- NPC hole cards revealed in the log (hidden during play)
- Performance summary table with grades
- Overall grade, key leaks, strengths

---

## Resolved Design Decisions

| Decision | Resolution |
|---|---|
| NPC archetypes visible? | Configurable via `show_archetypes` (default: true) |
| Coach tone | Always critical — no tone toggle |
| Escalating blinds in Phase 1? | Yes — included, user plays tournaments |
| NPC hole cards in logs? | Yes — hidden during play, revealed in session log |
| User-configurable seed? | Yes — optional `--seed` flag, auto-generated by default |
| Architecture | Monolithic CLI — simple, iterate fast, refactor later |
| Entry point | `uv run main.py` with `pyproject.toml` |
