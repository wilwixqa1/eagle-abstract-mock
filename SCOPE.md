# eagleabstract.com Rebuild — Project Scope

**Prepared:** July 16, 2026 · **For:** Eagle Abstract Corp. (current site: WordPress/Divi, ~$50/mo)
**Goal:** Improve the site substantially across UX, SEO, and trust — without disrupting the existing order flow that current clients rely on.

---

## Tier 1 — Fix What's Broken (existing site, days of effort)

Low-risk fixes done directly on the current WordPress site. No redesign required.

1. **Order page URL** — rename `/order-new-gravity-form/` to `/order/` with a 301 redirect; reconcile the homepage link (`/order/`) vs nav link mismatch.
2. **Anti-spam field** — replace the broken "enter a number from 9 to 9" captcha with reCAPTCHA/Turnstile.
3. **Typos & copy** — "comfirmation" on the order page; audit all pages.
4. **Email mismatch** — Resources page shows `customersupport@` but links to `customerservice@`. Confirm the real inbox and fix.
5. **Mobile accessibility** — remove `user-scalable=0` from the viewport tag (blocks pinch-zoom; Google flags it; ADA exposure).
6. **Dead/duplicate links** — clean empty anchor tags on Resources; remove `?et_fb=1` from the Privacy Policy footer link.
7. **Basic local SEO** — add "Long Island / Nassau & Suffolk / New York" to title tags, meta descriptions, and homepage copy. Add LocalBusiness (InsuranceAgency) schema.
8. **Google Business Profile** — claim/verify, add hours, photos, and start collecting attorney reviews. (Highest-ROI item in the whole project.)
9. **Publish NAP** — street address appears nowhere on the site. Add full name/address/phone to the footer of every page (required for local SEO and basic trust).
10. **License line** — display the NY DFS title agent license number in the footer.
11. **Analytics** — install GA4 + Search Console so all later work is measurable.

**Decision point:** items 1–6 can be done on the $50/mo setup immediately, even if the redesign proceeds.

---

## Tier 2 — Rebuild the Money Pages (the redesign, weeks of effort)

New site (this repo is the start), deployed on Railway. Keep WordPress live until parity, then cut DNS over.

1. **Homepage** — ✅ mocked in this repo (`static/index.html`). Brand-crimson design system: Marcellus display / Public Sans body / IBM Plex Mono utility; recording-stamp signature element; SEO title/meta/schema baked in.
2. **Multi-step order form** — the flagship improvement. Steps: transaction type → property → parties → review & submit. Conditional logic (co-op fields only for co-op searches; lender block optional), inline validation, progress indicator, email confirmation to client + intake email to Eagle. Backend: FastAPI + email relay (or webhook into their existing intake).
3. **Searchable forms library** — the 100+ PDFs/DOCs with a search box, category filters, human-readable names + one-line descriptions, keeping the legal disclaimer.
4. **Remaining pages** — About/team (bios exist), Recording Fees & Services, Contact (with address + map), Privacy.
5. **Quality floor** — responsive with a real mobile nav (hamburger — currently omitted in the mock), keyboard focus states, alt text everywhere, HTTPS, sub-1s loads (static pages, no page builder).
6. **Redirect map** — 301s from every old WordPress URL to its new equivalent so existing SEO equity and bookmarked links survive.

**Migration safety:** old site stays untouched at $50/mo until the new one is proven. Zero downtime risk.

---

## Tier 3 — Growth (ongoing after launch)

1. **Service pages** — one page per search type (purchase, refi, commercial, co-op, foreclosure, CEMA/recordings) targeting "X + Long Island/NY" queries.
2. **Bulletins/blog** — short monthly NY real-estate law updates (FinCEN, transfer tax, TP-584 changes — competitors like Abstracts Inc. do this and it drives their mailing list). Doubles as the newsletter content the contact form already promises.
3. **Testimonials page** — collect from attorney clients; feature on homepage rotation.
4. **Closing scheduler** — "Schedule a closing" request form (competitor parity).
5. **Order status** — evaluate integration with their title production software (Qualia/ResWare/SoftPro) for client-facing status, or start with simple email status updates.
6. **Email list** — wire the newsletter opt-in to an actual list (Mailchimp/Buttondown); send the bulletins.
7. **Local SEO buildout** — county landing pages if warranted, citation cleanup, review generation cadence.

---

## This Repo (the mock)

- FastAPI static server: `app/main.py`, healthcheck at `/healthz`
- Railway-ready: `Procfile`, `railway.json` (Nixpacks, healthcheck configured)
- Homepage: `static/index.html` (self-contained CSS), brand assets in `static/img/`
- Deploy pattern: push to GitHub `main` → Railway auto-deploys (same as summit mock / Movement Miles)

**Open items for Will/Dad:**
- Street address + DFS license number (placeholders marked `TBD` in footer)
- Confirm the correct support email
- Headline sign-off: current mock uses "Clearing New York titles since 1979."
- Whether the live domain cutover is in scope or the mock stays a preview
