"""
seed_data.py — loads your real Madurai crop/buyer data into AgriMarket's
database so the demo isn't empty.

Run this ONCE before your demo, from inside the AgriMarket_App folder:

    python3 seed_data.py

It wipes any existing agrimarket.db and rebuilds it from scratch, so
it's safe to re-run if you want a clean slate.

What it creates:
- One farmer "group" account per market town in the Prices sheet
  (there are no individual farmer names in that sheet, only markets —
  so each market becomes a farmer account, and its listed crops become
  that account's crop listings).
- One buyer account per row in the Buyers sheet, with their real name,
  location, phone, and the crop they buy — plus a buying offer priced
  from the matching (or closest available) market price.
- One seed review per buyer, carrying over their original rating from
  the spreadsheet, so the Profile/Buyer Details screens show real
  numbers instead of "no reviews yet". The reviewer of record is a
  generic "Seed Data" farmer account created for this purpose — that's
  disclosed in the review comment, not hidden.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

# Wipe for a clean, deterministic seed
if os.path.exists(db.DB_PATH):
    os.remove(db.DB_PATH)
db.init_db()

# ---------------------------------------------------------------- data ----
# From Farmer_details.xlsx — PRICES sheet (crop, market, price per quintal)
PRICES = [
    ("Tomato", "Thirumangalam", 29.0),
    ("Tomato", "Usilampatti", 29.0),
    ("Tomato", "Anaiyur", 29.0),
    ("Tomato", "Anna Nagar", 28.0),
    ("Tomato", "Chokkkikulam", 28.0),
    ("Tomato", "Melur", 29.0),
    ("Tomato", "Palanganatham", 29.0),
    ("Onion", "Palanganatham", 62.5),
    ("Onion", "Thirumangalam", 62.5),
    ("Onion", "Usilampatti", 62.5),
    ("Onion", "Melur", 19.0),
    ("Potato", "Anna Nagar", 72.0),
    ("Potato", "Anaiyur", 58.0),
    ("Potato", "Palanganatham", 58.0),
]

# From Farmer_details.xlsx — BUYERS NAME sheet (name, location, phone, crop, rating)
# NOTE: "Pottato" in the source sheet was corrected to "Potato" here — it's an
# obvious typo, and left as-is it silently broke price-matching against the
# Prices sheet (which spells it correctly), leaving several buyers showing
# a ₹0 offered price. Preserved everything else, including the short phone
# number, exactly as given.
BUYERS = [
    ("BALA", "Thirumangalam", "9471234567", "Tomato", 4.5),
    ("KRISHNA", "Usilampatti", "9087654321", "Potato", 4.4),
    ("SIVAKUMAR", "Anaiyur", "9076543219", "Onion", 4.3),
    ("AJAY KUMAR", "Anna Nagar", "9876587654", "Onion", 4.6),
    ("RAKESH KANNAN", "Chokkikulam", "9543212345", "Potato", 4.7),
    ("AKASH", "Melur", "9432165432", "Potato", 4.8),
    ("KANNAN", "Palanganatham", "9087654321", "Tomato", 4.5),
    ("JEYA KUMAR", "Palanganatham", "9765873456", "Onion", 4.4),
    ("REVENTH", "Thirumangalam", "9042850007", "Tomato", 4.6),
    ("ABDUL KAREEM", "Usilampatti", "9842519573", "Tomato", 4.8),
    ("BRIJESH", "Melur", "9500619573", "Potato", 4.3),
    ("NITHISH", "Anna Nagar", "9362519573", "Onion", 4.6),
    ("SENTHIL", "Anaiyur", "8362519573", "Tomato", 4.6),
    ("BALAJI", "Palanganatham", "767119573", "Onion", 4.5),
]

# ---------------------------------------------------------- seed farmers --
markets = sorted({m for _, m, _ in PRICES})
farmer_id_by_market = {}
for i, market in enumerate(markets):
    phone = f"90000{i:05d}"  # synthetic, won't collide with real buyer numbers
    fid = db.create_user(
        role="farmer",
        name=f"{market} Farmers",
        phone=phone,
        location=market,
        language="en",
    )
    farmer_id_by_market[market] = fid
print(f"Created {len(farmer_id_by_market)} farmer accounts (one per market).")

for crop_name, market, price in PRICES:
    db.add_crop(
        farmer_id=farmer_id_by_market[market],
        crop_name=crop_name,
        quantity="",
        unit="quintal",
        expected_price=price,
        location=market,
        photo_path=None,
    )
print(f"Added {len(PRICES)} crop listings.")

# ------------------------------------------------ seed-data reviewer acct --
seed_reviewer_id = db.create_user(
    role="farmer",
    name="Seed Data",
    phone="9000099999",
    location="Madurai",
    language="en",
)

# ----------------------------------------------------------- seed buyers --
def matching_price(crop_name, location):
    """Find a price for this crop at this location; fall back to the
    average price for that crop across all markets if no exact match."""
    exact = [p for c, m, p in PRICES if c.lower() == crop_name.lower() and m == location]
    if exact:
        return exact[0]
    same_crop = [p for c, _, p in PRICES if c.lower() == crop_name.lower()]
    if same_crop:
        return round(sum(same_crop) / len(same_crop), 1)
    return 0.0


created_buyers = 0
seen_phones = set()
for name, location, phone, crop, rating in BUYERS:
    original_phone = phone
    while phone in seen_phones:
        # Source spreadsheet has a genuine duplicate phone number across
        # two different buyers. Since phone is the login ID here, we
        # nudge the duplicate's last digit for this demo seed only —
        # the real fix is correcting the actual number in your sheet.
        phone = phone[:-1] + str((int(phone[-1]) + 1) % 10)
    if phone != original_phone:
        print(
            f"  NOTE: '{name}' had duplicate phone {original_phone} "
            f"(already used by another buyer) — seeded as {phone} instead. "
            f"Fix the real number in your spreadsheet."
        )
    seen_phones.add(phone)

    bid = db.create_user(
        role="buyer",
        name=name.title(),
        phone=phone,
        location=location,
        language="en",
    )
    price = matching_price(crop, location)
    db.add_buyer_offer(bid, crop, price, unit="quintal")
    db.add_review(
        target_user_id=bid,
        reviewer_id=seed_reviewer_id,
        rating=rating,
        comment="Imported from initial ratings data.",
    )
    created_buyers += 1
print(f"Created {created_buyers} buyer accounts with offers and seed ratings.")

print("\nSeed complete. Run: streamlit run app.py")
print("Log in as any seeded account using its phone number to explore as that user,")
print("or sign up fresh with a new phone number to try the app as a brand-new user.")
