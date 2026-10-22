# Lessons

What this channel has learned from its own videos. The autopilot reads this before choosing
and writing scripts, and revises it after each analysis (step 1c). Each lesson names its
evidence (run ids, numbers) and its date. Drop a lesson when newer data contradicts it.
Keep it under 40 lines.

## Production

- 2026-10-18: The ElevenLabs voice reads about 2.9 words a second (insurance run: 159 words, 54.8 s).
- 2026-10-18: Keyframes that mention tags, labels or price stickers get garbled text; describe
  objects without anything that carries writing.
- 2026-10-18: Spoken stake in the first five words, an `on_screen_hook` over the first 2.6 s,
  a cut at least every 3.5 s, music bed and whooshes (video 1 had none and stalled), and never
  pad past the last word (7 s of silent ending is a swipe-away).
- 2026-10-19: Rivals show a literal, acting picture every 3-4 s (crops are not new pictures): every
  run has a shot list, an action per shot, labels for numbers, one recurring character.
- 2026-10-19: Z Image draws style words literally ("real-looking hands" put hands everywhere; 10-21:
  "expressive characters" drew a mascot on a wing); style says only the look. Banknotes garble.
- 2026-10-19: Motion prompts that say only what moves, in beats, with one named camera move
  and no "no ..." phrases made the same Hailuo clip move 54% more and act the script; Gen-4.5
  was only a little better at 15x the cost. Evidence: research/runway-bakeoff-2026-10-19.md.

## What viewers respond to

- 2026-10-20: Curiosity beats money. Owner's exports (YouTube Studio, Meta; to Oct 20 14:00 UTC,
  data/imports/2026-10-20-owner.csv): science what-ifs led everywhere (sun 1,321 YouTube / 459 IG /
  244 FB; penny 1,040 YouTube) and the Carrington story held 30 s a view (441 / 166 / 147). Money
  topics (insurance, credit digits, $1 a day) drew 5-6 YouTube views each. Format lift: what-if
  +1.0, micro-story +0.18, odd-object -0.26, money-math -0.33, brain-fact -0.53.
- 2026-10-20: YouTube is all or nothing: 4 of 10 Shorts got 263-1,321 views, the other 6 got
  2-6, even airplane windows (223 FB, 145 IG, 2 YouTube). The same-topic remake of the name video
  got 4 against the original's 263: never repost a topic. The three Shorts after penny (9 uploads
  in 26 h) all stalled; keep YouTube to 2 a day, 6 h apart.
- 2026-10-20: 30-45 s got the most views per hour (lift +0.81, 8 posts; under 30 s -0.66); viewers
  watch 7-12 s at any length. 25 posts: 1 follow, 0 shares, 0 comments, so every script asks a
  `comment_prompt`, and ends on a loop or punchline, as all 10 top Shorts studied do.
- 2026-10-21: Facebook's gate is watch time: waitlisted for Content Monetisation at 8.1 s average
  per Reel vs 15.4 s for similar earners (28-day views 1.5K vs 3.2K). Aim every video at 15 s+.
- 2026-10-22: YouTube Studio (research/youtube-studio-2026-10-22.md): 13 Shorts, 4.5K views,
  17.4 h watched, 107 likes, 0 comments, 7 subscribers. 96.5% of views come from the Shorts
  feed and 48.7% swipe away at once, while the winners keep 64-77% of the rest: the first
  frame and five words decide reach. All four money Shorts drew 0-8 views (untested money
  niches now borrow that result, `family_share`). Airplane windows went from 2 views at 55 h
  to 1,313: judge a Short at 72 h+, never remake it early.
