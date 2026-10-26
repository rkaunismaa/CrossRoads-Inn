# Steam AI-content disclosure (draft)

This is a draft of the answers for the AI section of the Steamworks Content Survey. Steam splits AI content into **pre-generated** content (made with AI tools during development) and **live-generated** content (made by AI while the game runs). Valve's wording and requirements change over time, so check the current Steamworks documentation before submitting.

Everything below can be checked against records in this repository.

## Pre-generated content

**Paste-ready answer:**

> All visual art in Crossroads Inn (the inn backdrop and the six character portraits) was generated with Stable Diffusion XL base 1.0 (Stability AI, CreativeML Open RAIL++-M license), run locally in ComfyUI, then reviewed by hand. Several images were rejected and regenerated. Every image's prompt, seed and settings are recorded so each one can be reproduced. The game was designed and programmed with the help of an AI coding assistant (Claude Code). All of its work was reviewed, tested and committed by the developer. No AI-generated audio is used.

**Where the evidence is:**
- `tools/comfyui/assets.json` holds the prompts, seeds and model, and `game/art/provenance.json` records each generated image.
- `docs/ai-log.md` records what was regenerated and why.
- `docs/session-history.md` is the full record of the AI-assisted development.

## Live-generated content

**Paste-ready answer:**

> "Bram's lines written by local AI" is an optional setting, off by default. If the player turns it on and has Ollama installed with the Qwen3-4B Instruct model (Apache 2.0), the recurring character Bram may have his one-line comments phrased live by that model, running entirely on the player's own machine. Lines phrased this way are marked "(local AI)" on screen. The game does not include, download or contact any online AI service. With the setting off, or without Ollama, Bram uses hand-written lines. The model never decides anything in the game: all outcomes, numbers and events come from game code.
>
> Guardrails:
> 1. **Input.** The model only receives a small set of facts built by game code (for example the day, the weather, the traveler's kind, and whether Bram is suspicious). Each fact is checked against a strict schema of known keys, types and words before sending, so no player-written or outside text can reach the model.
> 2. **Output.** Every reply is checked before it is shown. A reply is thrown away if it:
>    - is over 30 words, or contains characters outside plain ASCII;
>    - contains numbers (digits or number words) not in the facts;
>    - shows signs of breaking character or echoing its instructions;
>    - looks like narration rather than speech;
>    - contains a word from a profanity list;
>    - talks about theft when none happened, or claims a win;
>    - names a final-night event the facts don't support;
>    - makes certain specific contradictions of the facts (such as "plenty of firewood" when firewood is short).
>
>    When a reply is rejected, the hand-written line stays. These are pattern-based checks, not a guarantee.
> 3. **Testing.** An evaluation runs the real model over hundreds of game moments and a prompt-injection suite (`docs/bram-eval.md`). The injection results show that the input check is what stops injections: with it switched off, the model on its own followed 2 of 30.

**Where the evidence is:**
- `game/scripts/bram/bram_voice.gd` has the schema and reply checks; `game/scripts/bram/bram_llm.gd` has the local-only client.
- `docs/bram-eval.md` has the live results: 256 of 256 lines passed in normal play, and all injections were refused with the schema on.
- Players switch the feature on or off with the "Bram's lines written by local AI" checkbox, which is off by default and saved in `user://settings.cfg`. The developer can remove the feature at build time with `"enabled": false` in `game/data/bram_llm.json`.

## Open questions for the developer before submitting

- **Code.** Steam's survey focuses on content players see. Decide whether to mention the coding assistant at all; the draft mentions it for transparency.
- **The local LLM.** Bram's lines only come from the LLM if the player turns the setting on and installs Ollama themselves. Decide whether to describe this as an optional feature on the store page.
- **Reporting.** Steam lets players report live-generated content through the overlay. Confirm what Valve currently requires for that.
