"""
AgriMarket — Streamlit prototype
=================================

A two-sided marketplace connecting farmers with verified buyers.
Farmers list crops (with photos); buyers list what they buy and at
what price; both sides can browse, search, and leave reviews.

Run with:
    streamlit run app.py

First run creates agrimarket.db (SQLite) and an uploads/ folder in
the same directory automatically — nothing else to set up.
"""

import os
import uuid

import streamlit as st

import db
from i18n import LANGUAGES, t

# ------------------------------------------------------------------ setup --
st.set_page_config(page_title="AgriMarket", page_icon="🌾", layout="centered")
db.init_db()

COLORS = {
    "leaf": "#2E7D32",
    "leaf_dark": "#1B5E20",
    "bg": "#FFFFFF",
    "card_alt": "#F2F7F1",
    "border": "#DCE8DC",
    "text": "#1B2B1D",
    "muted": "#5B6B5D",
}

CUSTOM_CSS = f"""
<style>
.stApp {{
    background-color: {COLORS['bg']};
}}
.block-container {{
    max-width: 480px;
    padding-top: 1.2rem;
    padding-bottom: 5.5rem; /* room for bottom nav */
}}
.am-card {{
    background: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(27,43,29,0.06);
}}
.am-card-alt {{
    background: {COLORS['card_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 10px;
}}
.am-title {{
    color: {COLORS['leaf_dark']};
    font-weight: 800;
    font-size: 1.5rem;
    margin-bottom: 0;
}}
.am-subtitle {{
    color: {COLORS['muted']};
    font-size: 0.9rem;
    margin-top: 0;
}}
.am-price {{
    color: {COLORS['leaf']};
    font-weight: 800;
    font-size: 1.3rem;
}}
.am-muted {{
    color: {COLORS['muted']};
    font-size: 0.85rem;
}}
.am-pill {{
    display: inline-block;
    background: {COLORS['card_alt']};
    color: {COLORS['leaf_dark']};
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 0.78rem;
    margin-right: 6px;
    margin-bottom: 6px;
}}
.am-navbar button {{
    width: 100%;
}}
div[data-testid="column"] button {{
    border-radius: 12px !important;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------- session state ----
defaults = {
    "lang": "en",
    "user": None,
    "page": "home",
    "return_page": "home",
    "viewing": None,       # {"id": int} — profile currently being viewed
    "auth_mode": "login",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def lang():
    return st.session_state["lang"]


def goto(page):
    st.session_state["page"] = page
    st.session_state["viewing"] = None


def view_profile(user_id, from_page):
    st.session_state["return_page"] = from_page
    st.session_state["viewing"] = {"id": user_id}
    st.session_state["page"] = "view_profile"


# ------------------------------------------------------------- top bar -----
def render_top_bar():
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"<p class='am-title'>🌾 {t('app_name', lang())}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='am-subtitle'>{t('tagline', lang())}</p>", unsafe_allow_html=True)
    with col2:
        codes = [c for c, _ in LANGUAGES]
        names = [n for _, n in LANGUAGES]
        idx = codes.index(st.session_state["lang"]) if st.session_state["lang"] in codes else 0
        choice = st.selectbox(
            "🌐", names, index=idx, key="lang_select", label_visibility="collapsed"
        )
        new_code = codes[names.index(choice)]
        if new_code != st.session_state["lang"]:
            st.session_state["lang"] = new_code
            if st.session_state["user"]:
                db.update_user(st.session_state["user"]["id"], language=new_code)
            st.rerun()


# --------------------------------------------------------------- auth ------
def auth_page():
    render_top_bar()
    st.markdown("---")
    st.markdown(f"### {t('welcome', lang())}")
    st.caption(t("get_started", lang()))

    role = st.radio(t("role", lang()), [t("farmer", lang()), t("buyer", lang())], horizontal=True)
    name = st.text_input(t("name", lang()))
    phone = st.text_input(t("phone", lang()), max_chars=15)
    location = st.text_input(t("location_label", lang()))

    if st.button(t("continue_btn", lang()), type="primary", use_container_width=True):
        phone_clean = phone.strip()
        if not phone_clean or not name.strip():
            st.warning(f"{t('name', lang())} / {t('phone', lang())}")
            return
        existing = db.get_user_by_phone(phone_clean)
        if existing:
            st.session_state["user"] = existing
            st.session_state["lang"] = existing.get("language", "en") or "en"
        else:
            role_code = "farmer" if role == t("farmer", lang()) else "buyer"
            uid = db.create_user(role_code, name.strip(), phone_clean, location.strip(), lang())
            st.session_state["user"] = db.get_user(uid)
        st.rerun()

    st.caption(
        "Demo login: enter your phone number. If it's new, we create your "
        "account with the role you picked above. No password needed for this prototype."
    )


# --------------------------------------------------------- bottom nav ------
def render_bottom_nav():
    st.markdown("---")
    tabs = [
        ("home", "🏠", t("home", lang())),
        ("location", "📍", t("location", lang())),
        ("buyers", "🤝", t("buyer_details", lang())),
        ("profile", "👤", t("profile", lang())),
    ]
    cols = st.columns(4)
    current = st.session_state["page"]
    for col, (key, icon, label) in zip(cols, tabs):
        with col:
            active = current == key or (current == "view_profile" and st.session_state["return_page"] == key)
            style = "primary" if active else "secondary"
            if st.button(f"{icon}\n{label}", key=f"nav_{key}", use_container_width=True, type=style):
                goto(key)
                st.rerun()


# ----------------------------------------------------------- stars UI ------
def stars_str(rating):
    if rating is None:
        return "—"
    full = round(rating)
    return "★" * full + "☆" * (5 - full) + f"  ({rating})"


# ---------------------------------------------------------- crop card ------
def render_crop_card(crop):
    st.markdown("<div class='am-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        if crop.get("photo_path") and os.path.exists(crop["photo_path"]):
            st.image(crop["photo_path"], use_container_width=True)
        else:
            st.markdown(
                "<div style='background:#F2F7F1;border-radius:10px;height:90px;"
                "display:flex;align-items:center;justify-content:center;font-size:2rem;'>🌾</div>",
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown(f"**{crop['crop_name']}**")
        st.markdown(
            f"<span class='am-price'>₹{crop['expected_price']:.0f}</span> "
            f"<span class='am-muted'>{t('per', lang())} {crop.get('unit','quintal')}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span class='am-muted'>📍 {crop.get('location') or '—'} · "
            f"{crop.get('quantity') or '—'} {crop.get('unit','')}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span class='am-muted'>{t('sold_by', lang())}: {crop['farmer_name']}</span>",
            unsafe_allow_html=True,
        )
        if st.button(t("view_farmer", lang()), key=f"view_farmer_{crop['id']}"):
            view_profile(crop["farmer_id"], st.session_state["page"])
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------- buyer card ------
def render_buyer_card(buyer):
    st.markdown("<div class='am-card'>", unsafe_allow_html=True)
    st.markdown(f"**{buyer['name']}**  🤝")
    st.markdown(
        f"<span class='am-muted'>📍 {buyer.get('location') or '—'} · "
        f"{stars_str(buyer.get('avg_rating'))}</span>",
        unsafe_allow_html=True,
    )
    offers = buyer.get("offers", [])
    if offers:
        pills = "".join(
            f"<span class='am-pill'>{o['crop_name']} · ₹{o['offered_price']:.0f}/{o.get('unit','quintal')}</span>"
            for o in offers
        )
        st.markdown(pills, unsafe_allow_html=True)
    if st.button(t("view_buyer", lang()), key=f"view_buyer_{buyer['id']}"):
        view_profile(buyer["id"], st.session_state["page"])
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------ HOME ---------
def home_page():
    render_top_bar()
    st.markdown(f"#### {t('home', lang())}")

    search = st.text_input(t("search_crop_placeholder", lang()), key="home_search")

    suggested = db.get_distinct_crop_names()
    if suggested and not search:
        st.markdown(f"<span class='am-muted'>{t('suggested_crops', lang())}:</span>", unsafe_allow_html=True)
        chip_cols = st.columns(min(len(suggested), 5))
        for i, crop_name in enumerate(suggested[:5]):
            with chip_cols[i]:
                if st.button(crop_name, key=f"chip_{crop_name}", use_container_width=True):
                    st.session_state["home_search"] = crop_name
                    st.rerun()

    user = st.session_state["user"]
    if user["role"] == "farmer":
        with st.expander(f"➕ {t('add_crop', lang())}"):
            with st.form("add_crop_form", clear_on_submit=True):
                cname = st.text_input(t("crop_name", lang()))
                qty = st.text_input(t("quantity", lang()))
                unit = st.selectbox(t("unit", lang()), ["quintal", "kg", "ton"])
                price = st.number_input(t("expected_price", lang()), min_value=0.0, step=10.0)
                cloc = st.text_input(t("location_label", lang()), value=user.get("location") or "")
                photo = st.file_uploader(t("upload_photo", lang()), type=["png", "jpg", "jpeg"])
                submitted = st.form_submit_button(t("submit", lang()), type="primary")
                if submitted and cname.strip():
                    photo_path = None
                    if photo is not None:
                        ext = os.path.splitext(photo.name)[1] or ".jpg"
                        fname = f"{uuid.uuid4().hex}{ext}"
                        photo_path = os.path.join(db.UPLOAD_DIR, fname)
                        with open(photo_path, "wb") as f:
                            f.write(photo.getbuffer())
                    db.add_crop(user["id"], cname.strip(), qty, unit, price, cloc, photo_path)
                    st.success(t("submit", lang()) + " ✅")
                    st.rerun()

    crops = db.get_crops(search=search or None)
    st.markdown("---")
    if not crops:
        st.info(t("no_crops_found", lang()))
    else:
        for crop in crops:
            render_crop_card(crop)


# --------------------------------------------------------- LOCATION --------
def location_page():
    render_top_bar()
    st.markdown(f"#### {t('location', lang())}")

    loc_q = st.text_input(t("search_location_placeholder", lang()), key="loc_search_location")
    crop_q = st.text_input(t("search_crop_placeholder", lang()), key="loc_search_crop")

    st.markdown(f"##### {t('crops_near_you', lang())}")
    crops = db.get_crops(search=crop_q or None, location=loc_q or None)
    if not crops:
        st.info(t("no_crops_found", lang()))
    else:
        for crop in crops:
            render_crop_card(crop)

    st.markdown("---")
    st.markdown(f"##### {t('buyers_near_you', lang())}")
    buyers = db.get_buyers(search_location=loc_q or None, search_crop=crop_q or None)
    if not buyers:
        st.info(t("no_buyers_found", lang()))
    else:
        for b in buyers:
            render_buyer_card(b)


# ------------------------------------------------------- BUYER DETAILS -----
def buyers_page():
    render_top_bar()
    st.markdown(f"#### {t('buyer_details', lang())}")

    loc_q = st.text_input(t("search_location_placeholder", lang()), key="buyers_search_location")
    crop_q = st.text_input(t("search_crop_placeholder", lang()), key="buyers_search_crop")

    buyers = db.get_buyers(search_location=loc_q or None, search_crop=crop_q or None)
    if not buyers:
        st.info(t("no_buyers_found", lang()))
    else:
        for b in buyers:
            render_buyer_card(b)


# ------------------------------------------------------------ PROFILE ------
def profile_page():
    render_top_bar()
    user = st.session_state["user"]
    st.markdown(f"#### {t('profile', lang())}")

    avg, cnt = db.get_avg_rating(user["id"])
    st.markdown("<div class='am-card'>", unsafe_allow_html=True)
    role_label = t("farmer", lang()) if user["role"] == "farmer" else t("buyer", lang())
    st.markdown(f"### {user['name']}  <span class='am-muted'>· {role_label}</span>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='am-muted'>📍 {user.get('location') or '—'} &nbsp;|&nbsp; 📞 {user['phone']}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<span class='am-muted'>{t('avg_rating', lang())}: {stars_str(avg)} ({cnt})</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander(f"✏️ {t('edit_profile', lang())}"):
        new_name = st.text_input(t("name", lang()), value=user["name"], key="edit_name")
        new_loc = st.text_input(t("location_label", lang()), value=user.get("location") or "", key="edit_loc")
        if st.button(t("save", lang()), key="save_profile"):
            db.update_user(user["id"], name=new_name.strip(), location=new_loc.strip())
            st.session_state["user"] = db.get_user(user["id"])
            st.success(t("save", lang()) + " ✅")
            st.rerun()

    if user["role"] == "farmer":
        st.markdown(f"##### {t('my_crops', lang())}")
        crops = db.get_crops_by_farmer(user["id"])
        if not crops:
            st.info(t("no_crops_found", lang()))
        else:
            for crop in crops:
                st.markdown("<div class='am-card-alt'>", unsafe_allow_html=True)
                cc1, cc2 = st.columns([1, 2])
                with cc1:
                    if crop.get("photo_path") and os.path.exists(crop["photo_path"]):
                        st.image(crop["photo_path"], use_container_width=True)
                with cc2:
                    st.markdown(f"**{crop['crop_name']}** — ₹{crop['expected_price']:.0f}/{crop.get('unit','quintal')}")
                    st.markdown(f"<span class='am-muted'>{crop.get('quantity','')} {crop.get('unit','')} · 📍 {crop.get('location','')}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"##### {t('my_offers', lang())}")
        with st.expander(f"➕ {t('add_offer', lang())}"):
            with st.form("add_offer_form", clear_on_submit=True):
                cname = st.text_input(t("crop_name", lang()))
                unit = st.selectbox(t("unit", lang()), ["quintal", "kg", "ton"])
                price = st.number_input(t("price_offered", lang()), min_value=0.0, step=10.0)
                submitted = st.form_submit_button(t("submit", lang()), type="primary")
                if submitted and cname.strip():
                    db.add_buyer_offer(user["id"], cname.strip(), price, unit)
                    st.rerun()
        offers = db.get_buyer_offers(user["id"])
        if not offers:
            st.info(t("no_crops_found", lang()))
        else:
            pills = "".join(
                f"<span class='am-pill'>{o['crop_name']} · ₹{o['offered_price']:.0f}/{o.get('unit','quintal')}</span>"
                for o in offers
            )
            st.markdown(pills, unsafe_allow_html=True)

    st.markdown(f"##### {t('reviews', lang())}")
    reviews = db.get_reviews(user["id"])
    if not reviews:
        st.info(t("no_reviews_yet", lang()))
    else:
        for r in reviews:
            st.markdown(
                f"<div class='am-card-alt'>{stars_str(r['rating'])}<br>"
                f"<b>{r['reviewer_name']}</b><br>"
                f"<span class='am-muted'>{r['comment'] or ''}</span></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    if st.button(t("logout", lang()), use_container_width=True):
        st.session_state["user"] = None
        goto("home")
        st.rerun()


# -------------------------------------------------------- VIEW PROFILE -----
def view_profile_page():
    render_top_bar()
    viewing_id = st.session_state["viewing"]["id"]
    target = db.get_user(viewing_id)
    current_user = st.session_state["user"]

    if st.button(f"← {t('back', lang())}"):
        goto(st.session_state["return_page"])
        st.rerun()
        return

    if not target:
        st.warning("Not found.")
        return

    avg, cnt = db.get_avg_rating(target["id"])
    st.markdown("<div class='am-card'>", unsafe_allow_html=True)
    role_label = t("farmer", lang()) if target["role"] == "farmer" else t("buyer", lang())
    st.markdown(f"### {target['name']}  <span class='am-muted'>· {role_label}</span>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='am-muted'>📍 {target.get('location') or '—'}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<span class='am-muted'>{t('avg_rating', lang())}: {stars_str(avg)} ({cnt})</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.link_button(f"📞 {t('call', lang())} {target['phone']}", f"tel:{target['phone']}", use_container_width=True)

    if target["role"] == "farmer":
        st.markdown(f"##### {t('my_crops', lang())} / {t('photos', lang())}")
        crops = db.get_crops_by_farmer(target["id"])
        if not crops:
            st.info(t("no_crops_found", lang()))
        else:
            for crop in crops:
                st.markdown("<div class='am-card-alt'>", unsafe_allow_html=True)
                cc1, cc2 = st.columns([1, 2])
                with cc1:
                    if crop.get("photo_path") and os.path.exists(crop["photo_path"]):
                        st.image(crop["photo_path"], use_container_width=True)
                with cc2:
                    st.markdown(f"**{crop['crop_name']}** — ₹{crop['expected_price']:.0f}/{crop.get('unit','quintal')}")
                    st.markdown(f"<span class='am-muted'>📍 {crop.get('location','')}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"##### {t('crops_i_buy', lang())}")
        offers = db.get_buyer_offers(target["id"])
        if not offers:
            st.info(t("no_crops_found", lang()))
        else:
            pills = "".join(
                f"<span class='am-pill'>{o['crop_name']} · ₹{o['offered_price']:.0f}/{o.get('unit','quintal')}</span>"
                for o in offers
            )
            st.markdown(pills, unsafe_allow_html=True)

    st.markdown(f"##### {t('reviews', lang())}")
    reviews = db.get_reviews(target["id"])
    if not reviews:
        st.info(t("no_reviews_yet", lang()))
    else:
        for r in reviews:
            st.markdown(
                f"<div class='am-card-alt'>{stars_str(r['rating'])}<br>"
                f"<b>{r['reviewer_name']}</b><br>"
                f"<span class='am-muted'>{r['comment'] or ''}</span></div>",
                unsafe_allow_html=True,
            )

    if current_user and current_user["id"] != target["id"]:
        with st.expander(f"⭐ {t('write_review', lang())}"):
            rating = st.slider(t("rating", lang()), 1, 5, 5)
            comment = st.text_area(t("comment", lang()))
            if st.button(t("submit_review", lang()), key="submit_review_btn"):
                db.add_review(target["id"], current_user["id"], rating, comment.strip())
                st.success(t("submit_review", lang()) + " ✅")
                st.rerun()


# --------------------------------------------------------------- main ------
def main():
    if st.session_state["user"] is None:
        auth_page()
        return

    page = st.session_state["page"]
    if page == "home":
        home_page()
    elif page == "location":
        location_page()
    elif page == "buyers":
        buyers_page()
    elif page == "profile":
        profile_page()
    elif page == "view_profile":
        view_profile_page()
    else:
        home_page()

    render_bottom_nav()


if __name__ == "__main__":
    main()
