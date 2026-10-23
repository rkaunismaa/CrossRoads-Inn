# Paper Prototype (Stage 1) - Design

Date: 2026-10-23
Status: draft for review

## Intent

Crossroads Inn is a 7-day resource-management game (see `docs/design.md`). Before any Godot gameplay is built, we want numbers that make a run feel **tight**: a careful player usually survives, but most runs end only just above the coin target.

Stage 1 finds those numbers in two steps:

1. A **LibreOffice Calc spreadsheet** where the user plays days by hand and tunes values.
2. A **Python simulation** that plays thousands of runs with those values and reports whether the balance meets the "tight" bar.

The numbers it settles feed the Godot `InnState` rules in stage 2. This is also part of the project's study of AI-assisted game development, so the work is logged in `docs/session-history.md` and `docs/ai-log.md`.

## Goals

- One place where every tunable number lives, used by both the spreadsheet and the simulation.
- A spreadsheet the user can play a full 7-day run in by hand, one traveler at a time.
- A simulation that runs a **careful player** and a **random player** over many seeded runs and reports results against the balance bar.
- A first set of numbers that meets the bar, recorded in `docs/design.md`.

## Non-goals

- No Godot code in this stage, apart from later copying the final numbers into the design doc.
- No UI, art, or Bram dialogue.
- No optimal or AI player. The careful player is a plain rule-based strategy.
- No game-rule formulas in the spreadsheet. The rules live in Python only.

## Anti-goals (failure even if it technically works)

- Numbers duplicated between the spreadsheet and the script, so they drift apart.
- A simulation whose rules quietly differ from the hand-play rules in the spreadsheet.
- A balance that only works because the careful player's rules are tuned to one exact set of numbers. It should still roughly hold if a few values change by around 10%.

## Game rules to model (decided with the user)

### Resources
- **Coins:** the score and buying power.
- **Food:** used up by meals.
- **Firewood:** burned each night. Each occupied room needs a lit hearth.

### Day structure (7 days)
1. **Morning:**
   - Pay the **daily upkeep** in coins. If you can't pay, the run is lost.
   - See the stock and today's weather (normal, cold, snow), plus any news you've been told.
   - Optionally buy food or firewood at the **village market**. Prices can vary by day.
2. **Travelers:** 3-5 arrive one at a time. Each wants a room, a meal, or both. For each one the player accepts, declines, or (for the noble) haggles.
3. **Night:** firewood burns. The amount depends on the weather and how many rooms are occupied. A firewood shortage has a consequence.
4. **Summary**, then the next day.
5. **Night 7:** a **final-night event** happens (see below).
6. **The morning after day 7:** the **landlord debt** (equal to the coin target) is due. If you can pay it, you win. If not, you lose.

### Hidden stat
- **Goodwill/reputation:** pilgrims you feed raise it, and failed haggles lower it. It affects how many travelers arrive and/or what they pay, and it protects you in the robbery event.

### Traveler types and their dilemmas (kept as written by the user)
1. **Soldier (cold-night soldier):** pays well for a room, but a room needs a lit hearth. In snow, taking him can leave you short of firewood.
2. **Thief disguised as a merchant:** offers top coin for a meal and a room, but sometimes leaves in the night with some of your coins. Bram gives a hint, which is sometimes right and never certain.
3. **Merchant:** the honest twin of the disguised thief. The player can't tell them apart except through the hint.
4. **Pilgrim (hungry pilgrim):** wants a meal and pays almost nothing. Feeding pilgrims builds goodwill, which raises later payments or brings a festival.
5. **Noble (haggling noble):** wants the best room and opens with a low offer. You can haggle: a good haggle pays a lot, but pushing too far makes him leave, which costs reputation and brings fewer travelers tomorrow.
6. **Wanderer:** pays only in news, for example a storm in two days, cheap firewood at the market tomorrow, or which final-night event is coming.

### Final-night event (night 7, one of)
- **Blizzard:** firewood use doubles.
- **Hungry soldiers:** a large food demand.
- **Robbery:** you lose coins unless your goodwill is high.

## The balance bar (decided with the user)

Over many seeded runs:
- The **careful player** wins **70-80%** of runs.
- The careful player's **median ending coins are 0-15% above the target**.
- The **random player** wins **under 20%** of runs.

## How it gets made

- **Spreadsheet:** LibreOffice Calc, `.ods` (the user's choice).
- **Simulation:** Python (the user's choice). Python 3.10 is installed.
- **Location:** a new top-level `prototype/` folder. *(Agent's call.)*
- **Single source of truth:** all tunable numbers live on a `Params` sheet in `prototype/balance.ods`. The simulation reads that sheet straight from the `.ods` file, with no manual copy step. *(Agent's call.)* An `.ods` file is a zip of XML, so the standard library can read it, and no extra package is needed. pandas and odfpy are not installed.
- **The rules live only in Python (user's choice).** The spreadsheet does not calculate results. For hand play, the Python sim **deals** a run from a seed: the weather, traveler arrivals and types, which merchants are thieves, market prices, haggle outcomes or their thresholds, and the final-night event. It writes them into a hand-play sheet. The user makes the decisions and records the results. The sim can also replay a hand-played run's decisions, to check the bookkeeping and compare against what the careful player would have done. Hidden values, like goodwill and whether a merchant is really a thief, are dealt into a separate "reveal" area or sheet that the user looks at only after deciding.
- **Writing the `.ods` file:** the sim writes the dealt run and updates params through headless LibreOffice (`soffice`, installed), not by editing the zip/XML directly. It must never overwrite the user's hand edits on other sheets. *(Agent's call.)*
- **Tuning is a mix (user's choice).** The agent runs the sim and adjusts parameters until a first set meets the bar, keeping a short record of what changed and why. The user then plays dealt runs by hand and adjusts by feel. After any change the sim reruns to confirm the bar still holds.
- **Robustness check (agent's call):** the sim has a sensitivity mode that moves each parameter by ±10% one at a time and reruns. "Roughly holds" means the careful player's win rate stays between 60% and 90% for every single-parameter nudge. Any parameter that breaks this is flagged in the report.
- **Losing (agent's call):** a run is lost **only** by failing to pay, either the daily upkeep or the final debt. A bad final-night event (soldiers you can't feed, a blizzard you can't heat, or a robbery) becomes a coin penalty. A firewood shortage on any night also costs coins and/or goodwill. So "a final-night event goes badly" in `docs/design.md` means "it leaves you unable to pay the debt". Update the design doc wording to match.
- **Reproducible:** the simulation takes a seed and a run count, so the same inputs always give the same report.
- **Tests:** the simulation's rule functions get a few plain unit tests (pytest, or unittest from the standard library). These are fixed-seed checks that a known day gives a known result.
- **Commits:** small, with `docs/session-history.md` updated as work goes.

## Left to the builder

- The first-guess values for every parameter. Finding good ones is the point of this stage, so the first pass only needs to be plausible.
- Exactly how goodwill changes arrivals and payments, how the noble's haggling and walk-out chance work, how good the thief hint is, how market prices vary, and what a firewood shortage costs. Each should be one or two parameters on the `Params` sheet so they can be tuned.
- The careful player's rules. They should be simple, readable, and written down in the code.
- How the spreadsheet lays out hand play, such as one row per traveler or one block per day.
- The report format. Text output is enough, plus an optional CSV of per-run results.
- Small definitions:
  - "Ending coins" means coins held before paying the debt.
  - The random player picks uniformly among legal actions, including at the market and when haggling.
  - The inn's room count is a parameter.
- Whether "news" stays a thing travelers can ask for. *(Agent's call for the prototype: news only comes from wanderers, and no traveler asks for it. Update `docs/design.md` to match.)*

## Done when

- `prototype/balance.ods` has a `Params` sheet and a hand-play sheet. The sim can deal a seeded run into the hand-play sheet, and the user can play it.
- The simulation runs from the command line with a seed and a run count, and prints careful versus random results against the bar.
- The sensitivity mode runs and reports any parameter that breaks the 60-90% band.
- The agent has found a first set of parameters that meets the bar, and the user has played at least one dealt run by hand and adjusted by feel. The final numbers are written into `docs/design.md`, and its open questions about balance and the win target are closed.
