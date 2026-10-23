# Tuning Log

What changed while tuning the numbers on the `Params` sheet of `balance.ods`, and why. All runs are 5000 runs at seed 0 unless noted. The bar: the careful player wins 70-80%, the careful player's median ending coins are 0-15% above the debt, and the random player wins under 20%.

## 2026-10-23 - First pass (agent)

**Baseline (first-guess numbers):**

| player | win rate | median ending coins | margin over debt 60 |
|---|---|---|---|
| careful | 0.171 | 40 | -33.3% |
| random | 0.000 | 2 | -96.7% |

Result: BAR FAIL.

**What the spread showed.** The careful player's ending coins ran from 28 (25th percentile) to 41 (median) to 54 (75th percentile). Passing the bar needs the 25th percentile close to the debt and the median no more than 15% above it, so the results have to be bunched tightly.

Turning randomness sources off one at a time showed that no single source causes the spread. Final events, thieves, weather, how many travelers arrive, prices and the mix of traveler types each add a little. With all of them off, every run ends on exactly 81 coins.

Thieves cost the most on average. Switching them off raised the median by 19 coins, because each thief takes a share of all your coins.

**Changes:**

1. **`robbery_frac` 0.4 → 0.1 and `thief_steal_frac` 0.3 → 0.1.** Losses that take a share of your coins widen the spread more than anything else.
2. **`start_coins` 20 → 60.** The run-to-run gap stays around 10-13 coins whatever the numbers are, so the median can only be within 15% of the debt when the coin base is large.
3. **`rooms` 3 → 2.** When rooms fill most nights, daily income is close to the same every run, which tightens the spread. It also makes the soldier dilemma bite harder.
4. **`goodwill_pay_bonus` 0.05 → 0.02, `noble_high` 15 → 12, and `thief_p` 0.3 → 0.2.** These trim the lucky high-end runs and the thief losses, bunching the results further.
5. **`debt` 60 → 64.** This puts the debt just below the median of 73.

**Result after the changes:**

| seed | careful win | careful median | careful margin | random win | bar |
|---|---|---|---|---|---|
| 0 | 0.774 | 73 | +14.1% | 0.000 | PASS |
| 1000 | 0.770 | 73 | +14.1% | 0.000 | PASS |

**Sensitivity (±10%, 2000 runs):** one param is flagged.
- `debt` ×1.1 drops the careful player's win rate to 0.586, below the 0.60 floor.

This is close to built into the bar. If the median sits at most 15% above the debt, a debt 10% higher lands near the median, so only about 55-60% of runs can still win. I tried twice to bunch the top of the results more tightly. The best result that stayed comfortably inside the other bands was 0.57, so I left it for the user to decide (see below).

Some whole-number params can't move by 10% (for example upkeep 3 × 1.1 still rounds to 3), so the sensitivity run lists them as not tested: `start_goodwill`, `upkeep`, `rooms`, `fire_base`, `fire_per_room`, `shortage_coin_per_unit`, `shortage_goodwill`, `pilgrim_goodwill`, `food_per_meal`, `walkout_goodwill_loss`, and `final_food_penalty`.

**Notes for hand play:**
- The random player loses almost every run. It usually spends its coins at the market and then can't pay the upkeep. That easily meets the "under 20%" bar, but it says little about how forgiving the game is for a casual human.
- The week now nets only +4 coins over the start (60 → 64 owed, plus 21 in upkeep). The game is more about not losing coins than making them, which hand play should test.
