# Session History

A running, step-by-step record of everything done in the Claude Code terminal sessions on this project, in order. Unlike `ai-log.md`, which keeps short notes on successes and failures, this file records the whole sequence of events.

Format: each session has a heading. Each step lists the user's request, then what the agent did and the result.

---

## Session 1 - 2026-10-23

### 1. "what is happening here?"
- The agent read `CLAUDE.md` and `docs/design.md`. Neither file was committed yet, and the branch was `master`.
- It summarized the project (a Godot 4 resource-management game used as a learning project for AI-assisted game development) and suggested next steps.

### 2. "commit these and rename the branch to main"
- Renamed the branch `master` to `main`.
- Commit `8ca40fb` added the project instructions and the initial design doc.

### 3. "set up the Godot project in game/"
- Godot was not installed. The user chose to have the agent download it to `~/.local/bin`.
- Installed Godot 4.7.2 (latest stable) from the official GitHub releases and checked it against the SHA512 checksums.
- Vendored GUT 9.7.1 into `game/addons/gut`.
- Created:
  - `game/project.godot` (1280x720, GL Compatibility, warnings for untyped declarations)
  - the `InnState` rules class
  - a grey-box main scene
  - two GUT tests
  - `tools/run-tests.sh`
  - `docs/ai-log.md`
- Updated `CLAUDE.md` with the test command and folder layout.
- Checked: tests pass with exit 0, a deliberately failing test gives exit 1, and the main scene runs headless with no errors.
- Commit `be9eea9`.

### 4. "I have created https://github.com/rkaunismaa/CrossRoads-Inn.git"
- Confirmed the repo was empty (it is public).
- Added it as `origin`. The HTTPS push failed because no credentials were stored, so the agent switched to the SSH URL, which was already authenticated.
- Pushed `main`. It tracks `origin/main` and is GitHub's default branch.

### 5. "start the paper prototype to balance the numbers"
- Started a design conversation (brainstorming) before building anything.
- Decisions from the user so far:
  - Format: first a spreadsheet, then a script that simulates many runs.
  - Target feel: tight. Most runs should end barely above the coin target.
- The user also asked for this running history file. The agent created it and will keep it up to date (commit `e372ea6`, pushed).
- Tools: LibreOffice Calc for the spreadsheet and Python for the simulation.
- The user asked the agent to propose dilemmas. The agent offered five: the cold-night soldier, the thief disguised as a merchant, the hungry pilgrim (goodwill), the haggling noble (reputation), and the wanderer who pays in news. The user kept all five as written.
- The agent played back its understanding. The user confirmed every guess: a village market for buying food and firewood, a hidden goodwill/reputation stat, daily weather (normal, cold, snow), the merchant as the honest twin of the thief, and a simulation that compares a rule-based "careful player" against a random baseline.
- Debts (confirmed): a fixed landlord debt is due the morning after day 7 and equals the coin target. There is also a small daily upkeep due each morning. Missing either payment ends the run.
- Final-night event (confirmed): on night 7 one of a few events happens: a blizzard (double firewood), hungry soldiers (lots of food), or a robbery (coins lost unless goodwill is high). Wanderer news can warn of it.
- What "tight" means (confirmed): the careful player wins 70-80% of runs with a median ending 0-15% above the target, and the random player wins under 20%.
- The agent sized this as a project that needs a written design doc, and started writing it.
- Wrote the draft spec `docs/superpowers/specs/2026-10-23-paper-prototype-design.md`. A reviewer subagent read it as a builder would and raised four gaps. The agent settled two itself (a ±10% sensitivity check, and what counts as an instant loss) and took two to the user: whether the spreadsheet works out results or is a ledger, and who tunes the numbers.
- User's answers:
  - Option (c): the Python sim deals seeded runs into the sheet, and the user makes the decisions. The rules live only in Python.
  - Tuning is a mix: the agent finds a first set that meets the bar, then the user adjusts by feel.
- Updated the spec to match. It now waits for the user's approval.

### 6. "looks good"
- The user approved the paper prototype spec, and its status was set to approved. Next the agent writes the implementation plan using the writing-plans skill.
- Wrote the implementation plan `docs/superpowers/plans/2026-10-23-paper-prototype.md` using the writing-plans skill. It has 9 tasks: the params/ODS reader, dealing, day rules, night/final event, players, the simulation report and sensitivity check, the UNO workbook writer, hand-play dealing/replay, and a first tuning pass. It also fixes the rule model and first-guess parameter values. Checked the tools first: pytest 9 and python3-uno are present, along with LibreOffice 7.3.

### 7. "native it is"
- The user chose native execution: the agent builds all nine tasks itself in this session, and one reviewer checks everything at the end. Work happens on the branch `paper-prototype`.
- Added a root `.gitignore` for the superpowers workspace and Python caches.
- Task 1: the `prototype/inn_sim` package, `DEFAULT_PARAMS` (the first-guess numbers), and an `.ods` reader that uses only the standard library. A missing, unknown or non-numeric param gives an error naming it. 8 tests: watched them fail, then pass.
- Task 2: `model.py` holds the dealt-run data types, and `deal_run(params, seed)` rolls everything random up front. News is always true. 9 tests: watched them fail, then pass. Rulings: the news format, and the order rolls happen in.
- Task 3: day rules covering upkeep, market buying, arrivals and serving each traveler, including the noble's haggling and walk-outs. Anything impossible, like no room, no food, or haggling with a non-noble, counts as a decline. 20 tests: watched them fail, then pass.
- Task 4: the night (firewood, shortages, thieves), the final-night events, and `play_run`, which plays a whole dealt run with any player and keeps a day-by-day ledger. 48 tests in total, all passing.
- Task 5: the players. The careful player follows simple written rules; the random player picks uniformly among legal moves; and a scripted player replays hand-play decisions. 58 tests passing. On the first-guess numbers the careful player wins 16% of runs and the random player 0%, which is far from the bar. Tuning comes in Task 9.
- Task 6: the simulation report and CLI. `python3 -m inn_sim simulate` compares the careful and random players on the same deals and prints `BAR: PASS/FAIL` with the reasons, with an optional CSV. `sensitivity` nudges each number by ±10%. 66 tests passing. The first-guess numbers give `BAR: FAIL` (careful player wins 16%, median 32% below the target).
- Task 7: the workbook writer. It starts a private headless LibreOffice with its own throwaway profile, edits only the named sheet, and refuses with "close the workbook in Calc first" if the file is open. `python3 -m inn_sim init` created `prototype/balance.ods` with the sheets `Params`, `HandPlay` and `Reveal`. 74 tests passing. The LibreOffice tests take about 15 s.
- Task 8: hand play. `python3 -m inn_sim deal --seed N` writes the run into `HandPlay`, with nothing hidden shown, and the truth into `Reveal`. `replay` reads your decisions back, warns about bad cells by row number instead of crashing, warns if `Params` changed since the deal, and prints your ledger next to the careful player's result. 86 tests passing. Tried it on the real workbook with seed 1.
- Task 9: the first tuning pass.
  - Baseline: the careful player won 17%.
  - Ablation: every source of randomness adds a little spread, and thieves cost the most.
  - Changes: start coins 60, 2 rooms, debt 64, robbery 10%, thief theft 10%, thief chance 20%, goodwill pay bonus 0.02, `noble_high` 12.
  - Result: `BAR: PASS` on seeds 0 and 1000 (careful player 77% wins, median 73, +14.1%; random player 0%).
  - Sensitivity: reversed the Task 6 "nudge whole numbers by ±1" decision with tests, because it falsely flagged a dozen params. Firewood amounts were added to the whole-number list.
  - One flag is left: raising the debt by 10% drops the careful player to 58.6%, against a 60% floor. Two adjustment attempts didn't fix it, and it looks built into the bar. It goes to the user.
  - Wrote `prototype/tuning-log.md` and updated `docs/design.md` (v0.2): rules, numbers, the lose condition, and news coming only from wanderers.
- Final review by a fresh reviewer subagent. It found nothing critical and 5 important issues. The agent fixed 3 of them, each with a test that failed first:
  - the CLI now prints `error: ...` instead of a traceback;
  - a blank row after the seed row no longer silently drops every decision;
  - a blank decision for a traveler who actually arrived now gets a warning with its row number.

  93 tests passing. One finding was kept as a decision: goodwill isn't a hidden-info leak, because a player can work it out from what happened. One goes to the user: the hand-play sheet shows the whole week up front. Six minor findings were deferred.

### 8. "1" (merge locally)
- Fast-forward merged `paper-prototype` into `main`. 93 tests pass on `main`. Deleted the local branch.
- Left for the user to decide: pushing `main`, deleting the remote `paper-prototype` branch, the debt sensitivity gap, and whether the hand-play sheet should show the whole week up front.

### 9. "push main and delete the remote branch"
- Pushed `main` to GitHub and deleted the remote `paper-prototype` branch. Local `main` now matches `origin/main`.

### 10. "add a mode that deals one day at a time"
- Short design conversation. The user wants to see how each day turned out first, then the next day's travelers.
- The agent described a small change:
  - `deal --daily` writes only day 1;
  - `next` prints the day's results, logs them to a `DayLog` sheet, and adds the next day with only the travelers who really arrive;
  - `Reveal` is filled only after day 7;
  - earlier days are replayed from the sheet every time.

  The user approved it ("go ahead and build it"). Work happens on the branch `daily-deal`.
- Built daily mode test-first. Each piece's tests were watched failing, then passing:
  - `rules.play_days()` plays a run up to a given day, and `play_run` now uses it;
  - wanderer news appears in plain words in the ledger;
  - each night line shows the stock after the night;
  - `handplay.daily_rows()` lists only travelers who really arrived, labels the column `arrivals`, and keeps the player's cells;
  - `deal --daily` and `next` added to the CLI.
- One test was wrong: it compared a lost run, which has no End line, and compared a list to a tuple. The agent fixed the test, not the code.
- 104 tests passing. Tried it by hand on a copy of the workbook (seed 5, day 1, then `next`).

### 11. "1" (merge locally)
- Fast-forward merged `daily-deal` into `main`. 104 tests pass on `main`. Deleted the local branch, which was never pushed.

### 12. "sure" (push)
- Pushed `main` to GitHub.

### 13. "why is there no readme.md ?" / "yes, write it and push"
- There was none because neither CLAUDE.md nor any task asked for one. Wrote `README.md`: what the game is, status, folder layout, requirements, how to run the Godot tests, how to use the paper prototype including daily hand play, and how AI is used. Pushed to `main`.

### 14. "start the grey-box Godot prototype"
- Started a design conversation (brainstorming) for stage 2. The user asked the agent to propose options. The agent offered a browser tab of mockups, the user accepted, and the agent started the brainstorming visual companion server.
- First screen: three layouts for a traveler's arrival: (A) a ledger desk, (B) the counter scene with speech bubbles, (C) a queue of travelers at the door.
- The user said "you choose". The agent picked B, the counter scene, and borrowed C's "N more travelers today" count. Agent's reasons: B is closest to the final game, so stage 3 art (portraits, backdrop) drops straight in; and the count gives the same planning information the simulation's careful player uses.
- Proposed five definitions of "stage 2 done". The user picked 1 (a full week you can play, rules in GDScript with GUT tests), 2 (the same ledger as the Python sim on exported fixtures) and 3 (Bram picks fixed lines from a facts object).
- The agent described how it would build them, and the user said "looks right, write it up". Wrote the draft spec `docs/superpowers/specs/2026-10-23-greybox-godot-design.md` and sent a reviewer subagent to read it as a builder would.
- The reviewer reported "nothing important left". The agent added three of its own calls to the spec: deliberately illegal-action fixtures, copying Python's round-half-to-even, and Bram's facts holding only what the player can see. The spec now waits for the user's approval.

### 15. "approved, write the plan"
- The user approved the stage 2 spec. Stopped the mockup server; the mockups stay in `.superpowers/brainstorm/`, which git ignores. Next the agent writes the plan with the writing-plans skill.
- Wrote the stage 2 implementation plan `docs/superpowers/plans/2026-10-23-greybox-godot.md`. It has 9 tasks: export params, export parity fixtures, GDScript params and model, day rules, night + `DayRunner` + parity test, dealing, Bram's facts and lines, the counter UI, and docs. Self-review fixed the test-default values and a made-up description of Bram.

### 16. "lets go native"
- The user chose native execution for stage 2. Work happens on the branch `greybox-godot`.
- Task 1: `python3 -m inn_sim export` writes `game/data/params.json` from `balance.ods`, with whole numbers written as ints. A test fails if the file is stale. 106 Python tests passing.
- Task 2: `python3 -m inn_sim export-fixtures` writes 20 dealt runs, each with recorded decisions and the expected ledger, plus a `manifest.json` holding a params hash, to `game/tests/fixtures/`. The runs are 8 careful, 6 random, 3 accept-everyone and 3 haggle-everyone. Together they cover every rule branch: walk-outs, thefts, shortages, upkeep losses, all 3 final events, robbery stopped, each kind of decline, news, and wins. A test fails if the fixtures are stale. 111 Python tests passing.
- Task 3: the GDScript numbers loader (`InnParams`), with errors that name the file or key, and the data model (`DealtTraveler`, `DayDeal`, `RunDeal.from_dict`, `TravelerView`, and `InnState` extended with `snapshot()`).
- Found and fixed a tooling hole. GUT silently skipped test files that didn't parse and still reported "All tests passed". `tools/run-tests.sh` now fails when Godot reports any script error. Checked both ways: exit 1 with the broken files, exit 0 when clean. 12 GDScript tests passing.
- Task 4: ported the day rules to GDScript (`InnRules`): Python-style rounding, upkeep, buying, arrivals, traveler views, serving, "why can't I" reasons, and news in plain words. 24 new tests mirror the Python rule tests with the same numbers. 35 GDScript tests passing.
- Task 5: the night rules, `DayRunner` (plays a run step by step, as the UI will) and the parity test. All 20 Python runs are reproduced line for line by the GDScript rules, matching on the first try. Checked the test can fail: changing "thief stole" to "thief took" made it fail and show the first differing line, then the change was reverted. 46 GDScript tests passing.
- Task 6: `Dealer.deal_run` deals runs in Godot with `RandomNumberGenerator`, using the same odds and roll order as Python (a seed won't give the same run as Python, which is expected). 9 tests ported from the Python deal tests, covering shape, thieves, news truthfulness, noble tiers, weather frequencies and cheap-day prices. Fixed one type-inference compile error along the way. 55 GDScript tests passing.
- Task 7: Bram. `BramFacts` builds morning, traveler and night facts, containing only what the player can know; every key is documented for stage 5. `Bram` picks a situation by priority and chooses one of at least 2 hand-written lines. Tests over 20 dealt runs show no secrets leak and Bram changes nothing. Fixed one type-inference error, and corrected a code comment that called Bram "the regular" (an invented detail) to the design doc's wording. 63 GDScript tests passing.
- Task 8: the counter-layout screen (`game/scenes/main.gd`, built in code). It has the morning market, travelers at the counter with Accept, Decline and Haggle, greyed-out buttons with reasons, the night summary, the end screen and "Play again", and Bram speaks at each moment. 9 scene tests drive it through its buttons.
- The agent can't play by hand from a terminal, so it rendered the real screen with a throwaway script and looked at screenshots of the morning, counter, night and end screens. That revealed a bug: the night top bar showed the next day. Fixed test-first, along with off-centre box captions and a missing margin. 72 GDScript tests passing.
- Task 9: updated `docs/design.md` (stages 1 and 2 done, a grey-box section), `README.md` (status, how to play, regeneration commands), the `CLAUDE.md` layout and the AI log.
- Final review by a fresh reviewer subagent: nothing critical, and the parity port and harness were judged solid. The agent fixed these, each with a test that failed first:
  - the morning screen now says how many travelers are coming (a label, plus a count in the top bar);
  - the counter's top bar shows "N more travelers today" from the first traveler;
  - the end screen has a week summary;
  - two of Bram's lines no longer hard-code balance numbers ("Day seven", "twice the wood").

  76 GDScript tests passing. Six minor findings were deferred.

### 17. "1" (merge locally)
- Merged `greybox-godot` into `main`. On `main`, 76 GDScript tests and 111 Python tests pass. Deleted the local branch, which was never pushed.

### 18. "yes" (push)
- Pushed `main` to GitHub, including stage 2.

### 19. "gonna bail for now and will continue later"
- Session paused. State: stages 1 and 2 are done and on `main`. Next up is stage 3, generated 2D art (portraits and a backdrop via ComfyUI).
- Open items for the user:
  - the debt ×1.1 sensitivity gap (`prototype/tuning-log.md`);
  - whether a week netting about +4 coins feels good in play;
  - six deferred minor findings from the stage 2 review, listed under step 17's review notes and in the AI log.

---

## Session 2 - 2026-10-23 (resumed)

### 1. "continue"
- The user resumed the same Claude Code session (`ClaudeResume.txt` holds the resume command; it stays untracked).
- The agent checked the state: `main` matches GitHub, and stages 1 and 2 are done. Two GPUs are available (RTX 4090 24 GB and RTX 2070 SUPER 8 GB). No ComfyUI install was found in the obvious places. Started stage 3 (generated 2D art) with a design conversation.

### 2. "skip the questions and just start"
- The agent's stated choices: run ComfyUI locally on the RTX 4090 with SDXL base 1.0 (CreativeML Open RAIL++-M, commercial use allowed); keep every image reproducible from `tools/comfyui/assets.json`, with a provenance file for the Steam AI disclosure; generate one backdrop plus framed portraits of the five traveler types and Bram (a thief uses the merchant portrait); fall back to grey boxes when art is missing.
- Searched the machine: no ComfyUI and no model files. Cloned ComfyUI into `~/ComfyUI` (outside the repo) with its own Python 3.12 environment, installed PyTorch for CUDA 12.8, and started downloading SDXL base 1.0 (about 7 GB).
- Built `tools/comfyui/` test-first: `comfy_client.py` (an SDXL text-to-image job sent to the ComfyUI API, using only the standard library) and `generate_assets.py` (generates the missing images from `assets.json` and writes `provenance.json`). 6 tests.
- `assets.json` holds 7 images: the backdrop and portraits of the merchant, pilgrim, soldier, noble, wanderer and Bram. Bram's appearance is the agent's call (a weathered local man in a wool tunic); the design doc doesn't describe him.
- Work happens on the branch `art-stage3`. Wrote 3 failing Godot tests: portraits match the traveler shown, Bram and the backdrop use their art, and the scene falls back to grey boxes when art is missing.
- The model download finished. Its SHA-256 matched the published value for SDXL base 1.0. ComfyUI ran on the RTX 4090, at about 7 s per image.
- Generated all 7 images and reviewed them on a contact sheet. Redid 3: the backdrop (white edges), the noble (an ornate frame and odd style), and the wanderer (too much like Bram; made younger with a green cloak). Then regenerated the other 4 so `assets.json` reproduces every image; `provenance.json` matches.
- Scene integration: the backdrop sits behind everything, the portrait follows the traveler shown (a thief shows as the merchant), and Bram has his own portrait. It falls back to grey boxes if art is missing. 3 new tests; 79 GDScript tests passing.
- Screenshots of the real scene showed white text was hard to read over the painting. Added dark backing panels behind text and hid empty bubbles.
- Updated `docs/design.md` (stage 3 done), `README.md` (status, layout, and the AI-art disclosure note), the AI log and this history.

### 3. "1" (merge locally)
- Merged `art-stage3` into `main`. On `main`, 79 GDScript tests, 111 Python tests and 6 art-tool tests pass. Deleted the local branch, which was never pushed. Stopped the ComfyUI server to free the GPU.

### 4. "push it"
- Pushed `main` to GitHub, including the stage 3 art.

---

## Session 3 - 2026-10-23 (resumed)

### 1. "continue"
- Resumed the same Claude Code session. The agent checked the state: `main` matches GitHub, and stages 1–3 are done.
- Tooling found: Ollama is installed and running locally but has no models pulled. Blender is not installed.
- Next is either stage 4 (an optional 3D prop) or stage 5 (Bram's local-LLM dialogue). The agent asked the user which one.

### 2. "stage 5"
- The user picked stage 5, Bram's local-LLM dialogue. Started a design conversation (brainstorming).

### 3. "just do it"
- The user skipped the questions. The agent's calls:
  - Qwen3-4B through the local Ollama on the 4090;
  - the fixed line shows first, and the LLM line swaps in only if it passes the checks;
  - if anything fails, the fixed line stays.
- Pulled `qwen3:4b`. A spike showed it always writes its reasoning out loud, even with `think: false`. Pulled `qwen3:4b-instruct` instead (Apache 2.0 license confirmed) and removed the first model.
- A second spike with a code-chosen goal and Bram's fixed lines as voice examples gave usable lines at about 0.1 s each, and ignored a basic injection.
- Branch `bram-llm`. Built test-first:
  - `BramVoice`: the prompt; reply checks for length, invented numbers, breaking character, thief certainty and unsupported words; and a strict schema for the facts.
  - `BramLLM`: a non-blocking Ollama client that fails quietly and reads `game/data/bram_llm.json`. `tools/run-tests.sh` switches the LLM off unless `CROSSROADS_LLM_LIVE=1`.
  - Scene wiring: the fixed line shows first; the LLM reply replaces it only for the same moment.
- `game/tools/bram_eval.gd` runs the live model over 6 dealt runs plus an injection suite and writes `docs/bram-eval.md`.
  - First run: 256/256 lines OK, but 2 of 30 injections showed ("Arrr").
  - Added the fact schema, plus a prompt rule against listing facts.
  - Second run: 0 of 30 injections shown with the schema on. The model alone still lets 3 of 30 through.
- Checked in the real scene: the fixed line appeared, then the live LLM line replaced it ("That merchant... looks off...").
- Updated `docs/design.md` (the Bram section; stage 5 done), `README.md` and the AI log. 101 GDScript tests passing.

### 4. "review first"
- The user asked for an independent review before merging. The agent sent a fresh reviewer subagent over the `bram-llm` branch.
- The reviewer found no path from the LLM to game state, and nothing critical. It reported 5 important and 7 minor findings. The agent fixed the 5 important ones, each test-first:
  - **Reply checks:** text is normalized first (curly quotes, fullwidth, zero-width, unusual spaces). Replies must be plain English. Theft talk is allowed only on a theft night. "Won/win" claims, spelled-out numbers not in the facts, final-night words the facts don't support, prompt leaks, narration and rude words are rejected, and so are lines that contradict the facts ("plenty of firewood", "trust him"). The over-broad "tier", "prompt" and "system" rules were dropped.
  - **Cold start:** a warm-up call, plus a 60 s timeout until the model first answers. The measured cold start was 4.1 s, which the old 4 s limit would have cancelled.
  - **Tests:** the unreachable-server test now reaches the network. The scene tests use a missing LLM config, so `CROSSROADS_LLM_LIVE=1 tools/run-tests.sh` passes (106).
  - **Eval:** replies in the model-alone run are now checked against the clean facts; success detection is better (French, copied phrases); the cold start is measured; and the docs say plainly that the schema is what blocks injections.
- The new live eval first rejected 3 good lines ("won't" matched "won"). A failing test reproduced it, then the rule was fixed. Final live eval: 256/256 lines OK, 0/30 injections with the schema, 2/30 with the model alone, and a cold start of 4.1 s.
- Deferred minors: a stray comment in `main.gd`; `pending_bram_id` not cleared on the error/end screens; superseded requests not cancelled; no character cap and the 25 vs 30 word mismatch; the schema copies the word lists rather than reading the Dealer constants; and one bad news item would disable later mornings' LLM lines.

### 5. "1" (merge locally)
- Merged `bram-llm` into `main`. On `main`, 106 GDScript tests, 111 Python tests and 6 art-tool tests pass. Deleted the local branch, which was never pushed.

### 6. "yes" (push)
- Pushed `main` to GitHub, including stage 5.

---

## Session 4 - 2026-10-26 (resumed)

### 1. "ok so whats next?"
- The agent checked the state: `main` matches GitHub, and stages 1, 2, 3 and 5 are done. It summarized the remaining options for the user (stage 6, stage 4, the open balance and polish items).

### 2. "i want to run the game from a new terminal window. what do i type?"
- The agent gave the commands (`cd` into the project, then `godot --path game`) and confirmed Ollama is running with `qwen3:4b-instruct`, so Bram's LLM lines will work.

### 3. "start stage 6"
- Started a design conversation (brainstorming) for stage 6: the Linux export and the Steam AI-disclosure review.

### 4. "just do it"
- The user skipped the questions. The agent's calls: Bram's LLM ships as an optional local feature (it uses the player's Ollama if present, otherwise fixed lines, and never contacts an online service), and the work stops at a build and a drafted disclosure, with no Steam upload.
- Branch `stage6-export`. Downloaded the Godot 4.7.2 export templates (1.28 GB), confirmed the SHA-512 against `SHA512-SUMS.txt`, and installed only the Linux templates to `~/.local/share/godot/export_templates/4.7.2.stable/`.
- Added a smoke-test mode (`game -- --smoke-test`), test-first, with 2 new tests: it plays a full week headless and reports params, art and the result. 108 GDScript tests passing.
- Added `game/export_presets.cfg` (Linux; leaves out tests, GUT and tools), `tools/export-linux.sh` (export, notices, then the smoke test of the exported binary), `game/tools/write_notices.gd` (Godot's license text plus the AI model notices), `docs/release.md` and `docs/steam-ai-disclosure.md`. Added `build/` to `.gitignore`.
- Results:
  - The exported build's smoke test passed (`"ok":true`, 7 images, params OK).
  - The `.pck` holds no tests, fixtures, eval tool or GUT code; only the editor-plugin setting names GUT.
  - The windowed build runs with no errors.
  - Fixed one wrong line in the release doc (no `.sh` launcher is made on Linux).
- Updated `docs/design.md`, `README.md` and the AI log.

### 5. "review first"
- The user asked for an independent review of `stage6-export` before merging. The agent sent a fresh reviewer subagent. The diff file was missing at first because the scratch folder hadn't been created; the agent fixed that and told the reviewer.
- The reviewer found nothing critical, and confirmed the build, the export filter and that the smoke test exercises the real release binary. It reported 5 important and 8 minor findings.
- The agent re-graded 2 minors as important, because inaccurate disclosure and legal text shouldn't ship: the guardrail list overclaimed slightly, and the notice wrongly said the images were under the SDXL licence.
- Fixes (scene changes test-first; 6 new tests, 112 GDScript tests passing):
  - **LLM opt-in (Important 1 and 2).** A "Bram's local AI voice" checkbox, off by default and saved in `user://settings.cfg`. No model loads unless the player opts in, and AI-phrased lines are marked "(local AI)". This reverses the agent's earlier "on if Ollama is present" call. The disclosure now says how players switch it.
  - **Notices (Important 3).** They now include every component's copyright lines and licence, plus all 19 full licence texts (2,231 lines). The SDXL wording was corrected (the model, not the images, is under that licence), and the writer handles a failed file write.
  - **Export script (Important 4 and 5).** `timeout 120` on the notices step and the smoke test; the game's exit code is checked; the smoke test must report `"llm_config":"ok"`; the notices must contain licence texts. A negative check (exporting without `bram_llm.json`) failed as it should, and the export was green again once the file was restored.
  - **Docs.** The disclosure's guardrails are worded exactly as they work, and the model-alone injection figure (2/30) is added. The release notes, README and design doc describe the opt-in.
- Deferred minors:
  - `art/provenance.json` is packed (harmless);
  - `rm -rf build/linux` happens before the export, so a failed export leaves no build;
  - import errors are hidden;
  - the smoke run only declines travelers.

### 6. "1" (merge locally)
- Merged `stage6-export` into `main`. On `main`, 112 GDScript tests, 111 Python tests and 6 art-tool tests pass, and `tools/export-linux.sh` passes. Deleted the local branch, which was never pushed.

### 7. "yes please" (push)
- Pushed `main` to GitHub, including stage 6. All six stages in the design doc are now done except the optional stage 4.

### 8. "i am not hearing the voice"
- The agent realized its label "Bram's local AI voice" was misleading: the game has no sound at all. The "voice" only means the local model writes the text in Bram's speech bubble. The agent checked Ollama, the model and the saved setting, then explained this to the user.

### 9. "What is this Steam thing you keep talking about?"
- The agent explained Steam (Valve's PC game store) and its AI-content disclosure, and pointed out that the Steam goal came from the design doc's stage 6 ("Linux export and Steam AI-disclosure review"). Nothing has been uploaded anywhere.

### 10. "rename the checkbox"
- Renamed the checkbox from "Bram's local AI voice" to "Bram's lines written by local AI", in the game, the notices, the README, the design doc, the release notes and the disclosure. The internal setting name stays the same, so the user's saved "on" choice still works.
- Added a test first (the label must not say "voice", since there's no audio). Watched it fail, then pass. 113 GDScript tests passing, and the export passes.
