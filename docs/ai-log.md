# AI Log

Short notes on what the agent did, what was fixed by hand, and rough time spent.

## 2026-10-23 - Godot project scaffold
- Agent: installed Godot 4.7.2 to `~/.local/bin/godot` (checksum verified), vendored GUT 9.7.1 into `game/addons/gut`, created `project.godot`, a grey-box main scene, a plain `InnState` rules class, two GUT tests, and `tools/run-tests.sh`.
- Verified: tests pass headless (exit 0), a deliberately failing test exits 1, main scene runs headless with no errors.
- Fixed by hand: nothing.
- Time: ~10 min.

## 2026-10-23 - Paper prototype (stage 1)
- Agent: ran a design conversation with the user, which produced the spec. A reviewer subagent found 4 gaps (2 settled by the agent, 2 answered by the user). The agent then wrote a 9-task plan and built it inline with TDD: a Python `inn_sim` package, an `.ods` reader using only the standard library, a UNO writer that runs headless LibreOffice, careful/random/scripted players, simulate/sensitivity/deal/replay CLI commands, and 88 tests. It then tuned the numbers until the bar passed on two seeds.
- What worked: ablation (turning each randomness source off in turn) quickly showed the spread came from many small sources. Realizing the careful player never looks at the debt let one run of results be scored against every possible debt.
- What went wrong and was fixed by the agent: a Task 6 ruling had small whole-number params move by ±1 instead of 10%, which falsely flagged a dozen params. It was reversed in Task 9 with tests.
- Not solved: the debt ×1.1 sensitivity (careful win 0.586 vs the 0.60 floor) appears to conflict with the tight bar itself. It was escalated to the user.
- Fixed by hand: nothing so far.
- Time: about 1.5 hours of agent time for the whole stage.

## 2026-10-23 - Daily hand-play mode
- Agent: short design check (results first, then the next day), then built `deal --daily` and `next` test-first. 17 new tests, 104 in total.
- Fixed by the agent: one wrong test (it compared a lost run's ledger against a winning run's shape).
- Fixed by hand: nothing.
- Time: about 20 minutes.

## 2026-10-23 - Grey-box Godot prototype (stage 2)
- Agent: did the design conversation with browser mockups (the agent picked the counter layout when asked), wrote the spec (a reviewer found nothing to add) and a 9-task plan, then built it inline test-first. That covered:
  - Python exporters for the params and 20 parity fixtures;
  - a GDScript port of the rules and dealing, plus `DayRunner`;
  - Bram's facts and fixed lines;
  - the counter UI, built in code.

  The result is 72 GDScript tests and 111 Python tests.
- What worked: the parity test passed on all 20 fixtures first time, and a deliberate mutation proved it can fail. Rendering screenshots of the real scene found a bug the tests missed (the night showed the next day's number).
- What went wrong and was fixed by the agent:
  - GUT silently skipped test files that didn't parse and still reported a pass. `run-tests.sh` now fails on script errors.
  - A few GDScript type-inference compile errors.
  - The agent twice wrote an invented description of Bram, once in the plan and once in a code comment, and corrected both to the design doc's wording.
- Fixed by hand: nothing.
- Time: about 1.5 hours of agent time.

## 2026-10-23 - Generated 2D art (stage 3)
- Agent:
  - installed ComfyUI and SDXL base 1.0 (checksum matched), running on the RTX 4090;
  - built a small ComfyUI API client and an asset generator, test-first;
  - generated 7 images: the backdrop, the 5 traveler types, and Bram;
  - added art loading to the scene, with a grey-box fallback.
- Review by eye: the first batch had a backdrop with white unfinished edges, a noble with an ornate frame and an off-style look, and a wanderer who looked too much like Bram. The agent changed seeds and prompts and regenerated, then regenerated the rest so `assets.json` reproduces every image exactly.
- Screenshots of the real scene showed white text was hard to read over the painting. The agent added dark backing panels and hid empty bubbles.
- Fixed by hand: nothing. Time: about 45 minutes, plus about 25 minutes downloading the model.

## 2026-10-23 - Bram's local-LLM dialogue (stage 5)
- Agent: the user skipped the questions.
  - Model: the agent picked Qwen3-4B through the already-installed Ollama.
  - Throwaway spikes found a problem and a fix. The plain `qwen3:4b` tag always writes its reasoning out loud, even with `think: false`, so the agent switched to `qwen3:4b-instruct` (Apache 2.0). Giving the model a code-chosen goal plus Bram's fixed lines as voice examples made its lines usable.
  - Built test-first: `BramVoice` (prompt, reply checks, fact schema), `BramLLM` (non-blocking Ollama client that fails quietly), scene wiring (fixed line first, the LLM line swaps in for the same moment only), and `game/tools/bram_eval.gd`. 101 GDScript tests, plus one opt-in live test.
- Evaluation against the live model: 256/256 lines passed the checks, at a median of about 120 ms.
- Prompt injection: the first run let 2 of 30 injections through ("Arrr"). The agent added a strict fact schema so outside text never reaches the model. With the schema on, all 30 are refused before the model, which shows the schema works. No fact in the game can carry outside text today, so there is no live attack surface. With the schema off, the model alone still lets 2 of 30 through, and `docs/bram-eval.md` records this.
- Independent review (requested by the user) found no path to game state. It did find:
  - real gaps in the reply checks (thief certainty with a curly apostrophe, numbers spelled out, "you won", unannounced final-night words, prompt leaks, narration, non-English text) and over-broad words ("tier", "prompt");
  - a cold-start bug: the measured first load was 4.1 s, against a 4 s timeout that would cancel the load;
  - a test that never reached the network;
  - a live test command that failed;
  - an eval that overstated its result.

  All five were fixed test-first. The new live eval at first rejected 3 good lines ("won't" matched "won"), which was fixed test-first too. 106 tests passing; the live eval shows 256/256 lines OK.
- Slip: the agent wrote "a regular" for Bram in a spike prompt again, and caught it before it reached the real prompt.
- Fixed by hand: nothing. Time: about 1 hour, plus about 13 minutes of model downloads.

## 2026-10-26 - Linux export and Steam AI disclosure (stage 6)
- Agent: the user skipped the questions. The agent decided Bram's LLM ships as an optional local feature (Ollama if present, fixed lines otherwise), and that no Steam upload would happen. It then:
  - downloaded the 1.28 GB Godot 4.7.2 template bundle, checked it against the published SHA-512, and installed only the Linux templates;
  - added a test-first smoke mode (`-- --smoke-test`) so the exported build checks itself;
  - wrote an export preset that leaves out tests, fixtures, GUT and tools, and `tools/export-linux.sh` (export, then the notices file, then the smoke test);
  - wrote a notices writer that uses Godot's own license text;
  - drafted `docs/steam-ai-disclosure.md` and `docs/release.md`.
- Verified:
  - the exported binary's smoke test reports params OK, 7/7 images and a full week played;
  - a check of the `.pck` file showed no tests, fixtures, eval tool or GUT code;
  - the windowed build runs with no errors.
- Fixed by hand: nothing. Time: about 30 minutes, plus the template download.
