import html
import json
import math
import streamlit as st
from azure_clients import get_blob_container
from analyzer import extract_text, analyze_language, match_score, save_to_history, load_history
from auth_store import create_user, verify_login

st.set_page_config(page_title="Resume Analyzer Pro", layout="wide")

# ---------------------------------------------------------------------------
# Theme tokens
# ---------------------------------------------------------------------------
LIGHT = dict(
    primary="#4F46E5", primary_dark="#4338CA",
    bg="#F5F5FA", card_bg="#FFFFFF", navbar_bg="#FFFFFF",
    text="#111827", muted="#6B7280", border="#E5E7EB",
    input_bg="#FFFFFF", input_text="#111827", input_border="#D1D5DB",
    badge_indigo_bg="#EEF2FF", badge_indigo_text="#4338CA",
    badge_mint_bg="#ECFDF5", badge_mint_text="#047857",
    badge_rose_bg="#FEF2F2", badge_rose_text="#B91C1C",
    badge_slate_bg="#F3F4F6", badge_slate_text="#374151",
    ring_track="#E5E7EB",
    entry_card_bg="#DBEAFE", hero_text="#4338CA",
)

DARK = dict(
    primary="#6366F1", primary_dark="#818CF8",
    bg="#0F1115", card_bg="#181B22", navbar_bg="#14161C",
    text="#F3F4F6", muted="#9CA3AF", border="#2A2E37",
    input_bg="#0F1115", input_text="#F3F4F6", input_border="#333844",
    badge_indigo_bg="rgba(99,102,241,0.18)", badge_indigo_text="#A5B4FC",
    badge_mint_bg="rgba(16,185,129,0.18)", badge_mint_text="#6EE7B7",
    badge_rose_bg="rgba(239,68,68,0.18)", badge_rose_text="#FCA5A5",
    badge_slate_bg="rgba(156,163,175,0.18)", badge_slate_text="#D1D5DB",
    ring_track="#2A2E37",
    entry_card_bg="#1E3A5F", hero_text="#A5B4FC",
)


def get_tokens() -> dict:
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    return DARK if st.session_state.theme == "dark" else LIGHT


def inject_css(t: dict):
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: {t['bg']} !important;
        color: {t['text']};
    }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    p, span, label, li, div, h1, h2, h3, h4, h5, h6 {{ color: {t['text']}; }}

    /* Buttons */
    .stButton > button, .stFormSubmitButton > button {{
        background: linear-gradient(135deg, {t['primary']}, {t['primary_dark']});
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 0.55rem 1.3rem;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.15);
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{ opacity: 0.9; color: white !important; }}
    .stButton > button:disabled {{ opacity: 0.45; }}
    .stButton > button:focus, .stFormSubmitButton > button:focus,
    .stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {{
        outline: 2px solid {t['primary']} !important;
        outline-offset: 1px;
        box-shadow: none !important;
        border-color: transparent !important;
    }}

    /* Tooltips are always dark-on-dark by Streamlit default -- force light text regardless of app theme */
    [data-testid="stTooltipContent"], [data-testid="stTooltipContent"] * {{
        background-color: #1F2937 !important;
        color: #F9FAFB !important;
    }}

    /* Cards -- only style wrappers that directly hold our own marker element,
       not every bordered wrapper Streamlit creates internally (e.g. for columns) */
    .card-marker {{ position: absolute; width: 0; height: 0; overflow: hidden; opacity: 0; pointer-events: none; }}
    .card-marker-entry {{ position: absolute; width: 0; height: 0; overflow: hidden; opacity: 0; pointer-events: none; }}
    .page-root-marker {{ position: absolute; width: 0; height: 0; overflow: hidden; opacity: 0; pointer-events: none; }}
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker) {{
        border-radius: 16px !important;
        border: 1px solid {t['border']} !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        background: {t['card_bg']} !important;
        padding: 0.75rem 1.5rem !important;
    }}

    /* Login / guest entry cards -- same card styling but with a light-blue background.
       Plain ":has(.card-marker-entry)" matches every ancestor wrapper up to the page
       root in some Streamlit versions (all vertical blocks share the same testid,
       border or not), which leaked the background onto the whole app. Excluding any
       wrapper that also contains .page-root-marker (present only outside any card,
       next to the hero heading) reliably rules out that outer wrapper without having
       to guess exact DOM depth or column testids. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.card-marker-entry):not(:has(.page-root-marker)) {{
        border-radius: 16px !important;
        border: 1px solid {t['border']} !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        background: {t['entry_card_bg']} !important;
        padding: 1.5rem !important;
    }}


    /* Text inputs / textareas -- explicit bg+text fixes the black-field bug */
    .stTextInput input, .stTextArea textarea {{
        background-color: {t['input_bg']} !important;
        color: {t['input_text']} !important;
        border: 1px solid {t['input_border']} !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: {t['input_text']} !important;
    }}
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="base-input"] {{
        background-color: {t['input_bg']} !important;
    }}
    .stTextInput svg {{ fill: {t['muted']}; }}
    ::placeholder {{ color: {t['muted']} !important; opacity: 1; }}

    /* File uploader */
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {t['card_bg']};
        border: 1px dashed {t['border']} !important;
    }}
    [data-testid="stFileUploaderDropzone"] * {{ color: {t['muted']} !important; }}

    /* Alerts */
    [data-testid="stAlert"] {{
        background-color: {t['card_bg']};
        border: 1px solid {t['border']};
        color: {t['text']};
    }}

    /* Expander */
    [data-testid="stExpander"] {{
        background-color: {t['card_bg']};
        border: 1px solid {t['border']} !important;
        border-radius: 12px;
    }}

    /* Named Entities / JSON viewer -- its own syntax-highlight colors are set via
       inline styles per token, calibrated for a plain white or pure-black background.
       Against our custom card/background colors that washes the text out to near
       invisible, so force one legible color for everything inside it. */
    [data-testid="stJson"] {{
        background-color: {t['card_bg']} !important;
        border-radius: 8px;
    }}
    [data-testid="stJson"] * {{ color: {t['text']} !important; opacity: 1 !important; }}

    /* Tabs */
    .stTabs [data-baseweb="tab"] {{ color: {t['muted']}; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ color: {t['primary']} !important; }}

    /* Badges */
    .badge {{ display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }}
    .badge-indigo {{ background: {t['badge_indigo_bg']}; color: {t['badge_indigo_text']}; }}
    .badge-mint   {{ background: {t['badge_mint_bg']};   color: {t['badge_mint_text']}; }}
    .badge-rose   {{ background: {t['badge_rose_bg']};   color: {t['badge_rose_text']}; }}
    .badge-slate  {{ background: {t['badge_slate_bg']};  color: {t['badge_slate_text']}; }}

    .check-row {{ display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.5rem 0; font-size: 0.92rem; }}
    .check-row .dot {{ flex-shrink: 0; width: 8px; height: 8px; border-radius: 50%; background: {t['primary']}; margin-top: 0.45rem; }}
    .muted {{ color: {t['muted']} !important; }}
    </style>
    """, unsafe_allow_html=True)


def render_json_block(data, t: dict) -> str:
    """Render JSON as plain, fully-styled text instead of Streamlit's built-in
    st.json component -- that component renders inside an isolated element (in
    some Streamlit versions, an iframe) that our page CSS cannot reach, which is
    why its syntax-highlight colors were unreadable against our custom theme.
    This gives full, guaranteed control over contrast instead."""
    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    escaped = html.escape(pretty)
    return f"""
    <pre style="background:{t['input_bg']}; color:{t['input_text']}; border:1px solid {t['border']};
    border-radius:8px; padding:1rem; overflow-x:auto; font-family:'Courier New', monospace;
    font-size:0.85rem; line-height:1.5; white-space:pre-wrap; word-break:break-word; margin:0;">{escaped}</pre>
    """


def pill(text: str, variant: str, t: dict) -> str:
    return f'<span class="badge badge-{variant}">{text}</span>'


def mark_card():
    """Call this as the first line inside a `with st.container(border=True):` block
    so the CSS above styles that wrapper -- and only that wrapper -- as a card."""
    st.markdown('<span class="card-marker"></span>', unsafe_allow_html=True)


def mark_card_entry():
    """Same as mark_card(), but for the login / guest entry cards so they get the
    light-blue background instead of the default card background."""
    st.markdown('<span class="card-marker-entry"></span>', unsafe_allow_html=True)


def score_ring(percent: float, label: str, t: dict) -> str:
    size, stroke = 150, 13
    radius = (size - stroke) / 2
    circumference = 2 * math.pi * radius
    filled = circumference * (max(0, min(100, percent)) / 100)
    return f"""
    <div style="display:flex; flex-direction:column; align-items:center; gap:0.4rem; padding: 0.5rem 0;">
      <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" stroke="{t['ring_track']}" stroke-width="{stroke}" />
        <circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" stroke="{t['primary']}" stroke-width="{stroke}"
          stroke-dasharray="{filled} {circumference}" stroke-linecap="round"
          transform="rotate(-90 {size/2} {size/2})" />
        <text x="50%" y="46%" text-anchor="middle" font-size="30" font-weight="800" fill="{t['text']}"
          font-family="Inter, sans-serif">{percent:.0f}</text>
        <text x="50%" y="62%" text-anchor="middle" font-size="11" fill="{t['muted']}"
          font-family="Inter, sans-serif">out of 100</text>
      </svg>
      <span style="font-size:0.85rem; font-weight:600; color:{t['text']};">{label}</span>
    </div>
    """


SENTIMENT_VARIANT = {"positive": "mint", "negative": "rose", "neutral": "slate", "mixed": "indigo"}


# ---------------------------------------------------------------------------
# Navbar (shown on every screen)
# ---------------------------------------------------------------------------
def render_navbar(t: dict):
    auth_status = st.session_state.get("auth_status")
    username = st.session_state.get("username")

    with st.container(border=True):
        mark_card()
        col_brand, col_spacer, col_theme, col_auth = st.columns([3, 3, 1, 1.5], vertical_alignment="center")

        with col_brand:
            st.markdown('<div style="font-weight:800; font-size:3.5rem; margin:-1.75rem 0 -1.75rem 0; line-height:1;">HireScope</div>', unsafe_allow_html=True)

        with col_theme:
            icon = "🌙" if st.session_state.theme == "light" else "☀️"
            if st.button(icon, key="theme_toggle", help="Toggle dark / light theme", use_container_width=True):
                st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
                st.rerun()

        with col_auth:
            if auth_status == "user":
                if st.button("Log out", key="navbar_logout", use_container_width=True):
                    for k in ("auth_status", "username"):
                        st.session_state.pop(k, None)
                    st.rerun()
            elif auth_status == "guest":
                if st.button("Exit guest", key="navbar_exit_guest", use_container_width=True):
                    for k in ("auth_status", "username"):
                        st.session_state.pop(k, None)
                    st.rerun()

    st.write("")


# ---------------------------------------------------------------------------
# Login / sign-up / guest page
# ---------------------------------------------------------------------------
def render_login_page(t: dict):
    render_navbar(t)

    st.markdown(f"""
    <div style="padding: 0.5rem 0 0.75rem;">
      <span class="page-root-marker"></span>
      <h1 style="font-size:2.3rem; font-weight:800; margin: 0.6rem 0 0.35rem; color:{t['hero_text']};">
        See your resume the way ATS bots do.
      </h1>
      <p class="muted" style="font-size:1.02rem; max-width:620px; margin:0;">
        Upload a resume to pull structured entities, sentiment, key phrases, and an optional
        job-match score — powered by Azure AI Document Intelligence and Azure AI Language.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            mark_card_entry()
            st.markdown(f"""
            <div style="padding: 0.25rem 0 0.5rem;">
              {pill("FULL HISTORY ACCESS", "indigo", t)}
              <h3 style="margin: 0.6rem 0 0.2rem;">Log in or create an account</h3>
              <p class="muted" style="font-size:0.9rem; margin:0 0 0.5rem;">
                Save every analysis, revisit your history, and download reports.
              </p>
            </div>
            """, unsafe_allow_html=True)

            login_tab, signup_tab = st.tabs(["Log In", "Sign Up"])

            with login_tab:
                with st.form("login_form", border=False):
                    username = st.text_input("Username", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    submitted = st.form_submit_button("Log In")
                if submitted:
                    if verify_login(username, password):
                        st.session_state.auth_status = "user"
                        st.session_state.username = username.strip().lower()
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")

            with signup_tab:
                with st.form("signup_form", border=False):
                    new_username = st.text_input("Choose a username", key="signup_username")
                    new_password = st.text_input("Choose a password (min 8 characters)", type="password", key="signup_password")
                    confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")
                    submitted = st.form_submit_button("Create Account")
                if submitted:
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        success, message = create_user(new_username, new_password)
                        if success:
                            st.success(message + " Please log in from the Log In tab.")
                        else:
                            st.error(message)

    with col2:
        with st.container(border=True):
            mark_card_entry()
            st.markdown(f"""
            <div style="padding: 0.25rem 0 0.5rem;">
              {pill("NO SIGN-UP NEEDED", "mint", t)}
              <h3 style="margin: 0.6rem 0 0.2rem;">Continue as guest</h3>
              <p class="muted" style="font-size:0.9rem; margin:0 0 0.75rem;">
                Run a single analysis right now, no account required.
              </p>
              <div class="check-row"><div class="dot"></div>Full analysis: entities, sentiment, key phrases, match score</div>
              <div class="check-row"><div class="dot"></div>Nothing saved to history, and nothing visible to anyone else</div>
              <div class="check-row"><div class="dot"></div>Report is not downloadable — copy what you need before you leave</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.auth_status = "guest"
                st.session_state.username = None
                st.rerun()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def render_main_app(t: dict):
    render_navbar(t)
    is_guest = st.session_state.auth_status == "guest"
    username = st.session_state.username

    if is_guest:
        st.markdown(f'{pill("GUEST SESSION", "slate", t)} <span class="muted" style="font-size:0.85rem;"> — results won\'t be saved and can\'t be downloaded</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'{pill("LOGGED IN", "mint", t)} <span class="muted" style="font-size:0.85rem;"> — {username}</span>', unsafe_allow_html=True)

    st.write("")

    if is_guest:
        tabs = st.tabs(["Analyze a Resume"])
        tab1 = tabs[0]
    else:
        tab1, tab2 = st.tabs(["Analyze a Resume", "History"])

    with tab1:
        with st.container(border=True):
            mark_card()
            uploaded = st.file_uploader("Upload a resume", type=["pdf", "jpg", "jpeg", "png"])
            job_description = st.text_area("Optional: paste a job description to get a match score")
            analyze_clicked = st.button("Analyze", disabled=not uploaded)

        if uploaded and analyze_clicked:
            with st.spinner("Extracting text with Document Intelligence..."):
                resume_text = extract_text(uploaded.getvalue())

            with st.spinner("Running Azure AI Language analysis..."):
                analysis = analyze_language(resume_text)
                analysis["match_score_percent"] = match_score(resume_text, job_description)

            if is_guest:
                st.info("Guest session — this analysis is not being saved and can't be downloaded.")
            else:
                blob_name = save_to_history(uploaded.name, analysis, username, uploaded.getvalue())
                st.success(f"Saved to history as {blob_name}")
                st.download_button(
                    "⬇️ Download analysis report (JSON)",
                    data=json.dumps(analysis, indent=2),
                    file_name=f"{uploaded.name}-analysis.json",
                    mime="application/json",
                )

            st.write("")
            st.markdown(pill("SCAN RESULTS", "indigo", t), unsafe_allow_html=True)
            st.write("")

            row1_col1, row1_col2 = st.columns([1, 2], gap="large")
            with row1_col1:
                with st.container(border=True):
                    mark_card()
                    if analysis["match_score_percent"] is not None:
                        st.markdown(score_ring(analysis["match_score_percent"], "Job Description Match", t), unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="text-align:center; padding: 1.5rem 0;">
                          <p class="muted" style="font-size:0.9rem;">Paste a job description above<br>to get a match score.</p>
                        </div>
                        """, unsafe_allow_html=True)
            with row1_col2:
                with st.container(border=True):
                    mark_card()
                    st.markdown('<h4 style="margin-top:0;">Summary</h4>', unsafe_allow_html=True)
                    st.write(analysis["summary"])
                    st.markdown(f"""
                    <div style="margin-top:0.75rem;">
                      {pill("Detected language: " + analysis["language"], "slate", t)}
                      {pill(analysis["sentiment"].capitalize() + " sentiment", SENTIMENT_VARIANT.get(analysis["sentiment"].lower(), "slate"), t)}
                    </div>
                    """, unsafe_allow_html=True)

            st.write("")

            row2_col1, row2_col2 = st.columns(2, gap="large")
            with row2_col1:
                with st.container(border=True):
                    mark_card()
                    st.markdown('<h4 style="margin-top:0;">Key Phrases</h4>', unsafe_allow_html=True)
                    phrase_html = " ".join(pill(p, "indigo", t) for p in analysis["key_phrases"]) or '<span class="muted">None detected</span>'
                    st.markdown(f'<div style="line-height:2.1;">{phrase_html}</div>', unsafe_allow_html=True)
            with row2_col2:
                with st.container(border=True):
                    mark_card()
                    st.markdown('<h4 style="margin-top:0;">Named Entities</h4>', unsafe_allow_html=True)
                    st.markdown(render_json_block(analysis["entities"], t), unsafe_allow_html=True)

            st.write("")

            with st.container(border=True):
                mark_card()
                st.markdown('<h4 style="margin-top:0;">PII-Redacted Text</h4>', unsafe_allow_html=True)
                st.text_area("Redacted", analysis["redacted_text"], height=200, label_visibility="collapsed")

    if not is_guest:
        with tab2:
            st.markdown('<h4>Your Analysis History</h4>', unsafe_allow_html=True)
            container = get_blob_container()
            history = load_history(username)
            if not history:
                st.info("No history yet — analyze a resume to get started.")
            for blob_name in history:
                data_bytes = container.download_blob(blob_name).readall()
                data = json.loads(data_bytes)
                with st.expander(blob_name):
                    st.markdown(render_json_block(data, t), unsafe_allow_html=True)
                    st.download_button(
                        "⬇️ Download this report (JSON)",
                        data=data_bytes,
                        file_name=blob_name.split("/")[-1],
                        mime="application/json",
                        key=f"download-{blob_name}",
                    )


if "auth_status" not in st.session_state:
    st.session_state.auth_status = None
if "theme" not in st.session_state:
    st.session_state.theme = "light"

tokens = get_tokens()
inject_css(tokens)

if st.session_state.auth_status is None:
    render_login_page(tokens)
else:
    render_main_app(tokens)