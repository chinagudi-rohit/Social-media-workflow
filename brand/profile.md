# Nickel Notes: channel profile

The same name everywhere. These handles were free on 2026-10-18: YouTube `@NickelNotes`
and Instagram `nickelnotes`. The Facebook Page username `nickelnotes` was not checked.

## YouTube Studio → Customization → Profile

| Field | Value |
|---|---|
| Picture | `brand/profile-picture.png` (800×800) |
| Banner image | `brand/youtube-banner.png` (2560×1440; all text inside the 1546×423 safe area) |
| Video watermark | `brand/video-watermark.png` (300×300, transparent). Display time: Entire video. Shorts players don't show it; long videos do. |
| Name | Nickel Notes |
| Handle | @NickelNotes |
| Description | Below |
| Links | Instagram: `https://www.instagram.com/nickelnotes`. Facebook: `https://www.facebook.com/nickelnotes`. Add each once it exists. |
| Contact info | Your email, or an alias such as `yourname+nickelnotes@gmail.com`, for sponsor enquiries |

### Description

```
Nickel Notes explains one money idea in about 80 seconds: investing, credit scores, taxes, insurance, real estate, side hustles and the AI tools that save you money.

Every note is made for Americans and backed by sources you can check. They're linked in each video's description.

New note every day.

What you'll learn:
• How compound interest, index funds and fees really work
• 401(k), Roth IRA and HSA rules in plain English
• Credit scores, debt payoff and the fine print banks hope you skip
• Insurance and real-estate math before you sign

Visuals and narration are made with AI tools. Scripts are researched, and every fact is sourced.

For education only. Not financial, tax or legal advice. Talk to a licensed professional about your situation.
```

## YouTube Studio → Settings

| Where | Setting |
|---|---|
| Channel → Basic info | Country of residence: India. Keywords: `personal finance` `money tips` `investing for beginners` `compound interest` `credit score` `401k` `Roth IRA` `HSA` `insurance explained` `side hustle` `AI tools` `money explained` |
| Channel → Advanced settings | Audience: No, set this channel as not made for kids |
| Upload defaults → Basic info | Visibility: Public. Tags: `personal finance, money tips, Nickel Notes` |
| Upload defaults → Advanced settings | Category: Education. Video language: English (United States). Title and description language: English (United States). License: Standard YouTube License. Comments: Hold potentially inappropriate comments for review |
| Community → Automated filters | Block links: on |
| Community → Blocked words | `telegram, whatsapp, t.me, wa.me, signal app, dm me, text me, contact me, message me, account manager, investment manager, crypto mentor, trading signals, forex, binary options, recover funds, recovery expert` |

Scam replies that pose as the channel ("message me on Telegram") are the most common
attack on finance channels. The blocked words and link block catch most of them.

## Same art on the other platforms

- Instagram and Facebook profile picture: `brand/profile-picture.png`.
- Facebook Page cover: `brand/facebook-cover.png` (1640×924).
- Instagram bio, 150 characters max:
  `Money, explained in 80 seconds. 🇺🇸 Investing, credit, taxes. New note daily. Sources in every caption. Education only, not advice.`

Edit `brand/src/` and run `NODE_PATH="$(npm root -g)" node brand/render.mjs` to change the art.
