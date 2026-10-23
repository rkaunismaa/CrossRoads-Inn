# Paper Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python simulation plus a LibreOffice Calc workbook that together find, and let the user hand-test, balance numbers for Crossroads Inn's 7-day run.

**Architecture:** The game rules live only in a Python package, `prototype/inn_sim`. Every random outcome is rolled up front into a `RunDeal` by `deal_run`. `play_run` applies the rules to a deal using a `Player`'s decisions, so careful, random and hand-played runs all use the same rules and the same deals. All tunable numbers live on the `Params` sheet of `prototype/balance.ods`. The sim reads that sheet with the standard library and writes sheets through headless LibreOffice over UNO.

**Tech Stack:** Python 3.10 (standard library plus pytest 9, already installed), LibreOffice 7.3 headless with `python3-uno` (installed, `import uno` works from the system python3).

**Spec:** `docs/superpowers/specs/2026-10-23-paper-prototype-design.md`

## Global Constraints

- All tunable numbers live on the `Params` sheet of `prototype/balance.ods`, which has columns `name`, `value`, `notes`. Python code never hard-codes balance values except `DEFAULT_PARAMS`, which is used only to create the workbook the first time and as test fixtures.
- Game rules exist only in Python. No rule formulas go in the spreadsheet.
- Reading `.ods` uses the standard library only (`zipfile` + `xml.etree`). Writing uses headless `soffice` through UNO, never direct zip editing. A write replaces only the named sheet and leaves every other sheet untouched.
- A run is lost **only** by failing to pay the daily upkeep or the final debt. Penalties reduce coins (clamped at 0) or goodwill and never end the run directly.
- "Ending coins" means coins held before paying the debt. The debt equals the coin target.
- Balance bar: careful player win rate between 0.70 and 0.80 inclusive, careful median ending coins between 0% and 15% above the debt, and random player win rate below 0.20.
- Sensitivity: nudging any single parameter by ±10% must keep the careful player's win rate between 0.60 and 0.90. Parameters that break this are flagged.
- The same seed and run count always give the same report.
- News only comes from wanderers, and no traveler asks for news.
- Run everything from `prototype/`: tests with `cd prototype && python3 -m pytest`, the CLI with `cd prototype && python3 -m inn_sim <command>`.
- After each task, append a step to `docs/session-history.md` (the user wants a full running record) and commit. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A `Params` sheet with a missing, extra, or non-numeric value** (for example the user types "ten"). Loading should stop with an error that names the parameter, not a `KeyError` or `ValueError` traceback. Pinned in Task 1.
2. **A decision cell in the hand-play sheet that is blank, misspelled, or illegal** (for example `haggle_high` on a pilgrim). Replay should report the row number and the bad value, and treat it as a decline rather than crashing. Pinned in Task 8.
3. **Writing while the user has `balance.ods` open in Calc**, which leaves a `.~lock.balance.ods#` file next to it. The writer should refuse with a clear "close the workbook in Calc first" error. Pinned in Task 7.
4. **Re-dealing a new seed into a workbook whose `Params` the user has hand-edited.** The `Params` values must survive unchanged. Pinned in Task 7.
5. **Taking a room when every room is full, or a meal with no food.** The rules treat it as a decline, and the random player only picks legal actions. Pinned in Tasks 3 and 5.

---

## File structure

```
prototype/
  inn_sim/
    __init__.py
    __main__.py      # CLI entry: simulate | sensitivity | init | deal | replay
    params.py        # DEFAULT_PARAMS, ParamError, read_sheet(), load_params()
    model.py         # dataclasses: DealtTraveler, DayDeal, RunDeal, InnState, TravelerView, DayView, RunResult
    deal.py          # deal_run()
    rules.py         # morning/market/serve/night/final-event, play_run(), Player protocol
    players.py       # CarefulPlayer, RandomPlayer, ScriptedPlayer
    report.py        # simulate(), check_bar(), sensitivity()
    ods_write.py     # UNO writer: write_sheet(), create_workbook(), set_params()
    handplay.py      # deal_to_rows(), reveal_rows(), read_decisions()
  tests/
    test_params.py  test_deal.py  test_rules.py  test_players.py
    test_report.py  test_ods_write.py  test_handplay.py
  conftest.py        # puts prototype/ on sys.path
  balance.ods        # created by `python3 -m inn_sim init`, then committed
  tuning-log.md      # what the agent changed while tuning, and why
```

## Rule model (decisions the spec left to the builder)

Every name below is a key in `DEFAULT_PARAMS` and a row on the `Params` sheet.

| Area | Rule | Params (first guess) |
|---|---|---|
| Start | Starting stock. | `start_coins` 20, `start_food` 10, `start_firewood` 8, `start_goodwill` 0 |
| Run | Length and costs. | `days` 7, `debt` 60, `upkeep` 3, `rooms` 3 |
| Market | Each day a price for each good is `base * U(1-jitter, 1+jitter)`, rounded to an int ≥ 1. On a "cheap firewood day" the firewood price is multiplied by the discount. | `price_food` 2, `price_firewood` 2, `price_jitter` 0.25, `p_cheap_day` 0.15, `cheap_discount` 0.5 |
| Weather | Rolled each day: snow with `p_snow`, cold with `p_cold`, otherwise normal. | `p_cold` 0.3, `p_snow` 0.15 |
| Night fire | `need = ceil((fire_base + fire_per_room * occupied) * mult)`, where `mult` is 1, `mult_cold` or `mult_snow`. On night 7 a blizzard multiplies by `blizzard_mult` as well. | `fire_base` 1, `fire_per_room` 1, `mult_cold` 1.5, `mult_snow` 2.0, `blizzard_mult` 2.0 |
| Shortage | If firewood is below the need: firewood drops to 0, `coins -= deficit * shortage_coin_per_unit`, `goodwill -= shortage_goodwill`. | `shortage_coin_per_unit` 2, `shortage_goodwill` 1 |
| Arrivals | The base count is `randint(travelers_min, travelers_max)`. +1 if goodwill ≥ `goodwill_arrival_threshold`, −1 the day after a noble walks out. Each day deals `travelers_max + 1` travelers, and only the first `count` arrive. | `travelers_min` 3, `travelers_max` 5, `goodwill_arrival_threshold` 5 |
| Types | Drawn by weight. A drawn "merchant" is a thief with chance `thief_p`. | `w_merchant` 3, `w_pilgrim` 2, `w_soldier` 2, `w_noble` 1, `w_wanderer` 1, `thief_p` 0.3 |
| Needs/pay | merchant: room + meal, pays `pay_merchant`; pilgrim: meal, pays `pay_pilgrim`, goodwill += `pilgrim_goodwill`; soldier: room, pays `pay_soldier`; noble: room (see haggle); wanderer: meal, pays 0 and gives one news item. Coin pay is multiplied by `1 + goodwill * goodwill_pay_bonus` and rounded. A meal costs `food_per_meal` food. Goodwill is clamped to `0..goodwill_cap`. | `pay_merchant` 8, `pay_pilgrim` 1, `pilgrim_goodwill` 1, `pay_soldier` 6, `food_per_meal` 1, `goodwill_pay_bonus` 0.05, `goodwill_cap` 10 |
| Thief | The hint is true with chance `hint_accuracy` if the traveler is a thief, and with chance `hint_false_pos` if honest. An accepted thief pays, then at night steals `floor(coins * thief_steal_frac)`. | `hint_accuracy` 0.7, `hint_false_pos` 0.2, `thief_steal_frac` 0.3 |
| Noble | The noble opens at `noble_offer`. The actions are `accept`, `haggle_mid` (ask `noble_mid`), and `haggle_high` (ask `noble_high`). The noble's dealt tolerance tier is 0, 1, or 2, with P(tier ≥ 1) = `p_noble_mid` and P(tier = 2) = `p_noble_high`. If the ask is over the tier, he walks out: no pay, goodwill −= `walkout_goodwill_loss`, and tomorrow has −1 arrival. | `noble_offer` 6, `noble_mid` 10, `noble_high` 15, `p_noble_mid` 0.6, `p_noble_high` 0.3, `walkout_goodwill_loss` 2 |
| News | Each wanderer is dealt one item, chosen uniformly from: `weather:<day>` (tomorrow's weather), `cheap:<day>` (the next cheap firewood day, or "none"), `final:<event>`. | — |
| Final event | Rolled once, uniformly among `blizzard`, `hungry_soldiers`, `robbery`. Hungry soldiers eat `hungry_soldiers_food`, and each unit short costs `final_food_penalty` coins. Robbery takes `floor(coins * robbery_frac)` unless goodwill ≥ `robbery_safe_goodwill`. | `hungry_soldiers_food` 6, `final_food_penalty` 3, `robbery_frac` 0.4, `robbery_safe_goodwill` 4 |

**Order of each day:**
1. Morning: pay upkeep (if coins < upkeep, the run is lost).
2. Market buys.
3. Travelers in order.
4. Night: firewood, then thief theft.
5. On day 7, the final event happens after the night fire.

Rooms free up each morning. Accepting a traveler who needs a room when `occupied == rooms`, or a meal when `food < food_per_meal`, counts as a decline. So does any `haggle_*` on a non-noble. After night 7: `end_coins = coins`, and `won = coins >= debt`.

---

### Task 1: Package skeleton, params and the ODS reader

**Files:**
- Create: `prototype/conftest.py`, `prototype/inn_sim/__init__.py`, `prototype/inn_sim/params.py`
- Test: `prototype/tests/test_params.py`

**Interfaces:**
- Produces:
  - `DEFAULT_PARAMS: dict[str, tuple[float, str]]`, where each entry is name → (value, note), with every key from the rule-model table.
  - `class ParamError(ValueError)`.
  - `read_sheet(ods_path: Path, sheet: str) -> list[list[str]]`: rows of cell text, with trailing empty cells and rows dropped, and `table:number-columns-repeated`/`number-rows-repeated` expanded but capped at 1000.
  - `load_params(ods_path: Path) -> dict[str, float]`.
  - `params_from_defaults() -> dict[str, float]`.

- [ ] **Step 1: Write the failing tests.** The tests build a minimal `.ods` in `tmp_path` with a helper `make_ods(path, {sheet: rows})`. The helper writes a `mimetype` entry first and stored, plus a `content.xml` with `office:spreadsheet/table:table/table:table-row/table:table-cell/text:p`.

```python
def test_load_params_reads_values(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"Params": [["name","value","notes"], *[[k, str(v), n] for k,(v,n) in DEFAULT_PARAMS.items()]]})
    assert load_params(p) == params_from_defaults()

def test_missing_param_names_it(tmp_path):     # drop "upkeep" row
    with pytest.raises(ParamError, match="upkeep"): load_params(p)

def test_unknown_param_names_it(tmp_path):     # extra row "upkep"
    with pytest.raises(ParamError, match="upkep"): load_params(p)

def test_non_numeric_value_names_it(tmp_path): # upkeep = "ten"
    with pytest.raises(ParamError, match="upkeep.*ten"): load_params(p)

def test_read_sheet_expands_repeated_cells(tmp_path): ...  # a cell with number-columns-repeated="3" yields 3 values
def test_missing_sheet_raises(tmp_path):
    with pytest.raises(ParamError, match="Params"): load_params(make_ods(tmp_path/"b.ods", {"Other": []}))
```

- [ ] **Step 2: Run** `cd prototype && python3 -m pytest tests/test_params.py -v`. Expected: FAIL, because `inn_sim.params` can't be imported.
- [ ] **Step 3: Implement `params.py`.** `conftest.py` inserts its own directory into `sys.path`. Non-numeric values are reported with the param name and the raw text.
- [ ] **Step 4: Run the same command.** Expected: all PASS.
- [ ] **Step 5: Log and commit.** Append Task 1 to `docs/session-history.md`, then `git add prototype docs/session-history.md && git commit -m "Add inn_sim params and ODS reader"`.

### Task 2: Model and dealing

**Files:**
- Create: `prototype/inn_sim/model.py`, `prototype/inn_sim/deal.py`
- Test: `prototype/tests/test_deal.py`

**Interfaces:**
- Consumes: `params_from_defaults()`.
- Produces:
  - `Kind = Literal["merchant","pilgrim","soldier","noble","wanderer"]`, `Weather = Literal["normal","cold","snow"]`, `FinalEvent = Literal["blizzard","hungry_soldiers","robbery"]`.
  - `@dataclass(frozen=True) DealtTraveler(kind: Kind, is_thief: bool, hint: bool, noble_tier: int, news: str | None)`. `kind` is the true kind; a thief has `kind="merchant", is_thief=True`.
  - `@dataclass(frozen=True) DayDeal(day: int, weather: Weather, price_food: int, price_firewood: int, cheap_day: bool, base_arrivals: int, travelers: tuple[DealtTraveler, ...])`.
  - `@dataclass(frozen=True) RunDeal(seed: int, days: tuple[DayDeal, ...], final_event: FinalEvent)`.
  - `deal_run(params: dict[str, float], seed: int) -> RunDeal`, which uses only `random.Random(seed)`.

- [ ] **Step 1: Write the failing tests.**

```python
def test_same_seed_same_deal(): assert deal_run(P, 7) == deal_run(P, 7)
def test_different_seeds_differ(): assert deal_run(P, 1) != deal_run(P, 2)
def test_shape():
    d = deal_run(P, 3)
    assert len(d.days) == 7 and all(len(x.travelers) == 6 for x in d.days)   # travelers_max + 1
    assert all(3 <= x.base_arrivals <= 5 for x in d.days)
def test_only_merchants_can_be_thieves():   # over seeds 0..199
    assert all(t.kind == "merchant" for t in all_travelers if t.is_thief)
def test_only_wanderers_carry_news(): ...
def test_weather_frequencies_roughly_match_params():  # 2000 days: snow 0.15±0.03, cold 0.30±0.04
def test_cheap_day_halves_firewood_price(): ...  # every cheap day's firewood price <= round(price_firewood*(1+jitter)*cheap_discount), and >= 1
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_deal.py -v`. Expected: FAIL (import error).
- [ ] **Step 3: Implement `model.py` and `deal.py`.** Roll in a fixed order (day by day, and within each day: weather, prices, cheap, arrivals, travelers; final event last), so that adding a field later only changes deals if it is rolled in the middle. News for `weather:` and `cheap:` refers to facts already present in the deal.
- [ ] **Step 4: Run the same command.** Expected: all PASS.
- [ ] **Step 5: Log and commit** (`"Add run dealing"`).

### Task 3: Day rules: morning, market, serving travelers

**Files:**
- Create: `prototype/inn_sim/rules.py`
- Modify: `prototype/inn_sim/model.py`, to add the state and view types.
- Test: `prototype/tests/test_rules.py`

**Interfaces:**
- Consumes: `RunDeal`, `DayDeal`, `DealtTraveler`.
- Produces:
  - `@dataclass InnState(coins: int, food: int, firewood: int, goodwill: int, occupied: int = 0, thieves_tonight: int = 0, walkout_yesterday: bool = False, lost: bool = False, news: list[str] = field(default_factory=list))`.
  - `new_state(params) -> InnState`.
  - `Action = Literal["accept","decline","haggle_mid","haggle_high"]`.
  - `@dataclass(frozen=True) TravelerView(kind_shown: Kind, hint: bool, offer: int, needs_room: bool, needs_meal: bool)`. A thief shows `"merchant"`. `offer` is the goodwill-adjusted pay (the noble's offer is `noble_offer`).
  - `@dataclass(frozen=True) DayView(day: int, weather: Weather, price_food: int, price_firewood: int, arrivals: int)`.
  - `pay_upkeep(state, params) -> None`, which sets `lost`.
  - `buy(state, day: DayDeal, food: int, firewood: int) -> None`, which buys as much as coins allow, food first.
  - `arrivals(state, day, params) -> int`.
  - `traveler_view(state, t: DealtTraveler, params) -> TravelerView`.
  - `serve(state, t: DealtTraveler, action: Action, params) -> str`, which applies the action and returns a short outcome string for the ledger, e.g. `"accepted +8"` or `"declined (no room)"`.

- [ ] **Step 1: Write the failing tests** (state built with `new_state(P)` and adjusted inline):

```python
def test_upkeep_paid(): s.coins = 5; pay_upkeep(s, P); assert s.coins == 2 and not s.lost
def test_upkeep_unpaid_loses(): s.coins = 2; pay_upkeep(s, P); assert s.lost and s.coins == 2
def test_buy_limited_by_coins(): ...       # coins 5, price 2/2, ask 2 food + 2 wood -> gets 2 food, 0 wood, coins 1
def test_merchant_accept_pays_and_uses_room_and_food(): ...  # +8 coins, -1 food, occupied 1
def test_goodwill_raises_pay(): s.goodwill = 4; assert traveler_view(s, merchant, P).offer == 10   # round(8*1.2)
def test_room_full_is_decline(): s.occupied = 3; assert serve(s, soldier, "accept", P).startswith("declined")
def test_no_food_is_decline(): s.food = 0; ...  # pilgrim
def test_haggle_on_non_noble_is_decline(): ...
def test_noble_haggle_within_tier_pays_ask(): ...   # tier 1, haggle_mid -> +10
def test_noble_haggle_over_tier_walks_out(): ...    # tier 0, haggle_mid -> +0, goodwill -2 (clamped at 0), walkout_yesterday True
def test_pilgrim_raises_goodwill_capped(): ...      # goodwill 10 stays 10
def test_wanderer_adds_news_no_coins(): ...
def test_accepted_thief_counts_for_tonight(): ...   # thieves_tonight == 1
def test_arrivals_bonus_and_walkout_penalty(): ...  # base 4: goodwill 5 -> 5; walkout -> 3; both -> 4; never above len(travelers)
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_rules.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the functions above in `rules.py` and the dataclasses in `model.py`.
- [ ] **Step 4: Run the same command.** Expected: all PASS.
- [ ] **Step 5: Log and commit** (`"Add day rules for upkeep, market and travelers"`).

### Task 4: Night, final event and `play_run`

**Files:**
- Modify: `prototype/inn_sim/rules.py`, `prototype/inn_sim/model.py`
- Test: `prototype/tests/test_rules.py`

**Interfaces:**
- Consumes: everything from Task 3.
- Produces:
  - `class Player(Protocol)` with `market(self, state: InnState, day: DayView, params) -> tuple[int, int]` and `decide(self, state: InnState, day: DayView, view: TravelerView, params) -> Action`.
  - `fire_need(occupied: int, weather: Weather, params, blizzard: bool = False) -> int`.
  - `night(state, day: DayDeal, params, final_event: FinalEvent | None) -> None`.
  - `@dataclass(frozen=True) RunResult(won: bool, end_coins: int, lost_on_day: int | None, ledger: tuple[str, ...])`.
  - `play_run(params, deal: RunDeal, player: Player) -> RunResult`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_fire_need(): assert fire_need(2, "cold", P) == 5 and fire_need(2, "snow", P, blizzard=True) == 12
def test_shortage_costs_coins_and_goodwill(): ...    # need 3, firewood 1: firewood 0, coins -4, goodwill -1 (clamped at 0)
def test_shortage_never_makes_coins_negative(): ...
def test_thief_steals_after_fire(): ...              # coins 20, 1 thief: coins 14
def test_rooms_reset_each_morning(): ...
def test_hungry_soldiers_shortfall_penalty(): ...    # food 2 -> coins -12, food 0
def test_robbery_blocked_by_goodwill(): ...
def test_win_when_end_coins_reach_debt(): ...        # a stub player that always declines, with start_coins high enough
def test_lost_day_recorded(): ...                    # start_coins 0 -> lost_on_day == 1, won False
def test_ledger_has_one_line_per_traveler_and_night(): ...
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_rules.py -v`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement.** `play_run` loops through the days in the order given in the rule model. It stops early when the run is lost (`end_coins` is the coins at that moment). On day 7 the night fire uses `blizzard=(final_event == "blizzard")`, and then `hungry_soldiers` and `robbery` are applied.
- [ ] **Step 4: Run** `python3 -m pytest -v`. Expected: all PASS.
- [ ] **Step 5: Log and commit** (`"Add night, final event and play_run"`).

### Task 5: Players

**Files:**
- Create: `prototype/inn_sim/players.py`
- Test: `prototype/tests/test_players.py`

**Interfaces:**
- Consumes: `Player`, `InnState`, `DayView`, `TravelerView`, `fire_need`.
- Produces:
  - `RandomPlayer(seed: int)`.
  - `CarefulPlayer()`.
  - `ScriptedPlayer(market: dict[int, tuple[int,int]], decisions: dict[tuple[int,int], Action])`, keyed by (day, slot) with slots starting at 1. A missing key means `(0,0)` or `"decline"`.

**Careful player rules** (each one is a commented block in the code):
1. Market:
   - Buy firewood up to `fire_need(rooms, weather) + 2` for today.
   - On a known cheap day, buy up to 2 days' worth.
   - Before day 7, also cover `blizzard_mult` if the news says blizzard (or if the event is unknown, half of that extra).
   - Buy food up to `arrivals * food_per_meal`, plus `hungry_soldiers_food` before day 7 if that event is known.
   - Never spend coins below `upkeep * days_left + 2`.
2. Travelers:
   - Decline any merchant with a hint.
   - Accept a room only while firewood covers `fire_need(occupied + 1, weather)`.
   - Feed a pilgrim only if food after the meal still covers the arrivals still to come.
   - Accept wanderers whenever food allows.
   - With the noble, `haggle_mid` if goodwill is at most 2, otherwise `accept`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_random_player_only_picks_legal_actions():   # 500 deals: never haggle on a non-noble, never accept with no room or no food
def test_random_player_is_seeded(): ...             # same seed -> same RunResult
def test_careful_declines_hinted_merchant(): ...
def test_careful_refuses_room_without_firewood(): ...
def test_careful_never_spends_below_upkeep_reserve(): ...
def test_scripted_player_replays_decisions(): ...
def test_careful_beats_random_on_defaults():          # seeds 0..299: careful win rate > random win rate
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_players.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the three players. `RandomPlayer` picks uniformly among legal actions, where legal means `decline` always, `accept` if there is room and food for the needs, and haggles only for the noble. Its market choice is a random quantity from 0 up to the most the coins can buy, for each good.
- [ ] **Step 4: Run** `python3 -m pytest -v`. Expected: all PASS.
- [ ] **Step 5: Log and commit** (`"Add careful, random and scripted players"`).

### Task 6: Simulation report, bar check, sensitivity and CLI

**Files:**
- Create: `prototype/inn_sim/report.py`, `prototype/inn_sim/__main__.py`
- Test: `prototype/tests/test_report.py`

**Interfaces:**
- Consumes: `deal_run`, `play_run`, `CarefulPlayer`, `RandomPlayer`, `load_params`.
- Produces:
  - `@dataclass(frozen=True) Stats(runs: int, win_rate: float, median_end: float, median_margin: float)`, where `median_margin = (median_end - debt) / debt`.
  - `simulate(params, runs: int, seed: int) -> dict[str, Stats]`, with keys `"careful"` and `"random"`. Run i uses `deal_run(params, seed + i)` for both players, and `RandomPlayer(seed + i)`.
  - `check_bar(stats: dict[str, Stats]) -> list[str]`: a list of failure messages, empty when the bar passes.
  - `sensitivity(params, runs, seed) -> list[tuple[str, float, float]]`: (param, factor, careful win rate) for each nudge outside 0.60–0.90. It skips `days`, `travelers_min` and `travelers_max`, rounds integer params after nudging, and clamps probabilities to 0..1.
  - CLI: `python3 -m inn_sim simulate [--ods balance.ods] [--runs 5000] [--seed 0] [--csv out.csv]` prints both Stats plus `BAR: PASS` or `BAR: FAIL` with the reasons. `python3 -m inn_sim sensitivity [--ods] [--runs 2000] [--seed 0]` prints the flagged params or `SENSITIVITY: PASS`. Both fall back to `DEFAULT_PARAMS` with a warning if the `.ods` file doesn't exist.

- [ ] **Step 1: Write the failing tests:**

```python
def test_simulate_is_deterministic(): assert simulate(P, 200, 5) == simulate(P, 200, 5)
def test_check_bar_messages():
    ok = {"careful": Stats(100, .75, 66, .10), "random": Stats(100, .1, 40, -.33)}
    assert check_bar(ok) == []
    assert any("careful win rate" in m for m in check_bar({**ok, "careful": Stats(100, .9, 66, .10)}))
    assert any("margin" in m for m in check_bar({**ok, "careful": Stats(100, .75, 80, .33)}))
    assert any("random" in m for m in check_bar({**ok, "random": Stats(100, .3, 50, -.1)}))
def test_bar_edges_inclusive(): ...   # 0.70, 0.80, margin 0.0 and 0.15 pass; random 0.20 fails
def test_sensitivity_flags_breaking_param(monkeypatch): ...  # stub simulate so that only "upkeep" x1.1 gives careful 0.5 -> [("upkeep", 1.1, 0.5)]
def test_cli_simulate_prints_bar(capsys): ...   # main(["simulate","--runs","50"]) prints "BAR:"
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_report.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `report.py` and `__main__.py` (argparse, with `main(argv: list[str] | None = None) -> int`).
- [ ] **Step 4: Run** `python3 -m pytest -v`, then `python3 -m inn_sim simulate --runs 2000`. Expected: tests PASS, and the CLI prints two Stats lines and a `BAR:` line. The defaults aren't expected to pass yet.
- [ ] **Step 5: Log and commit** (`"Add simulation report, bar check and sensitivity CLI"`).

### Task 7: The UNO workbook writer and `init`

**Files:**
- Create: `prototype/inn_sim/ods_write.py`
- Modify: `prototype/inn_sim/__main__.py`, to add `init`
- Test: `prototype/tests/test_ods_write.py`. The whole module is skipped with `pytest.importorskip("uno")` and when `shutil.which("soffice")` is missing.

**Interfaces:**
- Consumes: `DEFAULT_PARAMS`, `read_sheet`, `load_params`.
- Produces:
  - `class WorkbookLocked(RuntimeError)`.
  - `write_sheet(ods_path: Path, sheet: str, rows: list[list[str | float]]) -> None`: creates the sheet if it's missing, clears it, and writes the rows. Other sheets are untouched.
  - `create_workbook(ods_path: Path) -> None`: sheets `Params` (from `DEFAULT_PARAMS`), `HandPlay` and `Reveal`, both with headers only. Refuses to overwrite an existing file.
  - `set_params(ods_path: Path, updates: dict[str, float]) -> None`: changes only those values and keeps the notes.
  - CLI: `python3 -m inn_sim init [--ods balance.ods]`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_create_then_load_round_trips(tmp_path): create_workbook(p); assert load_params(p) == params_from_defaults()
def test_create_refuses_existing(tmp_path): ...
def test_write_sheet_leaves_other_sheets(tmp_path):
    create_workbook(p); set_params(p, {"upkeep": 4}); write_sheet(p, "HandPlay", [["x"]])
    assert load_params(p)["upkeep"] == 4 and read_sheet(p, "HandPlay") == [["x"]]
def test_set_params_keeps_notes(tmp_path): ...
def test_locked_workbook_refused(tmp_path):
    create_workbook(p); (tmp_path / ".~lock.b.ods#").write_text("x")
    with pytest.raises(WorkbookLocked, match="close"): write_sheet(p, "HandPlay", [])
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_ods_write.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** A context manager starts `soffice --headless --invisible --norestore --accept="socket,host=localhost,port=<free port>;urp;"` with its own `-env:UserInstallation=file://<tmpdir>`, so it never conflicts with the user's running Calc. It connects through `uno`, loads the document hidden, edits it, stores it (filter `calc8`), closes it, and terminates the process. It checks for the lock file before starting.
- [ ] **Step 4: Run** `python3 -m pytest -v`, then `cd prototype && python3 -m inn_sim init`. Expected: all PASS, and `prototype/balance.ods` exists and opens in Calc with three sheets.
- [ ] **Step 5: Log and commit** (`"Add UNO workbook writer and init"`), including `prototype/balance.ods`.

### Task 8: Dealing into the hand-play sheet and replay

**Files:**
- Create: `prototype/inn_sim/handplay.py`
- Modify: `prototype/inn_sim/__main__.py`, to add `deal` and `replay`
- Test: `prototype/tests/test_handplay.py`

**Interfaces:**
- Consumes: `deal_run`, `RunDeal`, `ScriptedPlayer`, `play_run`, `CarefulPlayer`, `write_sheet`, `read_sheet`, `load_params`.
- Produces:
  - `HANDPLAY_HEADER = ["day","weather","price_food","price_firewood","base_arrivals","slot","kind_shown","hint","needs","base_offer","buy_food","buy_firewood","decision","notes"]`. There is one row per dealt traveler slot. `buy_food` and `buy_firewood` are filled only on slot 1 of each day and blank otherwise. `decision` starts blank. A first row before the header holds `seed=<n>`.
  - `REVEAL_HEADER = ["day","slot","true_kind","is_thief","noble_tier","news"]`, plus a final row `final_event,<event>`.
  - `deal_to_rows(deal: RunDeal, params) -> list[list]` and `reveal_rows(deal) -> list[list]`.
  - `read_decisions(rows: list[list[str]]) -> tuple[int, ScriptedPlayer, list[str]]`: returns (seed, player, warnings). A warning names the sheet row number and the bad value.
  - CLI: `python3 -m inn_sim deal --seed N [--ods]` writes HandPlay and Reveal. `python3 -m inn_sim replay [--ods]` replays the user's decisions with the seed from the sheet. It prints the warnings, the run's ledger and the result, and alongside them the careful player's result on the same deal.

- [ ] **Step 1: Write the failing tests:**

```python
def test_rows_hide_secrets():   # no HandPlay cell reveals is_thief, noble_tier or the final event; a thief shows "merchant"
def test_reveal_has_truth(): ...
def test_read_decisions_round_trip(): ...   # fill decisions on dealt rows -> ScriptedPlayer.decisions matches
def test_blank_decision_is_decline_with_no_warning(): ...
def test_bad_decision_warns_with_row(): ...  # "acept" on sheet row 5 -> warning contains "row 5" and "acept"; treated as decline
def test_illegal_haggle_on_pilgrim_warns(): ...
def test_replay_matches_play_run(): ...      # read_decisions(deal_to_rows(...) filled from a CarefulPlayer run) replays to the same RunResult
def test_deal_keeps_params(tmp_path): ...    # (uno-gated) set_params upkeep 4, deal seed 3 -> load_params upkeep still 4
```

- [ ] **Step 2: Run** `python3 -m pytest tests/test_handplay.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `handplay.py` and the two CLI commands. Decisions are matched case-insensitively against `accept`/`decline`/`haggle_mid`/`haggle_high`, with surrounding spaces stripped. Real arrivals depend on hidden goodwill, so the sheet shows all `travelers_max + 1` slots. Replay ignores decisions on slots that didn't arrive, and the ledger states the real arrival count each day.
- [ ] **Step 4: Run** `python3 -m pytest -v`, then `python3 -m inn_sim deal --seed 1` and `python3 -m inn_sim replay`. Expected: tests PASS. Replaying with blank decisions prints an all-decline run next to the careful player's result.
- [ ] **Step 5: Log and commit** (`"Add hand-play dealing and replay"`).

### Task 9: First tuning pass and documentation

**Files:**
- Modify: `prototype/balance.ods` (via `set_params`), `docs/design.md`, `docs/ai-log.md`, `docs/session-history.md`
- Create: `prototype/tuning-log.md`

- [ ] **Step 1: Baseline.** Run `python3 -m inn_sim simulate --runs 5000 --seed 0` and record the output as the first entry in `tuning-log.md`.
- [ ] **Step 2: Tune.** Repeat the following until `BAR: PASS`:
  - change one or two params with `set_params` (or a tiny one-off script);
  - rerun with `--runs 5000 --seed 0`;
  - add one log line: the change, why, and the before/after Stats.

  Prefer changing the debt, upkeep, pay and prices over changing the players' rules. If a rules change seems necessary, stop and ask the user.
- [ ] **Step 3: Confirm.** Run `simulate --runs 5000 --seed 1000` on a different seed, which must also pass. Then run `sensitivity --runs 2000`, and record any flagged params in the tuning log. If there are flags, adjust and repeat Steps 2–3 at most twice, then report the remaining flags to the user instead of forcing them.
- [ ] **Step 4: Update `docs/design.md`.**
  - Replace "Exact balance numbers" and "Win condition target" under Open questions with a pointer to `prototype/balance.ods` and the passing numbers (debt, upkeep, start stock).
  - Reword the lose condition to "Lose only by failing to pay daily upkeep or the final debt; bad events cost coins or goodwill."
  - Change "wanting a room, a meal, or news" to rooms and meals, with news coming from wanderers.
  - Add the market, goodwill, weather and final-night event sections, briefly.
- [ ] **Step 5: Log and commit.** Add an entry to `docs/ai-log.md` and a step to `docs/session-history.md`, then commit (`"First balance pass meets the tight bar"`) and push.
- [ ] **Step 6: Hand over to the user for hand play.** Tell them to run `cd prototype && python3 -m inn_sim deal --seed <n>`, open `balance.ods` in Calc, fill in `buy_*` and `decision`, save and close it, then run `python3 -m inn_sim replay`. Their tuning by feel happens after this, and is outside this plan.
