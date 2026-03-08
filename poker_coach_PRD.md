# Poker Coach — Product Requirements Document

**Version:** 1.0  
**Date:** 2026-03-08  
**Status:** Draft

---

## Overview

Poker Coach is an interactive, AI-powered No Limit Hold'em training program. The user plays through simulated hands against a configurable table of players, receives real-time coaching feedback, and gets a scored session summary at the end. A deterministic backend handles all card dealing and game state so the AI coach focuses entirely on instruction rather than bookkeeping.

---

## Goals

- Provide a realistic, repeatable poker training environment
- Enforce correct game state so the AI coach never gets confused about cards, stacks, or positions
- Generate varied, real-world scenarios through a true RNG
- Produce persistent session logs the user can review and track improvement over time
- Optional: deliver the experience through a clean UI

---

## Non-Goals

- Real money play or integration with any poker platform
- Multiplayer or networked play
- Full GTO solver integration (coaching is heuristic and educational, not solver-optimal)
- Mobile app (web or CLI first)

---

## User Stories

1. As a player, I want to configure the table so I can practice against field compositions that match my real games.
2. As a player, I want real randomly dealt hands so I encounter genuine variance rather than contrived scenarios.
3. As a player, I want the AI coach to ask what I would do, then tell me what it would do and why, so I learn by comparing decisions.
4. As a player, I want honest critical feedback — not validation — so I actually improve.
5. As a player, I want a session log saved to disk so I can track my progress over time.
6. As a player, I want a final scored review after each session so I know where my leaks are.

---

## Configuration

### Table Setup (required at session start)

| Parameter | Type | Default | Notes |
|---|---|---|---|
| Number of players | Integer | 6 | Range: 2–9 |
| Strong players | Integer | 1 | Must be ≤ total players |
| Weak players | Integer | remaining | Fills remainder of table |
| Starting stack mode | Enum | fixed | Options: fixed, range |
| Starting stack (fixed) | Integer | 500 | In chips/dollars |
| Starting stack (range) | Int, Int | 300, 700 | Min and max, randomly assigned |
| Number of hands | Integer | 20 | Range: 5–50 |
| Blind structure | Enum | fixed | Options: fixed, escalating |
| Small blind | Integer | 5 | — |
| Big blind | Integer | 10 | — |

### Player Archetypes

Each NPC at the table is assigned one of two archetypes at session start. The archetype affects how the backend resolves NPC actions and how the coach describes their tendencies.

**Weak (fish):**
- Calls too wide preflop and postflop
- Rarely 3-bets without a monster
- Chases draws regardless of odds
- Slow plays strong hands inconsistently
- Does not fold to aggression reliably

**Strong:**
- Opens and 3-bets with a balanced range
- Respects position
- Folds to well-sized aggression
- Capable of bluffing and trapping
- Adjusts to player tendencies over the session

---

## Backend — Game Engine

The game engine is fully deterministic and stateful. It owns all game logic. The AI coach receives game state as structured input and never infers card values or pot sizes independently.

### Responsibilities

- Maintain a standard 52-card deck
- Shuffle using a cryptographically random seed (e.g. `crypto.randomBytes` in Node or `secrets` module in Python) logged per session for reproducibility
- Deal hole cards to all players
- Deal community cards (flop, turn, river)
- Track pot size accurately through all streets
- Track stack sizes for all players after every action
- Track position (dealer button, SB, BB, UTG etc.) and rotate correctly
- Resolve NPC actions according to archetype and current game state
- Detect hand completion, side pots, and winner resolution
- Expose full game state as a structured object at every decision point

### Game State Object (per decision point)

```json
{
  "hand_number": 7,
  "street": "flop",
  "hero_position": "BTN",
  "hero_cards": ["Ah", "Kd"],
  "community_cards": ["9c", "3h", "Jd"],
  "pot": 145,
  "hero_stack": 1280,
  "players": [
    { "seat": 1, "archetype": "strong", "stack": 420, "status": "active", "bet": 0 },
    { "seat": 3, "archetype": "weak", "stack": 310, "status": "active", "bet": 0 }
  ],
  "action_options": ["check", "bet", "fold"],
  "min_bet": 10,
  "last_action": null,
  "side_pots": []
}
```

### NPC Action Resolution

NPC decisions are resolved by the backend using archetype logic, not by the AI coach. This keeps the AI focused on coaching.

**Weak NPC logic (simplified):**
- Preflop: call any raise up to 15% of stack with any two cards; fold otherwise
- Postflop: call any bet ≤ pot with top pair or better, any draw, or randomly 20% of the time with air
- Never raise without two pair or better
- Never fold top pair regardless of bet size

**Strong NPC logic (simplified):**
- Preflop: open top 20% of hands by position; 3-bet top 8%; fold to 4-bets without premiums
- Postflop: c-bet 70% of flops in position; fold to raises without strong equity
- Apply pressure to hero when hero is out of position
- 3-bet hero's opens from late position at 15% frequency

---

## AI Coach Interface

The coach receives the game state object at each decision point and operates in a strict format.

### Per-Hand Flow

1. **Setup narration** — describe the table, positions, relevant stack sizes, and player archetypes visible to the user
2. **Present hole cards and situation** — street, pot, community cards, relevant player actions so far
3. **Ask the user** — "What do you do and why?"
4. **Evaluate user response** — assess correctness of action and sizing
5. **Give coaching feedback** — what the coach would do, why, and where the user's reasoning was right or wrong
6. **Resolve NPC actions** — backend resolves, coach narrates what happened
7. **Repeat for each street** until hand completes
8. **Hand summary** — brief note on key decision(s) and running stack update

### Coaching Principles (system prompt constraints)

- Never agree with a bad play to be encouraging
- Always correct terminology errors (bet vs raise vs c-bet etc.)
- Always show pot odds math when a call decision is involved
- Always count outs explicitly when a draw is involved
- Call out sizing leaks specifically — name the correct size and explain why
- Reference player archetypes by behavior, not seat number where possible
- Track recurring mistakes across the session and flag them in the final review

### Scoring Dimensions

Each hand is scored silently by the coach across these dimensions. Scores are aggregated for the final review.

| Dimension | What it measures |
|---|---|
| Hand selection | Correct preflop decisions relative to position and field |
| Bet sizing | Appropriate sizing for value, protection, and draws |
| Position awareness | Adjusting decisions based on position correctly |
| Hand reading | Accuracy of opponent range assessment |
| Pot odds / math | Correct call/fold decisions based on equity |
| Discipline | Folding correctly when behind; avoiding tilt plays |
| Aggression | Appropriate semi-bluffs, value bets, and pressure plays |

Final grade per dimension: A / B / C / D with one-line summary of pattern observed.

---

## Session Log

At the end of each session, the backend writes a markdown file to a `sessions/` folder in the working directory.

### File naming

```
sessions/YYYY-MM-DD_HH-MM_<seed>.md
```

The seed is the RNG seed used for the session, enabling full replay.

### File structure

```markdown
# Poker Coach Session
**Date:** 2026-03-08  
**Hands played:** 20  
**Starting stack:** $500  
**Ending stack:** $1,840  
**Net:** +$1,340  
**RNG Seed:** a3f9c21b  

## Table Configuration
- Players: 6 (2 strong, 4 weak)
- Blinds: 5/10 fixed

---

## Hand Log

### Hand 1
**Position:** HJ | **Cards:** A♠ J♦ | **Stack:** $500

**Preflop:** Raised to $15. BTN called. BB called.  
**Flop:** J♣ 8♦ 3♥ | Pot: $52  
**User action:** Bet $20  
**Coach:** Sizing too small. Recommended $35–40 (2/3 pot). Fish call larger bets equally.  
**Result:** BTN called. Pot $92.  
**Turn:** ...

---

## Session Review

### Performance Summary

| Dimension | Grade | Notes |
|---|---|---|
| Hand selection | B+ | Strong overall, QJo from EP was loose |
| Bet sizing | C+ | Consistent leak — sizing too small for value |
| Position awareness | B | Improved through session |
| Hand reading | A- | Good fish reads throughout |
| Pot odds / math | B | Missed flush draw pricing twice |
| Discipline | A- | Strong folds vs good players |
| Aggression | B+ | Appropriate pressure on fish |

### Overall Grade: B

### Key Leaks
1. **Bet sizing** — repeatedly betting 40–45% pot vs fish. Correct sizing is 65–75%.
2. **Flush draw charging** — twice allowed draws to call profitably on the turn.
3. **Early position range** — one instance of opening too loose with strong player behind.

### Strengths
1. Stack size awareness — consistently checked stacks before decisions.
2. Disciplined folds against strong players.
3. Correct identification of fish tendencies and exploitation.
```

---

## Technical Architecture

### Recommended Stack

| Layer | Option A (CLI) | Option B (Web UI) |
|---|---|---|
| Language | Python 3.11+ | Node.js / TypeScript |
| Game engine | Python module | Shared JS module |
| AI coach | Anthropic API (Claude) | Anthropic API (Claude) |
| RNG | `secrets` module | `crypto.randomBytes` |
| Session storage | Flat markdown files | Flat markdown files |
| UI | Terminal (rich / click) | React + Tailwind |

### Module Breakdown

```
poker_coach/
├── engine/
│   ├── deck.py          # Deck, shuffle, deal
│   ├── hand_eval.py     # Hand ranking and winner resolution
│   ├── game_state.py    # State object, pot tracking, street management
│   ├── npc.py           # Archetype-based NPC action resolver
│   └── positions.py     # Button rotation, blind assignment
├── coach/
│   ├── prompt.py        # System prompt and state-to-prompt formatter
│   ├── evaluator.py     # Scores user decisions, tracks session metrics
│   └── session_log.py   # Writes markdown session files
├── ui/
│   ├── cli.py           # Terminal interface (Phase 1)
│   └── web/             # React app (Phase 2, optional)
├── sessions/            # Output folder for session logs
├── config.py            # Session configuration schema
└── main.py              # Entry point
```

### API Integration Notes

- Each decision point sends a single API call with full game state embedded in the system prompt
- Game state is serialized to JSON and injected — coach never tracks state independently
- Conversation history is maintained per hand to preserve coaching context
- Session-level history is summarized between hands to manage context window
- Coach response is parsed for: action evaluation, recommended action, sizing feedback, and score deltas

---

## Phase Plan

### Phase 1 — CLI (MVP)

- Configurable table setup via CLI prompts or config file
- Full game engine with RNG dealing
- AI coach integration via Anthropic API
- Per-hand coaching flow (ask → evaluate → resolve)
- Session log written to `sessions/` on completion
- Final scored review

**Definition of done:** User can run a complete 20-hand session from the terminal, receive per-decision coaching, and find a scored markdown log in `sessions/` afterward.

### Phase 2 — Web UI (Optional)

- React frontend replacing CLI prompts
- Visual card display and table layout
- Chat-style coaching interface
- Session history browser
- Progress charts across sessions

**Definition of done:** Full Phase 1 functionality accessible via browser with visual table and card rendering.

---

## Open Questions

1. Should NPC archetypes be visible to the user at session start, or revealed through play?
2. Should the coach have a configurable tone (encouraging vs brutally honest) or always be critical?
3. Should escalating blind structures be supported in Phase 1 or deferred to Phase 2?
4. Should session logs include a full hand history with NPC hole cards revealed, or keep them hidden for realism?
5. Should the RNG seed be user-configurable to enable specific scenario replay?

---

## Out of Scope (v1)

- Tournament ICM calculations
- Multi-table simulation
- Hand history import from real poker sites
- GTO range charts
- Heads-up display (HUD) statistics
