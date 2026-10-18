---
name: fm-scripts
description: Chooses and prepares the day's faceless short-video scripts. Picks the best unused library scripts for the top niches, writes a fresh script when a topic is trending, restocks thin niches, and creates validated run folders. Use for a "Choose N script(s) <date>" kanban card, or when asked to write or pick a script for a short.
version: 1.0.0
author: Faceless Monitisation
metadata:
  hermes:
    tags: [faceless, scripts, writing]
    requires_toolsets: [terminal]
---

# fm-scripts

The script decides whether a video earns. Every published video is a library script, or a
script written today, that passes validation and runs over 60 seconds.

## When to Use
- A kanban card titled `Choose N script(s) <date>`.
- An on-demand request from fm-lead for one script on a topic or niche.

## Procedure

1. `kanban_show()`. Take `N` and the date `D` from the card. Read the research card's
   handoff under "Parent task results": top niches and topic ideas.
2. `./fm library pick --count N` lists the best unused scripts across the top niches.
3. **Topical override.** If the research handoff has a topic idea with `trend_boost` >= 2 in
   a top-4 niche, and no library script covers it, write a new script for it (rules below)
   and use it instead of the weakest pick.
4. **Restock.** `./fm library stock`. For each top-4 niche with fewer than 2 unused scripts,
   write 2 new scripts. Write at most 4 new scripts per card, the override included.
5. For each chosen script id: `./fm start-run <script_id>` prints the run folder `RUN`.
   Then `./fm validate RUN` must print ok.
6. `kanban_complete(summary=<topics and niches>, metadata={"runs": ["runs/<run_id>", ...],
   "new_scripts": ["<id>", ...]})`.

On demand (a card from fm-lead with a topic): write one script for that topic, run
`./fm start-run <id>`, then `./fm gen-plan RUN`, and put `estimated_credits` and the hook
in the metadata so fm-lead can quote the cost.

## Writing a script
Follow `templates/script_guide.md` and copy the shape of
`library/scripts/inv-25-vs-35.json`.
- 8 blocks, each 19-24 spoken words. The hook is under 15 words and is the first
  sentence of block 1.
- Write numbers as words in the narration. Digits go in captions only.
- Use a `structure` from `comparison | myth-vs-fact | mistake | how-it-works | story |
  countdown` that the niche has not used recently (see `./fm history`).
- Use a CTA that differs from the niche's last two scripts.
- Give `sources` as `{"claim", "url"}` from gov, .edu or reputable outlets you actually
  opened (`web_search` / `web_extract`). Check that numbers are current for this year.
- `visual` lines describe scenes with no on-screen text, no logos, no celebrities and no
  talking presenter. Keep the niche's `visual_style`.
- No personalised advice and no promises of returns. Neutral, educational framing.
- `id` is `<niche prefix>-<slug>`, equal to the file name. Save it to
  `library/scripts/<id>.json`.
- `./fm library validate` must print `ok (<n> scripts)`. Fix and repeat until it does.

## Pitfalls
- `start-run` refuses a script that was already used. Pick another; never edit a used
  script to reuse it.
- Do not produce video or spend credits. That is fm-producer's card.
- Every new library script must also pass the whole test suite
  (`.venv/bin/python -m pytest -q`): the tests check every library script.

## Verification
Each run in your metadata exists, `./fm validate RUN` prints ok, and
`./fm library validate` prints ok.
