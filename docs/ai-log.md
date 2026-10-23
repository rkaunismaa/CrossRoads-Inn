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
