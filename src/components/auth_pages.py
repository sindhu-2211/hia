import streamlit as st
from auth.session_manager import SessionManager
from config.app_config import APP_ICON, APP_NAME, APP_TAGLINE, APP_DESCRIPTION
from utils.validators import validate_signup_fields
import time


def show_login_page():
    if "form_type" not in st.session_state:
        st.session_state["form_type"] = "login"

    current_form = st.session_state["form_type"]

    st.markdown("""
        <style>
        div[data-testid="InputInstructions"] > span:nth-child(1) { visibility: hidden; }

        .auth-hero {
            background: linear-gradient(135deg, #0d1b2a 0%, #1a237e 60%, #0a3d62 100%);
            border-radius: 20px;
            padding: 3rem 2rem;
            text-align: center;
            color: white;
            min-height: 480px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .auth-hero h1 { font-size: 3rem; margin-bottom: 0.5rem; }
        .auth-hero p  { font-size: 1.1rem; opacity: 0.85; line-height: 1.6; }
        .feature-pill {
            display: inline-block;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            padding: 6px 16px;
            margin: 4px;
            font-size: 0.85rem;
            color: #e3f2fd;
        }
        .auth-card {
            background: #ffffff08;
            border: 1px solid #ffffff18;
            border-radius: 16px;
            padding: 2.5rem 2rem;
        }
        .auth-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #e3f2fd;
            margin-bottom: 0.25rem;
        }
        .auth-sub {
            color: #90caf9;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        div[data-testid="stForm"] input {
            background: #0d1b2a !important;
            border: 1px solid #1a237e !important;
            border-radius: 8px !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown(f"""
        <div class="auth-hero">
            <div style="font-size:4rem; margin-bottom:0.5rem">{APP_ICON}</div>
            <h1>{APP_NAME}</h1>
            <p style="font-size:1.2rem; font-weight:600; color:#90caf9; margin-bottom:0.5rem">{APP_DESCRIPTION}</p>
            <p>{APP_TAGLINE}</p>
            <div style="margin-top:2rem">
                <span class="feature-pill">🧬 AI Blood Analysis</span>
                <span class="feature-pill">📊 Biomarker Tracking</span>
                <span class="feature-pill">🌐 Multi-language</span>
                <span class="feature-pill">🎙️ Voice Q&A</span>
                <span class="feature-pill">📄 PDF Export</span>
                <span class="feature-pill">🔍 OCR Support</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        is_login = current_form == "login"
        st.markdown(f"""
        <div style="padding: 1rem 0">
            <div class="auth-title">{"Welcome back 👋" if is_login else "Create account 🚀"}</div>
            <div class="auth-sub">{"Sign in to your HIA account" if is_login else "Start your health journey today"}</div>
        </div>
        """, unsafe_allow_html=True)

        if is_login:
            show_login_form()
        else:
            show_signup_form()

        st.markdown("<br>", unsafe_allow_html=True)
        toggle_text = "Don't have an account? **Sign up**" if is_login else "Already have an account? **Login**"
        if st.button(toggle_text, use_container_width=True, type="secondary"):
            st.session_state["form_type"] = "signup" if is_login else "login"
            st.rerun()


def show_login_form():
    with st.form("login_form"):
        email = st.text_input("📧 Email", key="login_email", placeholder="you@example.com")
        password = st.text_input("🔑 Password", type="password", key="login_password", placeholder="••••••••")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Login →", use_container_width=True, type="primary"):
            if email and password:
                success, result = SessionManager.login(email, password)
                if success:
                    with st.spinner("Logging in..."):
                        st.success("Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error(f"Login failed: {result}")
            else:
                st.error("Please enter both email and password")


def show_signup_form():
    with st.form("signup_form"):
        new_name = st.text_input("👤 Full Name", key="signup_name", placeholder="Your name")
        new_email = st.text_input("📧 Email", key="signup_email", placeholder="you@example.com")
        new_password = st.text_input("🔑 Password", type="password", key="signup_password", placeholder="Min 8 chars, upper, lower, number")
        confirm_password = st.text_input("🔑 Confirm Password", type="password", key="signup_password2", placeholder="Repeat password")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Create Account →", use_container_width=True, type="primary"):
            validation_result = validate_signup_fields(new_name, new_email, new_password, confirm_password)
            if not validation_result[0]:
                st.error(validation_result[1])
                return
            with st.spinner("Creating your account..."):
                success, response = st.session_state.auth_service.sign_up(new_email, new_password, new_name)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = response
                    st.success("Account created! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Sign up failed: {response}")
