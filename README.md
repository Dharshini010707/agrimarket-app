# AgriMarket (Streamlit prototype)

A two-sided marketplace connecting **farmers** with **verified buyers**.
Farmers list crops with photos and an expected price; buyers list what
they buy and at what price. Both sides can search, view full profiles,
and leave star reviews. Supports **English, Hindi, Tamil, Telugu,
Kannada, and Malayalam**.

## Run it

```bash
cd AgriMarket_App
pip install -r requirements.txt
streamlit run app.py
```

It opens in your browser at `http://localhost:8501`. First run creates
`agrimarket.db` (SQLite) and an `uploads/` folder automatically — no
other setup needed.

## How it's organized

- `app.py` — the whole UI: login, the 4 screens (Home, Location, Buyer
  Details, Profile), and the "view someone else's profile" flow.
- `db.py` — all data access (SQLite). Tables: `users`, `crops`,
  `buyer_offers`, `reviews`.
- `i18n.py` — every UI string in all 6 languages, plus the `t()` lookup
  helper.
- `uploads/` — crop photos land here, named with a random ID.

## What's implemented

- **Sign in**: phone number only. New number → pick Farmer or Buyer,
  enter name/location, account is created. Existing number → logs
  straight in.
- **Home**: search crops by name, suggested-crop shortcuts, list of
  all crop listings with photo/price/quantity/location, farmers can
  add their own listing (with a photo) from here.
- **Location**: search by location (and optionally crop) across both
  crop listings and buyers.
- **Buyer Details**: search/browse buyers by location or crop, see
  what each buyer is offering and their rating.
- **Profile**: your own details, your crop listings or buying offers,
  reviews you've received, edit name/location, log out.
- **View profile**: tapping "View Farmer" / "View Buyer" anywhere
  opens that person's full profile — their listings/offers, reviews,
  a call button, and (if you're logged in as someone else) a form to
  leave a star rating + comment.
- **Language switcher** top-right on every screen, saved to your
  account.

## Known simplifications (worth knowing before a demo or before you build on this)

1. **Auth is phone-number-only**, no password/OTP. Fine for a judged
   demo; not something to ship as-is.
2. **Bottom nav** sits at the bottom of each page's content rather
   than pixel-pinned to the screen edge — true fixed positioning in
   Streamlit needs a fragile CSS hack, so I kept it simple and
   reliable instead.
3. **Translations** cover the full core UI in all 6 languages, but
   were done without a native-speaker review pass — get one before a
   public/final submission.
4. **No real photo storage service** — uploaded photos are saved to a
   local `uploads/` folder next to the app. Fine for a local demo;
   you'd want cloud storage (S3, Cloudinary, etc.) for a real deploy.
5. **Search is simple substring matching** (`LIKE %term%`), not fuzzy
   or typo-tolerant.

## Natural next steps

- Swap phone-only login for OTP-based auth (e.g. via an SMS API).
- Move uploads to cloud storage if you deploy this publicly.
- Add pagination once listings grow past a page or two.
- Get the 5 non-English translation sets checked by native speakers.
