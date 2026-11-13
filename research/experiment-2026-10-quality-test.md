# Quality test 2026-10-quality-test: results (analysed 2026-10-26)

Four quality-tier videos made on 2026-10-19 (shot lists, Hailuo motion), each with its own
format, length, ending, hashtag and style arm, posted to YouTube, Instagram and Facebook.
Stats: Metricool per-video rows pulled 2026-10-26 04:45 UTC (all posts 4-7 days old) and
the owner's YouTube Studio screenshots of 2026-10-22 (retention). 164.68 credits.
Report: `data/experiments/2026-10-quality-test/report.json`.

## The four videos

| Video | Format | Length | Ending | Hashtags | Style | YouTube | Studio retention | Instagram | Facebook |
|---|---|---|---|---|---|---|---|---|---|
| Could a Falling Penny Kill You? | what-if | S | loop | none | photoreal | 1,046 | 75.3% | 323 | 350 |
| Why Airplane Windows Have Tiny Holes | odd-object | M | loop | none | photoreal | 1,314 | 72.1% | 149 | 223 |
| Australia Lost a War to Emus | micro-story | S | cta | niche | cartoon | 4 | | 230 | 250 |
| $1 a Day From Birth = $480,000? | money-math | M | loop | niche | photoreal | 8 | 77.6% | 41 | 15 |

## Winner per variable (median views across platforms; one to three videos each)

| Variable | Winner | Loser | Note |
|---|---|---|---|
| Format | what-if 1,719, odd-object 1,686 (1 each) | money-math 64 (1) | matches the money family's 0-8 YouTube views |
| Length | S 1,102 (2) ≈ M 875 (2) | | no real difference: keep 30-40 s |
| Ending | loop 1,686 (3) | cta 484 (1) | already the script guide's rule |
| Hashtags | none 1,703 (2) | niche 274 (2) | on YouTube: 1,046 and 1,314 vs 4 and 8 |
| Style | photoreal 1,686 (3) | cartoon 484 (1) | both YouTube winners photoreal |

Four videos cannot separate the variables (the two winners share format family, no
hashtags, loop and photoreal), so the changes below follow the direction, not a proof.

## Before and after (all three looks, same three platforms)

| Look | Videos | YouTube | Instagram avg watch | Notes |
|---|---|---|---|---|
| Old look (2026-10-18, before the quality tier) | sun, 1859, name in a crowd, credit cards, insurance | 1,337 / 463 / 324 / 6 / 7 | 5-12 s | two flops were money topics |
| Quality tier (2026-10-19) + pilot remake | the four above + name at a party | 1,046 / 1,314 / 4 / 8 / 7 | 4-11 s | the remake of a 324-view topic drew 7 |
| Locked look (2026-10-21: style key, asset lock) | Gimli Glider, neutron star | 1 / 1 | **18.4 s / 18.3 s** (view rate 69-70%) | Gimli: 1,602 Instagram views, the channel's best Reel |

1. **Top three:** airplane windows, penny, sun: everyday-science questions, photoreal or
   real-looking, no hashtags, a loop back to the opening.
2. **Bottom three on YouTube:** mortgage (1), Gimli (1), neutron star (1). Since 20 Oct
   every new Short has stopped at 1 view on YouTube while Instagram and Facebook kept
   growing, so the cause is the channel's YouTube distribution, not the videos (the Gimli
   Reel is the best Instagram video yet). The owner should check these three in YouTube
   Studio (Content: restrictions, checks, "altered or synthetic" setting; Channel: any
   strike or warning).
3. **The locked look works on Instagram:** average watch rose from 5-12 s to 18 s; Meta's
   bar for Content Monetisation was 15.4 s for similar earners.

## Changes made

- YouTube: no hashtags (`config/platforms.yaml` `youtube.max_hashtags: 0`).
- Style: photoreal for what-if, odd-object and how-it's-made topics; the stylized 3D look
  for character-led stories (autopilot skill, step 3.4).
- Formats: what-if and odd-object lead; money topics are ranked by the money family's
  results (`family_share`, 2026-10-22).
- Ending: loop (already the rule). Length: unchanged (30-40 s).
- `config/experiment.yaml` `active: false`.

## Old-look cleanup (owner's rule: under 50 views after 48 h goes on the delete list)

| Platform | Video | Views | Link |
|---|---|---|---|
| YouTube | Why Credit Cards Have 16 Digits | 6 | https://www.youtube.com/shorts/sG-pQXajn_M |
| YouTube | The Car Insurance Deductible Math Nobody Explains | 7 | https://www.youtube.com/shorts/A7J95zwdcbs |
| Instagram | Why Credit Cards Have 16 Digits | 24 | https://www.instagram.com/reel/Dep3ipZitfD/ |
| Instagram | Why You Hear Your Name in a Crowd | 31 | https://www.instagram.com/reel/DepcFXuEeGg/ |
| Facebook | The Car Insurance Deductible Math | 20 | https://facebook.com/reel/1778923520024339 |
| Facebook | Why You Hear Your Name in a Crowd | 3 | https://facebook.com/reel/1752155479411784 |

Kept: the sun and 1859 everywhere, the noisy-room video on YouTube (324), credit cards on
Facebook (115), insurance on Instagram (146).
