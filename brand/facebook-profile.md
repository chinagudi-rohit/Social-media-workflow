# Facebook setup: Worth Knowing

Do this with the VPN off, from India, on the phone you signed up with. Images are in
`brand/out/`. Order: personal profile ready → Page → Page details → settings → link
Instagram → Metricool.

## 0. If Page creation fails

"An error occurred while creating the page. Please ensure you are following Page
policies" usually means Facebook does not trust the new personal account yet. In order:

1. **Wait.** Give a new personal account 24-48 hours, and try once a day at most. Repeated
   attempts can extend the block.
2. **VPN off.** A VPN location that differs from your sign-up location is a common trigger.
3. **Finish the personal profile:** profile photo, confirmed phone and email, two-factor
   on (Accounts Center → Password and security → Two-factor authentication).
4. **Check restrictions:** Settings and privacy → Settings → Account status. If anything is
   listed, request a review there.
5. **Use a name that is not generic on its own:** `Worth Knowing Daily`, not `Worth
   Knowing`. Facebook rejects Page names that are only a general phrase.
6. **Create it from the Facebook app:** Menu → Pages → Create. The web address is
   https://www.facebook.com/pages/create.

## 1. Create the Page

| Field | What to enter |
|---|---|
| Page name | `Worth Knowing Daily` |
| Category | `Digital creator`. Add `Education` as the second category later in Page details. |
| Bio (101 characters) | `Money, mind & how the world works 🧠💸 One explainer a day. Educational only, not financial advice.` |

Then, in the steps that follow (or Edit details later):

| Field | What to enter |
|---|---|
| Profile picture | `picture-800x800.png` |
| Cover photo | `fb-cover-1640x624.png`. Phones show only its middle; the words are placed there. |
| Username | `worthknowingdaily` (same as Instagram). If taken: `worthknowing.hq`. |
| Website | Your YouTube channel link. Add Instagram as a second link once it exists. |
| Email | A `+` alias, e.g. `yourname+brands@gmail.com` (brands and sponsors write here). |
| Phone, address, hours | Leave empty / "No hours available". It is not a physical business. |
| Action button | `Follow` if offered; otherwise skip. |

## 2. Page settings

Switch into the Page first: your profile picture (top right) → See all profiles → Worth
Knowing Daily. Then Settings and privacy → Settings:

- **Page access:** you have full control. Optionally add a trusted second person with full
  control as a backup, so a locked personal account does not lock the Page too.
- **Privacy → Followers and public content:** who can follow you: **Public**.
- **Reels:** allow remixing (more reach).
- **Professional dashboard → Monetization:** open it once so it starts tracking
  eligibility. Bookmark it.
- **Branded content:** allow, so sponsored posts can be tagged later.

## 3. Link Instagram to the Page

Instagram must be a professional (Creator) account, and you must have full control of the
Page. Do **one** of these:

**From the Page** (phone or desktop): switched into the Page → Settings and privacy →
Settings → Linked accounts → Instagram → Connect account → log in as `worthknowingdaily`.
When asked about Instagram messages in the Page inbox, either answer works.

**From Instagram:** Profile → Edit profile → Page (under "Public business information") →
Connect existing Page → Worth Knowing Daily → Done.

Also add both to the same Accounts Center (Instagram → Accounts Center → Accounts → Add
accounts → Facebook). This makes login and recovery easier.

**Then turn cross-posting off**, in both places Meta offers it:

- Instagram → Settings and activity → Crossposting (or Sharing to other apps) → Facebook →
  Reels: **off**.
- Accounts Center → Connected experiences → Sharing across profiles → Reels: **off**.

The autopilot posts each video to the Page itself, at Facebook's best time. Meta's
cross-post would publish it a second time, which splits views and looks like duplicate
content.

**Check:** the Page's Linked accounts shows Instagram as connected, and Instagram's Edit
profile shows Page: Worth Knowing Daily.

## 4. Connect Metricool (one login covers both)

1. https://app.metricool.com → brand **Worth Knowing** → Connections → **Facebook**.
2. Log in with your personal Facebook account (the Page admin).
3. In Meta's dialog choose **Edit access** → tick **Worth Knowing Daily** and the
   Instagram account → accept every permission (publishing and insights both need them).
4. Pick the Page in Metricool. A linked Instagram usually connects with it; if it does not,
   Connections → Instagram → connect through Facebook.

The next autopilot run sees both networks and starts posting there. Nothing else to
change: `config/platforms.yaml` already lists them as targets.

**Metricool's free plan schedules 20 posts a month.** Two videos a day on YouTube alone is
about 60. With Facebook and Instagram it is about 180. Upgrade to Starter (about €16-20 a
month, priced per brand) before linking, or posts stop partway through the month.

## What the autopilot does on Facebook

- **One native Reel per video** at Facebook's own best slot (weekdays 12:30 PM ET to
  start; your followers' activity and results move it). The AI disclosure line is added to
  every caption.
- **Learning:** views, watch time and shares feed the daily insights, like YouTube.
- **Monetization ladder** (`config/monetization.yaml`). The daily report says when a step
  unlocks:
  - 500 followers: check Professional dashboard → Monetization for **Stars** and turn it
    on if offered (viewers send Stars on Reels; reported to need 500 followers for 30
    days).
  - 5,000 followers: watch for a **Content Monetization** invite (ads on Reels and
    videos) and accept it. Bars reported by third parties range from 5,000 to 10,000
    followers plus watch minutes, and in India it is often invite-only. The Professional
    dashboard shows the real status. Payouts need a PAN and a W-8BEN form.
- **Original content only.** The autopilot renders its own videos; never post another
  platform's watermarked copy.

Sources (third-party guides; Meta's dashboard is the final word):

- https://www.facebook.com/help/104002523024878 (create a Page)
- https://www.facebook.com/help/519912414718764 (Page name rules)
- https://fedica.com/blog/how-to-link-your-instagram-account-to-your-facebook-page/
- https://help.metricool.com/en/article/linking-facebook-to-instagram-17u655e/
- https://help.metricool.com/en/article/connect-facebook-on-metricool-complete-guide-o23pyn
- https://www.shortsync.app/resources/facebook-content-monetization-program-2026
- https://techiegigs.com/how-to-apply-for-facebook-monetization/
- https://socialsizes.io/facebook-cover-photo-size/
- https://www.upload-post.com/metricool-pricing/
