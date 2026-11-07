# Instagram setup: Worth Knowing

Do this with the VPN off, on the phone app unless a step says otherwise. Images are in
`brand/out/`.

## 1. Account

1. Sign up at https://www.instagram.com/accounts/emailsignup/ (or the app). For the
   email, use a Gmail `+` alias if your main email already has an Instagram account.
2. **Switch to professional:** Settings and activity → Account type and tools → Switch to
   professional account → **Creator** → category **Education** → turn on "Display
   category on profile".
3. **Two-factor:** Accounts Center → Password and security → Two-factor authentication →
   authentication app.

## 2. Edit profile

| Field | What to enter |
|---|---|
| Profile picture | `picture-800x800.png` |
| Name (64 characters, searchable) | `Worth Knowing • Money & Facts`. The name field is matched in search, so it carries two keywords. |
| Username (30 characters) | `worthknowingdaily`. If taken: `worthknowing.hq`, then `getworthknowing`. |
| Pronouns | Leave empty. |
| Bio (150 characters) | `Money, mind & how the world works 🧠💸` · `One short explainer every day` · `Educational only, not financial advice` (one per line) |
| Links | 1. Your YouTube channel, title `YouTube`. From 1,000 followers, put the free cheat sheet first (see monetization). |
| Gender | Prefer not to say. |
| Show Threads badge | Off. |

## 3. Professional settings (Settings and activity → Creator tools and controls)

- **Contact options:** add an email (a `+` alias like `yourname+brands@gmail.com`). Show as button.
- **Branded content:** allow; turn on "Manually approve tag requests".
- **Gifts:** appears at 500 followers (see monetization).

## 4. Privacy and sharing (Settings and activity)

- Account privacy: **Public**.
- Sharing and remixes → Reels: allow remixing and allow downloads (more reach).
- **Reels: "Share to Facebook" / "Recommend on Facebook": OFF.** The autopilot posts each
  video to the Facebook Page itself at Facebook's best time. Sharing from Instagram would
  post it twice.
- Hidden words: turn on "Hide comments" and "Advanced comment filtering".
- Suggested posts and account suggestions on your profile: **on** (helps discovery).

## 5. Link the Facebook Page (once the Page exists)

Follow `brand/facebook-profile.md` step 3: link from the Page (Linked accounts →
Instagram) or from Instagram (Edit profile → Page), then turn Meta's cross-posting off.

## 6. Story highlights

Post each cover as a Story first (it can be hidden from followers right away). Then
Profile → "+" → New highlight, pick the Story and use the same image as its cover.

| Highlight name | Cover |
|---|---|
| Start here | `ig-highlight-start.png` (add your best 3 Reels as Stories over time) |
| Money | `ig-highlight-money.png` |
| AI tools | `ig-highlight-ai-tools.png` |
| How it's made | `ig-highlight-how-its-made.png` |
| History | `ig-highlight-history.png` |
| Space | `ig-highlight-space.png` |
| Mind | `ig-highlight-mind.png` |

## 7. Connect to Metricool

Once the Page is linked, connecting Facebook in Metricool usually brings Instagram with it
(`brand/facebook-profile.md` step 4). Otherwise: Metricool → your brand → Connections →
Instagram → connect through Facebook. Accept every permission it asks for: publishing and
insights both need them. The next autopilot run sees it and starts posting Reels.

## What the autopilot does on Instagram

- **Reel per video**, posted at Instagram's own best slot (weekdays 7:30 PM ET, weekends
  10:30 AM to start; your followers' activity and results move it).
- **AI label on** for every Reel; captions under the limit with up to 5 hashtags.
- **Learning:** watch time, shares and saves feed the daily insights, like YouTube.
- **Monetization ladder** (`config/monetization.yaml`): the daily report tells you when a
  step unlocks.
  - 500 followers: turn on Gifts.
  - 1,000: Creator Marketplace, plus the link-in-bio cheat sheet.
  - 5,000: AI-tool affiliate links.
  - 10,000: Subscriptions.
