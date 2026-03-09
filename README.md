# Poker Coach

**An AI that watches you punt off chips and tells you exactly how bad you are at poker.**

You know that friend at the home game who won't shut up about pot odds? This is that, except it's actually right and you can't tell it to grab you a beer.

Poker Coach is a CLI-based No Limit Hold'em training tool. It deals you into simulated hands against configurable NPC opponents, then an AI coach (Claude) roasts your decisions in real time. At the end, you get a report card you didn't ask for.

---

## What It Does

- Deals real, randomly shuffled hands using a seeded RNG (reproducible pain)
- Runs you through full hands against a mix of strong regs and calling-station fish
- Asks what you'd do at every decision point, then tells you what you *should* have done
- Scores you across 7 dimensions so you can see, in writing, that your bet sizing is atrocious
- Saves a session log so you can revisit your mistakes later when you're feeling too good about yourself

## What It Doesn't Do

- Make you feel better about your game
- Agree with your "reads"
- Accept "I had a feeling" as a valid reason for calling three streets with ace-high

---

## Quick Start

```bash
# Clone it
git clone https://github.com/thatsjet/poker-coach.git
cd poker-coach

# Install deps (requires uv)
uv sync

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Get humbled
uv run python -m poker_coach.main
```

You can also pass a seed for reproducible sessions (great for replaying that hand where you definitely played it right and just got unlucky):

```bash
uv run python -m poker_coach.main --seed copium123
```

---

## Configuration

On startup you'll get prompted for table setup. Or just hit enter repeatedly if you trust the defaults (you shouldn't — trusting defaults is how you end up calling 3-bets with J4 suited because "it was the default action").

| Parameter | Default | What It Means |
|---|---|---|
| Players | 6 | 2-9. More players = more ways to lose |
| Strong players | 1 | NPCs that actually know what they're doing |
| Weak players | (rest) | NPCs that will call your value bets and also your bluffs, somehow |
| Starting stack | 500 | In chips. Not real money. Calm down |
| Hands | 20 | How many hands of therapy you're signing up for |
| Blinds | 5/10 | Fixed or escalating, because tournament players exist |
| Show archetypes | true | Whether the coach tells you who's a fish (spoiler: it's you) |

---

## How a Session Works

1. **You get dealt cards.** Try not to play them all.
2. **NPCs act.** Fish limp, regs raise. The circle of life.
3. **Coach narrates the situation** and asks what you'd do.
4. **You type your action.** Natural language — "raise to 40", "call", "fold", "cry".
5. **Coach evaluates your decision.** Spoiler: you sized it wrong.
6. **Repeat** until the hand ends or your ego does.
7. **Session review** with grades. You will receive a C+ in bet sizing. Accept it.

---

## Scoring

The coach silently judges you across seven dimensions every hand:

| Dimension | Translation |
|---|---|
| Hand selection | Did you play trash from UTG again |
| Bet sizing | You bet 1/4 pot into a fish. Why |
| Position awareness | Calling a 3-bet out of position with KJo is not "being aggressive" |
| Hand reading | "I put him on a bluff" — you put him on a bluff every time |
| Pot odds / math | The pot was offering you 2:1 and you needed 4:1. That's not close |
| Discipline | You called because you were curious. Curiosity costs chips |
| Aggression | Checking the nuts on the river is not "trapping" |

Final grades: A / B / C / D. Most people live in C territory. It's fine. Growth mindset.

---

## Session Logs

Every session gets saved to `sessions/` as a markdown file:

```
sessions/2026-03-08_21-30_a3f9c21b.md
```

Contains: full hand history, coach feedback, NPC hole cards (revealed post-session), and your performance summary. Perfect for sending to your poker group chat when you finally get an A in something.

---

## Architecture

Monolithic Python CLI. The game engine handles all state deterministically — dealing, pots, positions, NPC actions. The AI coach (Claude Sonnet) focuses purely on coaching. It receives structured game state and never tracks cards or pots independently, because even AI shouldn't be trusted with bookkeeping at a poker table.

```
poker_coach/
├── engine/          # Cards, hands, game state, NPC logic, positions
├── coach/           # AI prompt, scoring, session logs, API client
├── cli.py           # Rich terminal UI
├── game_loop.py     # Orchestrates the whole mess
├── config.py        # Session configuration
└── main.py          # Entry point
```

---

## Tech Stack

- **Python 3.11+** — the language
- **click** — CLI prompts
- **rich** — pretty cards and tables in the terminal
- **anthropic** — Claude API for coaching
- **uv** — package management
- **pytest** — 158 tests, all passing, all judging you

---

## AI Disclosure

This project was built with Claude. The AI wrote the code, and the AI also coaches you during gameplay. It's AI all the way down. The only human in the loop is you, and based on your bet sizing, that's the weakest link.

---

## License

Do whatever you want with it. If it makes you better at poker, you're welcome. If it makes you worse, that's a skill issue.
