# Higgsfield models for faceless shorts: cost and quality (2026-10-18)

Plus plan: 1,000 credits a month, no unlimited allowance on this account
(`models_explore` reports `unlim.available: false`). Prices are `get_cost` quotes, 9:16.

## Keyframes (8 per video)

| Model | Credits | Notes from a side-by-side test |
|---|---|---|
| **Z Image** (`z_image`) | **0.15** | Clean clay and documentary looks at 1152×2048, on par with Seedream 4.5 for this style. **Default.** |
| Seedream 5.0 Flash, 1k | 0.5 | Best detail of the cheap set, 800×1424. **Retry model** when Z Image garbles a frame. |
| Seedream 4.5 | 1.0 | Previous default, 1440×2560. |
| Nano Banana / Nano Banana 2 Lite / GPT Image 2 (low) | 1.0 | No gain for this use. |
| Grok Image 2.0 (low) | 1.25 | |
| FLUX.2 flex | 3.0 | |

## Motion (image-to-video, the biggest cost)

| Model and settings | Credits | Notes |
|---|---|---|
| **Seedance 2.0 Mini, 480p, 4 s** | **2.0** | 496×864 at 24 fps, upscaled to 1080×1920 it reads fine on a phone. **Default.** |
| Seedance 2.0 Mini, 480p, 5 s | 2.5 | |
| Seedance 1.5 Pro, 480p, 4 s | 2.4 | |
| Minimax Hailuo 2.3 fast, 768, 6 s | 4.0 | |
| Seedance 2.0 Mini, 720p, 5 s | 5.0 | Previous default. |
| Grok Video 1.5 Lite, 480p or 720p, 5 s | 5.0 | |
| Kling 3.0 Turbo / Kling 3.0 std / MiniMax H3 Max | 7.5 | |
| Happy Horse 720p 5 s | 12.5 | |

## Voice (one 160-word narration)

| Model | Credits | Notes |
|---|---|---|
| Qwen Audio 3.0 TTS Flash | 0.41 | Cheapest; untested for US English narration quality. |
| Text to Speech V2, Seed Speech | 1.9 | |
| **Text to Speech V2, ElevenLabs** | **2.85** | Kept: the voice carries a faceless video, and the saving would be under 2.5 credits. |
| Seed Audio 1.0 | 6.3 | |

## Tiers this gives (`config/production.yaml`)

| Tier | Per video | Videos a month | A day |
|---|---|---|---|
| **reach** (default): 4 animated moments | ~12 | ~75 | 2 |
| volume: 2 animated moments | ~8 | ~110 | 3 |
| lean (old default) | ~32 | ~28 | 1 |

Reach wins for now. Twice the uploads gives the algorithm twice the tests while the
channel grows, and keeps the motion that holds viewers. Switch to `volume` if the
insights show retention does not drop with fewer animated moments.
