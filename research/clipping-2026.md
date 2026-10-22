# Is "clipping" a good way to grow Worth Knowing?

Research date: 2026-10-18. Channel: Worth Knowing, a faceless, AI-made YouTube Shorts channel
(also posted to Instagram Reels and Facebook Reels; TikTok is not a target because it is blocked in
India, per `config/platforms.yaml`). The goal is reach now and the YouTube Partner Program (YPP)
later.

## How this was researched, and how far to trust it

- **Pages were not read directly.** In this environment WebFetch and curl could not reach any
  page: DNS failed, or the egress proxy returned 403. Every claim below therefore comes from
  search-engine summaries of the URL cited next to it. Re-read the key YouTube Help pages before
  acting on exact wording.
- **Labels used in this file:**
  - **[vendor]**: the source sells a clipping tool or service, or is an affiliate blog. Treat its
    numbers with care.
  - **[unverified]**: only one source says it, sources conflict, or the claim is old.
  - **[repo]**: taken from this repository, not from the web.
- **No numbers were invented.** Where no data was found, the text says so.

---

## 0. Short answer

| Option | Use for Worth Knowing? |
|---|---|
| (a) Paid clipping marketplaces (Whop Content Rewards, Vyro, ClipFarm) | **No, not on the main channel.** At most a separate, manual side experiment. |
| (b) Clipping other creators' videos without permission | **No, on any channel.** |
| (c) YouTube's built-in reuse (Remix "Cut"; Clips was retired) | **Occasionally and by hand at most.** It cannot be automated and adds little. |
| (d) Public-domain and openly licensed footage as B-roll inside original narrated explainers | **Yes, on the main channel.** Fits the space, history and how-it's-made niches. |
| (e) Own long-form to Shorts, and the reverse | **Later.** The channel has no long-form yet. Revisit when going for watch hours. |

---

## 1. What "clipping" means in 2025-2026

### 1a. The clipping economy (paid per 1,000 views)

**How it works**

- A brand or creator funds a campaign, supplies long-form source material, and sets a reward per
  1,000 views. Clippers cut short clips and post them on **their own accounts** on TikTok, Reels
  and Shorts. They submit the post link, and the brand approves it before views are paid.
  Sources:
  [Whop docs](https://docs.whop.com/memberships-and-access/third-party-apps/content-rewards),
  [Whop blog](https://whop.com/blog/whop-content-rewards/),
  [Picsart](https://picsart.com/blog/what-is-a-clipping-campaign/),
  [Ssemble on Vyro](https://www.ssemble.com/blog/vyro-review-2026) [vendor].
- Campaign briefs often ask for a dedicated account for that brand or niche, for example
  "create a dedicated account for WayinVideo game clips".
  Sources: [WayinVideo brief](https://app.notion.com/p/WayinVideo-Game-Clipping-Campaign_July-3903f2ea3aed80f7be44c531ae856216),
  [ClipAffiliates](https://www.clipaffiliates.com/blog/how-to-make-money-clipping-on-tiktok) [vendor].

**Whop Content Rewards mechanics (Whop's own docs)**

Source: [Whop docs](https://docs.whop.com/memberships-and-access/third-party-apps/content-rewards).

- The brand sets the reward rate per 1,000 views.
- A **minimum payout** decides which videos reach the brand's review queue. Whop's example: a $3
  rate with a $6 minimum, so a video needs about 2,000 views to qualify.
- A **maximum payout** caps each video. Whop's example: $3,000 at a $3 rate, so a video stops
  earning at 1 million views.

**Payout timing and fees**

- The Creator Terms describe CPM payout rounds as a 7-day earning period followed by a 3-day hold
  while views are verified and fraud checks run.
  Sources: [Whop Content Rewards app terms](https://b4e0vdqv6zgqeqj4pfgm.apps.whop.com/terms),
  [ClipSpeed](https://www.clipspeed.ai/blog/whop-content-rewards-clipping-guide.html) [vendor].
- A 10% "Content Reward Fee" is widely reported. Sources disagree on whether the brand or the
  clipper pays it [unverified].
  Source: [ClipSpeed](https://www.clipspeed.ai/blog/whop-content-rewards-clipping-guide.html) [vendor].

**Typical rates**

| Finding | Source |
|---|---|
| Median $1.00 per 1,000 views across 50 campaigns | [Foundry](https://www.builtbyfoundry.io/blog/what-is-clipping-1-dollar-per-1000-views-50-campaigns) [vendor] |
| Live range $0.20 to $6, averaging about $1 | [OpenClip](https://openclip.app/guides/whop-clipping-guide) [vendor] |
| 100 campaigns on 2026-10-12: $0.20 to $5.00, median $1.30 | [Shopiator](https://shopiator.com/blog/whop-content-reward-campaigns) [vendor] |
| Whop's own examples for clipping: about $0.30 to $1 | [Whop blog](https://whop.com/blog/whop-content-rewards/) |
| NPR (May 2026): $1 per 1,000 views for MLB clips, $25 for an AI startup's product, $0.50 from Polymarket | [NPR via HPPR](https://www.hppr.org/2026-05-12/the-clipping-economy-how-short-form-video-clippers-are-overrunningthe-internet), [NPR transcript](https://www.npr.org/transcripts/nx-s1-5794670-e1) |

**Vyro (MrBeast's platform, launched October 2025)**

- The headline rate is $3 per 1,000 views, with no follower minimum. Views are tracked on TikTok,
  Reels and Shorts.
  Sources: [Influencer Marketing Hub](https://influencermarketinghub.com/mrbeast-launches-vyro/),
  [Matt Navarra](https://www.threads.com/@mattnavarra/post/DVbkecZCuhD/mrbeast-has-launched-vyro-a-marketplace-paying-fans-to-clip-long-form-videos).
- Later reviews say live MrBeast campaigns pay $1 to $2, and only on posts above 5,000 views
  [unverified].
  Sources: [DareBay](https://darebay.com/en/earnings/vyro-review) [vendor],
  [Growthr](https://growthr.com/resources/best-clipping-platforms/) [vendor].
- Withdrawals go through Stripe or PayPal depending on country, with a $10 minimum.
  Source: [Ssemble](https://www.ssemble.com/blog/vyro-review-2026) [vendor].

**ClipFarm**

- Launched in August 2024 by YouTuber Airrack together with Whop. It is a pay-per-view model.
  Source: [FindClout](https://findclout.com/blog/clipfarm) [vendor, competitor].
- One listed campaign paid $1.50 per 1,000 views on TikTok and Instagram, capped at $400 per clip.
  Source: [ContentRewards listing](https://contentrewards.com/discover/e651db03-3395-4562-ab83-4a74a391370f).

**Scale and reach data**

- One gaming-brand campaign spent $841,850 over four months for 1.56B views, an effective $0.54
  per 1,000 views.
  Source: [Forkoff](https://forkoff.xyz/blog/clipping/whop-content-rewards-brand-cost-2026) [vendor].
- A June 2026 snapshot claims 1.76B+ views across all campaigns and $930K+ paid out.
  Source: [contentrewards.xyz](https://contentrewards.xyz/).
- Platform-wide payout totals conflict between sources, so treat them as [unverified].
- **No source gave per-clip median views.** NPR reports that many clippers quit within a week
  because they got no views.
  Source: [NPR via HPPR](https://www.hppr.org/2026-05-12/the-clipping-economy-how-short-form-video-clippers-are-overrunningthe-internet).
- One guide estimates beginners earn $100 to $500 a month.
  Source: [OpenClip](https://openclip.app/guides/how-much-do-clippers-make) [vendor].

**Requirements**

- Clippers must be 18 or older with a Whop account in good standing [unverified: it was not clear
  which page says this].
  Sources: [Sprites](https://www.sprites.ai/blog/whop-clipping-guide),
  [Whop docs](https://docs.whop.com/memberships-and-access/third-party-apps/content-rewards).
- Brands often buy US or Tier-1 audiences. One campaign required at least 50% US audience, and full
  rates often apply only to views that pass geography checks.
  Sources: [Lumina](https://luminaclippers.com/blog/what-is-a-clipping-campaign) [vendor],
  [FindClout](https://findclout.com/blog/how-to-verify-clipping-campaign-views) [vendor].
- Paid clips are adverts and need a clear disclosure such as #ad or a paid-partnership tag.
  Sources: [FindClout](https://findclout.com/blog/clipping-ftc-disclosure) [vendor],
  [Lumina](https://luminaclippers.com/blog/is-clipping-legal) [vendor].
- In June 2026, consumer advocates sued Polymarket, alleging it paid clippers $1 per 1,000 views to
  spread undisclosed clips through fake accounts. These are allegations, not findings.
  Sources: [NACA complaint](https://www.consumeradvocates.org/wp-content/uploads/2026/06/NACA-v.-Polymarket-complaint.pdf),
  [Kelley Drye](https://www.kelleydrye.com/viewpoints/blogs/ad-law-access/all-bets-are-off-as-polymarket-faces-lawsuit-over-influencer-campaigns).

**Can someone in India join and get paid?**

- Whop's payout docs list India among 200+ payout countries. Methods are bank (through Whop
  Payments, which needs KYC), PayPal and Coinbase, with a $10 minimum.
  Source: [Whop payouts docs](https://docs.whop.com/manage-your-business/manage-payouts/set-up-payouts).
- **No source confirms that Content Rewards payouts specifically work for Indian clippers**
  [unverified].
- One low-quality source suggests Whop's KYC blocks some countries.
  Source: [Whipscribe](https://whipscribe.com/clipping/earn) [unverified].
- TikTok is still banned in India, and most campaigns pay on TikTok views.
  Sources: [TechCrunch, Aug 2025](https://techcrunch.com/2025/08/22/tiktok-denies-india-comeback-after-reports-of-website-going-live),
  [Storyboard18](https://www.storyboard18.com/amp/brand-makers/tiktok-ban-in-india-still-stands-company-clarifies-after-brief-website-access-79505.htm).

**What this means for Worth Knowing**

- Marketplace clipping pays per view, but the clips are someone else's brand. They would not build
  Worth Knowing's audience.
- Posting them on the main channel would:
  - make it look like a reupload channel (see 1b);
  - add paid-promotion disclosures;
  - mix off-topic brands into the feed.
- Even with the brand's permission, YouTube's reused-content policy still applies (see 1b).

### 1b. Clipping other creators' long-form videos without permission

**Copyright**

- Fair use is decided case by case on four factors, and only a court can decide it.
- Crediting the owner, or writing "no infringement intended", does not make a copy fair use.
- Uses that substitute for the original are unlikely to be fair use.
- Sources: [YouTube fair use](https://support.google.com/youtube/answer/9783148),
  [Fair use FAQ](https://support.google.com/youtube/answer/6396261),
  [Copyright myths](https://support.google.com/youtube/answer/2797449).
- There is no "safe" clip length, and commercial clipping weighs against fair use.
  Source: [ReachCat](https://reach.cat/blog/is-clipping-legal-copyright-fair-use/) [vendor].
- Podcast background music is often licensed for the podcast only. Reusing it in a clip can be a
  separate infringement.
  Source: [SRIPLAW](https://sriplaw.com/blog/why-your-podcast-clips-might-be-violating-music-rights/).
- Fair use is a US doctrine. Other countries mostly use narrower "fair dealing".
  Source: [ReachCat](https://reach.cat/blog/is-clipping-legal-copyright-fair-use/) [vendor].
- Some platforms forbid clipping. For example, Netflix reportedly bars podcasters on its platform
  from clipping to YouTube [unverified].
  Source: [OpusClip blog](https://www.opus.pro/blog/netflix-bans-podcast-clipping-youtube-creators-need-ai-video-tools) [vendor].

**Enforcement on YouTube**

- **Three copyright strikes:** the channel is subject to termination. Linked channels can be
  terminated too, and the owner cannot create new channels.
  Source: [Copyright strikes](https://support.google.com/youtube/answer/2814000).
  - **This means a "separate" clip channel tied to the same owner can put the main channel at
    risk.**
- **Shorts over 1 minute:** any active Content ID claim, including a manual one, blocks the Short
  worldwide. It cannot be played, recommended or monetized.
  Source: [Three-minute Shorts](https://support.google.com/youtube/answer/15424877).

**Monetization: YouTube's reused-content policy**

Source: [Channel monetization policies](https://support.google.com/youtube/answer/1311392).

- It is judged at the level of the whole channel.
- It is separate from copyright and **applies even with the original creator's permission**.
- Not allowed:
  - "clips of moments … edited together with little or no narrative";
  - short videos compiled from other social media sites.
- If YouTube "cannot clearly tell that you made the content", monetization may be removed from
  the entire channel.

**Shorts revenue**

- These do not count toward revenue:
  - unedited clips from others;
  - reuploads of other creators' content;
  - compilations with no original content.
- When a Short includes third-party or remixed content, its views are split with rights holders.
- Source: [Shorts monetization policies](https://support.google.com/youtube/answer/12504220).

**Inauthentic-content policy**

- **July 2025:** "repetitious content" was renamed "inauthentic content". YouTube said reused
  content rules did not change.
  Sources: [Search Engine Journal](https://www.searchenginejournal.com/youtube-clarifies-monetization-update-targeting-spam-not-reaction-channels/550755/),
  [PPC Land](https://ppc.land/youtube-clarifies-inauthentic-content-policy-changes/).
- **July 2026:** the policy was clarified into three named categories:
  - generic or repetitive content;
  - unsatisfying or off-putting content;
  - AI personas giving advice on sensitive topics.
  Source: [TechCrunch, 2026-07-20](https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/).

**Reach: the October 2026 Shorts change**

- On 2026-10-01, YouTube said Shorts recommendations will favor original content. Channels that
  mainly reupload or aggregate others' clips without significant changes will get less reach.
- No start date was given, no threshold, and no notice to affected channels.
- Sources: [PPC Land](https://ppc.land/re-uploaded-shorts-lose-reach-as-youtube-favours-original-clips/),
  [Android Headlines](https://www.androidheadlines.com/2026/10/youtube-cuts-reach-reuploaded-shorts-originality-push.html).
- Creator Liaison Rene Ritchie said added value means "not just VO descriptions of what's
  happening on screen, minor technical edits, or template-based bulk changes". He suggested
  sharing other creators' videos through the Posts tab instead.
  Source: [Search Engine Journal](https://searchenginejournal.com/youtube-original-shorts-reposted-clips-reach/591774/).

**Other platforms the channel posts to**

- **Facebook (July 2025):** accounts that repeatedly reuse others' videos lose monetization for a
  period and get less distribution.
  Source: [TechCrunch, 2025-07-14](https://techcrunch.com/2025/07/14/following-youtube-meta-announces-crackdown-on-unoriginal-facebook-content).
- **Instagram:** accounts that mainly share unoriginal content are no longer eligible for
  recommendations.
  Source: [Communicate Online](https://communicateonline.me/news/instagram-expands-crackdown-on-reposted-content-across-platform/).
- **Meta's March 2026 definition:** narration that only describes someone else's clip does not
  count as original [unverified].
  Source: [NoFaceTube](https://nofacetube.com/rules/meta-unoriginal-content-crackdown/).

**What this means for Worth Knowing**

- Unpermitted clipping is high risk on every axis: strikes, blocked Shorts over 60 seconds,
  channel-wide demonetization and, since October 2026, reduced reach.
- Worth Knowing's narration is AI voice. Narration that describes someone else's footage is
  exactly what Ritchie and Meta say does not count.
- Do not do this on any channel.

### 1c. YouTube's built-in ways to reuse others' videos

**Shorts Remix**

Sources: [Remix help](https://support.google.com/youtube/answer/10623810),
[Remix opt-out help](https://support.google.com/youtube/answer/14946424),
[YouTube blog](https://blog.youtube/news-and-events/youtube-shorts-remix/).

- The options are Sound, Green Screen, Cut and Collab.
- **Cut** samples a 1 to 5 second segment of another video, picture and audio.
- **Sound** can use up to 90 seconds of audio. Some partner videos are limited to 30 seconds.
- Visual remix is unavailable for Shorts that carry third-party claims.
- Creators can opt their Shorts out of remixing.
- Remix appears to be mobile-only, with no API found [unverified].
  Source: [CollabPals](https://www.collabpals.com/tools/youtube-shorts-remix-checker) [vendor].

**AI remix tools**

- "Extend with AI" (September 2025) and the 2026 "Reimagine" and "Add Object" tests work on clips
  of up to about 5 to 8 seconds. They are English-only and exclude the EU and UK.
  Sources: [PPC Land](https://ppc.land/youtube-shorts-remix-gains-ai-powered-extend-feature-for-creators/),
  [PhoneArena](https://www.phonearena.com/news/youtube-test-reimagine-add-object-capabilities-in-shorts-remix_id178617).
- It is unclear whether AI-remix output counts as "original" under the October 2026 change.
  Source: [AI Weekly](https://aiweekly.co/alerts/youtube-downranks-re-uploaded-shorts-ai-remix-status-unclear).

**YouTube Clips was retired on 2026-04-17**

- Viewers can no longer create clips. Share-at-timestamp replaces it.
- YouTube promised "Video Clips to Shorts" with auto-suggestions "later this year". As of October
  2026 there is no confirmed launch [unverified].
- Sources: [9to5Google](https://9to5google.com/2026/04/17/youtube-clips-share-at-time-changes/),
  [Tubefilter](https://www.tubefilter.com/2026/04/17/youtube-clipping-tool-viewer-clips-shorts/),
  [Segue](https://segue.video/youtube-clips-retirement/).

**What this means for Worth Knowing**

- Remix gives at most a few seconds of someone else's footage, by hand, in the mobile app.
- It is fine as an occasional manual touch, for example reacting to a viral science clip.
- It cannot be part of an automated pipeline, and its value for reach is unmeasured: no data found.

### 1d. Public-domain and openly licensed long-form footage

**United States government works**

- Works by federal employees in their official duties have no US copyright.
- Contractor and grantee works are not automatically covered.
- Sources: [17 U.S.C. § 105 (govinfo)](https://www.govinfo.gov/content/pkg/USCODE-2020-title17/html/USCODE-2020-title17-chap1-sec105.htm),
  [Cornell LII](https://www.law.cornell.edu/uscode/17/105.html).

**NASA**

- **Status:** NASA content is "generally not copyrighted" and may be used without permission.
- **Exceptions:**
  - Material marked as copyrighted needs the owner's permission.
  - Some NASA videos contain licensed music or third-party footage.
- **Endorsement and logos:**
  - Do not imply NASA endorses anything.
  - The NASA insignia, logotype and seal need explicit permission.
  - Recognizable astronauts or talent raise publicity rights in commercial use.
- **Credit:** credit NASA. JPL asks for "Courtesy NASA/JPL-Caltech".
- **Sources:** [NASA advertising guidelines](https://www.nasa.gov/nasa-brand-center/advertising-guidelines/),
  [NASA brand guidelines](https://www.nasa.gov/nasa-brand-center/brand-guidelines/),
  [JPL image use policy](https://www.jpl.nasa.gov/jpl-image-use-policy/),
  [GPM image use policy](https://gpm.nasa.gov/image-use-policy).
- **Scientific Visualization Studio (SVS):**
  - Content is public domain unless noted.
  - Some visualizations use licensed music. The pictures can be reused without that audio.
  - Credit line: "NASA's Scientific Visualization Studio".
  - Source: [SVS FAQ](https://svs.gsfc.nasa.gov/help/).
- **Image and Video Library API:**
  - The `images-api.nasa.gov` search accepts `media_type=video`.
  - `/asset/{nasa_id}` lists the files for an item.
  - `/captions/{nasa_id}` returns caption files.
  - No API key is needed.
  - Sources: [API docs (PDF)](https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf),
    [Jentic](https://jentic.com/apis/nasa.gov/nasa).

**National Archives (NARA)**

- Federal agency films are treated as public domain.
- Donated collections and some newsreels carry restrictions.
- NARA does not guarantee status. The user is responsible.
- Source: [NARA permissions](https://www.archives.gov/research/motion-pictures/permissions).

**Library of Congress, National Screening Room**

- Most titles have no known restrictions and are free to reuse. They download as MP4 or ProRes.
- Some titles are permitted for streaming or educational use only. Check each catalog record.
- Sources: [LoC rights and access](https://www.loc.gov/collections/national-screening-room/about-this-collection/rights-and-access/),
  [LoC 2018 announcement](https://www.loc.gov/item/prn-18-125/).
- The Citizen DJ subset is identified as public domain and free for commercial use.
  Source: [Citizen DJ](https://citizen-dj.labs.loc.gov/loc-national-screening-room/use/).

**Prelinger Archives on archive.org**

- Reuse follows the license shown on each film's page.
- About 60 to 65% of the holdings are public domain.
- The Archive asks for a credit such as "Archival footage supplied by Internet Archive (at
  archive.org)".
- Sources: [Archive help](https://help.archive.org/help/prelinger-archive/),
  [Wikipedia](https://en.wikipedia.org/wiki/Prelinger_Archives).

**ESA (European Space Agency)**

- Some ESA images and videos are CC BY-SA 3.0 IGO, but only where an item says so.
- Credit example: "ESA/…, CC BY-SA 3.0 IGO".
- Some ESA galleries require approval for advertising use.
- Sources: [ESA open access](https://open.esa.int/?p=2),
  [XMM-Newton conditions](https://cosmos.esa.int/web/xmm-newton/conditions).
- ShareAlike may require the adapted Short itself to carry BY-SA. This is a legal nuance, not
  confirmed; avoid BY-SA unless that is acceptable.

**Creative Commons BY videos on YouTube**

- Reuse needs credit: title, author, source URL and license, on screen, spoken or in the
  description.
- Videos with Content ID claims cannot carry the CC BY label.
- Source: [License types on YouTube](https://support.google.com/youtube/answer/2797468).
- See section 2 for the download problem.
- General attribution format (title, author, source, license, plus a note of changes):
  [uOttawa guide](https://www.uottawa.ca/library/copyright/what-is-copyright/how-attribute-creative-commons-licensed-content-best-practices).

**Content ID and public-domain footage**

- Public-domain footage cannot be used as a Content ID reference. Content that is not eligible for
  Content ID must not be claimed manually either.
  Sources: [Content ID eligibility](https://support.google.com/youtube/answer/2605065),
  [Reference best practices](https://support.google.com/youtube/answer/107008).
- False claims still happen on NASA and Apollo footage, and disputes get them restored.
  Sources: [Techdirt](https://www.techdirt.com/2021/04/07/content-moderation-case-study-nasa-footage-taken-down-youtube-moderation-2012/),
  [Boing Boing](https://boingboing.net/2022/07/21/copyright-trolls-claim-public-domain-footage-of-apollo-moon-landing-on-youtube.html).
- If you prove the content is public domain, you can monetize it.
  Source: [What can I monetize](https://support.google.com/youtube/answer/2490020).

**Does YouTube treat this as reused content?**

- **Yes, if the footage is the product.** The reused-content test is about the creator's added
  value, not about rights.
  Source: [Channel monetization policies](https://support.google.com/youtube/answer/1311392).
- Older YouTube guidance named "videos consisting solely or mainly of public domain work created
  by other people" as hard to monetize [unverified, old wording quoted by a blog].
  Source: [longzijun](https://longzijun.wordpress.com/2018/06/15/youtube-monetization-and-the-issue-of-duplication/).
- **Used as B-roll under an original script, voiceover, captions and AI illustration**, the
  original explainer is the product. Third-party guides list "educational explainers that teach a
  topic clearly" as lower risk.
  Sources: [TunePocket](https://www.tunepocket.com/reused-content-youtube-guide/) [vendor],
  [vidIQ](https://vidiq.com/blog/post/youtube-reused-content-policy-guide/) [vendor].

**Precedent and reach data**

- NASA promotes creative reuse of its archive. The CineSpace competition requires NASA archive
  footage in entries.
  Source: [HeySuccess listing](https://www.heysuccess.com/opportunity/2026-CineSpace-Short-Film-Competition-by-NASA-and-Houston-Cinema-Arts-Society-(HCAS)-34055).
- NASA Goddard publishes vertical videos that pair archival footage with current missions
  ("SpaceBack") [unverified].
  Source: [SVS page](https://svs.gsfc.nasa.gov/api/14278).
- **No reach data was found** for Shorts that use public-domain footage, or for real footage
  versus AI imagery. The channel's own A/B results (`pipeline insights`) would have to answer it.

### 1e. Own long-form to Shorts, the reverse, and related-video links

**Making Shorts from your own long-form**

- You can make a Short from your own long-form video in YouTube. An older help page says up to 60
  seconds [unverified for 3-minute Shorts].
  Source: [Create Shorts from your videos](https://support.google.com/youtube/answer/12836917).
- Studio's "Video Clips" tool cuts segments from your own videos and live streams into new
  videos.
  Source: [Video clips and Shorts in Studio](https://support.google.com/youtube/answer/15824265).

**Related-video links from Shorts**

- A related-video link can point a Short to one of your own public or unlisted videos. It needs
  advanced features. It is added automatically when a Short is made with the clips tool.
  Source: [Add a related video](https://support.google.com/youtube/answer/14075157).
- Links in Shorts descriptions and comments are not clickable.
  Source: [Sharing links](https://support.google.com/youtube/answer/13748639).

**Conversion data, all mixed**

| Finding | Source |
|---|---|
| Related-video links sometimes convert under 1% | [Subscribr](https://subscribr.ai/p/youtube-shorts-hurting-long-form-views) [vendor] |
| Most Shorts viewers never leave the Shorts feed | [OutlierKit](https://outlierkit.com/resources/youtube-shorts-to-long-form/) [vendor] |
| A 20% long-form lift for one channel with closely themed Shorts | [Spotter](https://spottercommunity.beehiiv.com/p/increase-views-from-related-shorts) [vendor] |
| Long-form views declined after creators started Shorts (study of 250 creators) | [arXiv 2402.18208](https://arxiv.org/abs/2402.18208v2) |
| No consistent harm found (37 channels) | [OverseerOS](https://www.overseeros.com/blog/do-youtube-shorts-hurt-long-form-views) [vendor] |

**Compiling your own Shorts into long-form**

- No official ruling was found.
- The reused-content policy reviews "compilations". A stitched reel with no new material could
  also fall under "repetitive" inauthentic content.
- Adding new narration, structure and context is what makes it defensible.
- Source: [Channel monetization policies](https://support.google.com/youtube/answer/1311392).

**What this means for Worth Knowing**

- The channel has no long-form today, so there is nothing to clip.
- Long-form becomes relevant when chasing watch hours (section 5).
- A weekly or monthly "deep dive" built from a niche's Shorts can work, but only with new
  narration and connecting material. Link each Short to it with the related-video link.

---

## 2. Tools

**Automated clipping tools**

All of these find highlights in long talking-head or stream content you supply. None of them
solves rights.

| Tool | Price (third-party reports) | API | Source |
|---|---|---|---|
| OpusClip | Free with 60 credits a month (1 credit = 1 minute of input video). Starter $15/mo with 150 credits. Pro $29/mo with 300 credits. | Business tier only (custom price) | [Creatify](https://creatify.ai/blog/opusclip-pricing-plans-and-what-you-ll-actually-pay-in-2026) [vendor], [Castmagic](https://www.castmagic.io/fr/blog/opus-clip-pricing) [vendor] |
| Vizard | About $14.50/mo on annual billing or $29/mo monthly. Free tier of 60 credits with a watermark. | Public API reported from the Creator tier (sources conflict) | [Plisio](https://plisio.net/ai/vizard-ai), [Ssemble](https://www.ssemble.com/blog/best-ai-clipping-tools-2026) [vendor] |
| Klap | $14 to $29/mo quoted | None found | [Choppity](https://www.choppity.com/blog/best-opus-clip-alternatives/) [vendor] |
| Munch | About $49/mo Pro (200 upload minutes). No free plan. | None found | [Ssemble](https://www.ssemble.com/blog/best-ai-clipping-tools-2026) [vendor] |

**Higgsfield**

Sources: tool schemas loaded in this session;
[Higgsfield blog](https://higgsfield.ai/blog/how-to-make-youtube-shorts-with-ai).

- It has no highlight finder for long videos.
- **Shorts Studio** restyles one uploaded 4 to 120 second video into AI-styled clips at 720p, using
  a style preset. It is paid. Higgsfield's blog cites about $4 per 25-second clip (checked July
  2026).
- **`reframe`** outpaints a video of up to 60 seconds to 9:16, using credits.
- **`video_analysis_create`** gives a scene-by-scene analysis and accepts a YouTube URL.
- **`media_import_url`** imports any HTTPS media file of up to 50 MB.
- Outpainting real archival footage with AI would invent picture content around a historical
  record. Prefer a free ffmpeg crop or blurred-background pad.

**For this pipeline**

- None of these tools is needed. `tools/assemble.py` already downloads clips with ffmpeg, crops
  them to 1080x1920 and burns captions [repo].
- The missing pieces are a start offset, muting, and a pad mode for 4:3 or 16:9 sources (see
  section 4).

**Downloading from YouTube with yt-dlp**

- YouTube's Terms forbid users to "access, reproduce, download, distribute … any part of the
  Service or any Content" except:
  - as expressly authorized by the Service;
  - with prior written permission from YouTube and the rights holders;
  - in the 2022 wording, as permitted by applicable law.
  Sources: [YouTube Terms](https://www.youtube.com/terms),
  [archived 2022 Terms](https://webcf.waybackmachine.org/web/20220423214446/https://www.youtube.com/t/terms),
  [Python Discord quoting the Terms](https://www.pythondiscord.com/pages/tags/ytdl/).
- The YouTube API Developer Policies (section III.E.1) also bar downloading or storing YouTube
  audiovisual content without YouTube's prior written approval.
  Source: [Developer policies](https://developers.google.com/youtube/terms/developer-policies).
- A CC BY license gives copyright permission but not YouTube's contractual permission. Commentators
  call yt-dlp downloads of CC videos a Terms breach, though not infringement [unverified].
  Source: [Legally Explained](https://legallyexplained.com/is-it-legal-to-download-youtube-videos/) [vendor].
- The usual enforcement is platform-side: throttling, IP blocks, account restriction.
  Source: [Tunelio](https://tunelio.dev/blog/is-yt-dlp-safe/) [vendor].
- **Recommendation:** never use yt-dlp in this pipeline. Get footage from the original publisher
  (NASA, LoC, NARA, archive.org, Wikimedia Commons), whose sites allow direct downloads.

---

## 3. Options compared

| Option | Legal / Terms risk | Risk to main channel's future monetization | Reach potential (data) | Effort | Cost | Automatable (script renders 1080x1920 with burned captions)? |
|---|---|---|---|---|---|---|
| (a) Paid clipping marketplace, on main channel | Low on copyright (footage authorized). Needs ad disclosure. Polymarket lawsuit shows reputational risk. | **High.** Reused-content policy applies even with permission. October 2026 downranking of reupload channels. Off-topic brand clips. | Unknown per clip. Many clippers get no views (NPR). Most campaigns pay on TikTok, which is blocked in India. | Medium to high: briefs, approvals, per-campaign accounts | Free to join. A fee of about 10% reported. | Partly. Rendering yes; picking campaigns and submitting links is manual. |
| (a') Same, on a separate account as side income | As above. India payout for Content Rewards unconfirmed. | Low if fully separate. Strikes can reach linked channels (copyright-strike help page). | As above. Pays about $0.20 to $6 per 1,000 views. | Medium to high | As above | Partly |
| (b) Unpermitted clips of others | **High.** Fair use is unlikely for commercial, substitutive clips. Strikes. | **Very high.** Channel-wide demonetization, reduced reach, termination after 3 strikes. | Shrinking: YouTube, Meta and TikTok all now demote reuploads. | Low | Free | Technically yes, but it needs yt-dlp, which breaches the Terms. |
| (c) YouTube Remix "Cut" | None (licensed by YouTube). | Low, if the rest of the Short is original. | No data. 1 to 5 seconds only. | Manual, mobile app | Free | **No** |
| (d) Public-domain and CC footage as B-roll in original explainers | Low with per-asset checks. Watch for music in NASA and SVS videos, logos, endorsement, and donated NARA films. | **Low**, provided the script, voice, captions and analysis carry the video and footage is a supporting share. | No data found. Real footage is plausibly a retention win for space and history. **Test it.** | Medium (one build) | Free footage. **Saves Higgsfield credits** [repo: motion is 8 of about 12 credits in the reach tier]. | **Yes**: NASA API plus archive downloads, then the existing assembler. |
| (e) Own long-form to Shorts, and Shorts to long-form | None | Low. A plain Shorts-stitch compilation carries a repetitive-content risk. | Related-link conversion is often low (vendor data). Spotter reports a 20% lift [vendor]. | Medium | Low | Yes, later |

---

## 4. Recommendation for Worth Knowing

**Do this: option (d), on the main channel**

- Clip public-domain archival footage into the channel's own original explainers as B-roll. This is
  not a separate "clip channel".
- It fits three niches:
  - science and space: NASA, SVS, and ESA where CC BY;
  - history stories: NARA, Library of Congress, Prelinger;
  - how it's made: Prelinger industrial and educational films.
- It barely fits the money, AI-tools and psychology niches. Prelinger has some old consumer and
  finance films, but keep AI visuals there.

**Don't do this**

- Unpermitted clipping of others: on no channel.
- Marketplace clipping on Worth Knowing.
  - If the owner wants side income, it is a separate, manual experiment under a different account.
  - It must never be cross-posted, and it does not grow this channel.
  - The main paying surface, TikTok, is blocked in India.
  - Content Rewards payouts to India are unconfirmed.

**Later**

- When long-form starts, add related-video links and narrated monthly "deep dives" per niche.

### What the implementation needs

**1. Configuration first: a new `config/footage.yaml`**

The project's rule is that behavior lives in `config/`, so the rules go there before any code.

- **Allowed sources, each with its rule:**
  - NASA Image and Video Library: reject items whose description mentions copyright, music or
    "courtesy of" a non-NASA party.
  - NASA SVS: reject or mute pages that carry a music notice.
  - Library of Congress National Screening Room: only items whose record has no restrictions and
    a download.
  - NARA: only federal-agency productions; no Donated Materials; nothing whose use-restriction
    field is not "unrestricted".
  - Internet Archive Prelinger: only items whose license field is the Public Domain Mark or CC0.
  - Wikimedia Commons: only PD, CC0 or CC BY.
- **Blocked sources:** YouTube downloads of any kind; CC BY-NC, BY-ND and BY-SA (unless the
  owner accepts ShareAlike for the whole Short); stock sites whose terms ban "compilations".
- **Niche mapping:** which niches may use footage, and a cap on the share of runtime that is
  footage. Suggested house rule: at most about half. This is our rule, not YouTube's; YouTube sets
  no percentage.

**2. A new `pipeline/footage.py` module**

- **Search:**
  - NASA: `https://images-api.nasa.gov/search?q=<keywords>&media_type=video`, then
    `/asset/{nasa_id}` for the MP4 files.
  - archive.org advanced search on `collection:prelinger`. The exact license-field syntax is
    unverified.
  - The loc.gov JSON API. The exact query syntax is unverified.
- **Pick** an MP4 under about 50 MB, so it also works with Higgsfield `media_import_url`.
- **Write a rights ledger** under `data/footage/`, committed with each run. For each asset record:
  source URL, ID, the rights text as found, the license, the credit line, and the date checked.
- **Plan a segment:** a start offset and length for each block, matched to the script beat.

**3. The render plan**

- A block can carry `footage: {url, start, seconds, credit, mute: true}` in place of a Higgsfield
  `motion_url`.
- This removes about 2 credits per replaced motion block in the reach tier [repo].

**4. Changes to `tools/assemble.py`**

- In `motion_segment`, add `-ss start`.
- Add a mute flag that keeps footage audio out of `motion_audio`. **Always strip source audio**:
  NASA and SVS videos may carry licensed music, and a claim on a Short over 60 seconds blocks it
  worldwide.
- Add a "pad" mode: scale to width over a blurred, scaled copy, for 4:3 and 16:9 footage where a
  centre crop would cut the subject.
- Optional: a small corner tag reading "Archival: NASA" (or LoC, NARA) on footage shots, and keep
  AI illustrations visually distinct, so AI imagery is never passed off as real archival footage.
  AI labels stay on.
- Per CLAUDE.md: run `python -m pytest`, commit and push `assemble.py`, then update
  `render.assembler_url` and `render.assembler_sha256` in `config/production.yaml`.

**5. Script rules (for the script writer)**

- Footage illustrates the narration. It is never the subject.
- Narration must add facts, context and analysis, not "describe what's on screen" (the Ritchie
  test, which matches Meta's March 2026 rule).
- Vary which beats use footage, so videos do not feel templated (inauthentic-content
  "repetitive" category).
- Never imply endorsement ("NASA explains…", "official"). No NASA insignia or logotype in
  thumbnails or titles.

**6. Attribution text for the YouTube description, Reels and Facebook captions**

Credit is required for CC BY and requested for public domain. Add the sources to the existing
"Sources" block:

- NASA: `Footage: NASA (images.nasa.gov, ID <nasa_id>) – public domain. NASA does not endorse this channel.`
- SVS: `Visualization: NASA's Scientific Visualization Studio (<page URL>) – public domain.`
- JPL: `Courtesy NASA/JPL-Caltech.`
- Library of Congress: `Film: "<title>", Library of Congress, National Screening Room (<URL>) – no known restrictions.`
- NARA: `Film: "<title>", U.S. National Archives, NAID <id> (<URL>) – public domain (U.S. government work).`
- Prelinger: `Archival footage supplied by Internet Archive (archive.org), Prelinger Archives: "<title>" (<URL>) – Public Domain Mark.`
- CC BY (title, author, source, license, plus a note of changes): `"<title>" by <author> (<URL>), CC BY 4.0, cropped, trimmed and captioned.`

**7. Claims handling**

- After upload, check YouTube Studio's copyright tab for claims on footage videos.
- Dispute false claims on public-domain footage by citing the source URL and its public-domain
  status. Public-domain footage is ineligible for Content ID.
- For footage-heavy videos, staying at 60 seconds or under avoids the worldwide block while a
  dispute is pending. This trades off against the >60-second preference in CLAUDE.md for TikTok,
  which is not a current target.

**8. Measure it**

- Tag runs with `footage: true` and compare views per hour and average view duration against
  AI-only videos in the same niche (`pipeline insights`).
- No outside reach data exists for this format, so the channel's own results decide whether to
  extend it.

---

## 5. Policy context that affects timing

**YouTube Partner Program entry, as reported for 2026-08-10**

Sources: [Tubefilter](https://www.tubefilter.com/2026/08/10/youtube-partner-program-ad-eligibility-requirements-shorts/),
[PPC Land](https://ppc.land/new-youtube-creators-face-8-000-hour-bar-for-ad-revenue-from-february-2027/),
[AIN](https://en.ain.ua/2026/08/11/youtube-changes-monetization-rules-shorts-will-have-a-10-million-views-threshold/).

| | Requirement |
|---|---|
| Now | 1,000 subscribers, plus 4,000 watch hours in 365 days **or** 10M Shorts views in 90 days |
| New applicants from 2027-02-01 | 1,000 subscribers, plus 8,000 hours **or** 20M Shorts views in 90 days |
| Shorts revenue sharing from 2027-02-01 | Needs 10M qualified Shorts views per rolling 90 days |

- The lower fan-funding tier (500 subscribers plus 3,000 hours or 3M Shorts views) is unchanged.
- **Implication:** if the channel can reach 1,000 subscribers and 10M Shorts views in 90 days
  before 2027-02-01, applying before that date avoids the doubled bar. Reach-first strategy
  matters more than any clipping side channel.

**Every platform now demotes reuploads**

- YouTube Shorts recommendations (2026-10-01).
- Meta / Facebook (July 2025).
- Instagram recommendations.
- TikTok Creator Rewards excludes reposted clips. Source:
  [Nuelink](https://blog.nuelink.com/tiktok-creator-rewards-program/) [vendor].
- Original narration over properly licensed footage is the only "clipping" that holds up on all of
  them.
