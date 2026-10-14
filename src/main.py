import streamlit as st
from auth.session_manager import SessionManager
from components.auth_pages import show_login_page
from components.sidebar import show_sidebar
from components.analysis_form import show_analysis_form
from components.footer import show_footer
from components.biomarker_table import show_biomarker_table, load_biomarkers_from_messages
from utils.report_exporter import generate_pdf
from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
from services.ai_service import get_chat_response, translate_text
from components.voice_io import transcribe_audio, text_to_speech, LANGUAGE_TO_GTTS

st.set_page_config(
    page_title="HIA - Health Insights Agent", page_icon="🩺", layout="wide"
)
SessionManager.init_session()

# Global styles
st.markdown("""
<style>
div[data-testid="InputInstructions"] > span:nth-child(1) { visibility: hidden; }

/* Chat message styling */
[data-testid="stChatMessage"] {
    padding: 0.6rem 0 !important;
    border-bottom: none !important;
}
/* User bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: transparent !important;
}
/* Give chat input area breathing room */
.stChatInput { padding-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ── helpers ────────────────────────────────────────────────────────────────────

def _sid():
    s = st.session_state.get("current_session")
    return s["id"] if s else None


def _load_messages():
    sid = _sid()
    if not sid:
        return []
    ok, msgs = st.session_state.auth_service.get_session_messages(sid)
    return msgs if ok else []


def _ensure_cache():
    sid = _sid()
    if st.session_state.get("_cached_sid") != sid:
        st.session_state._cached_sid = sid
        st.session_state._cached_msgs = _load_messages()
        st.session_state.pop("current_biomarkers", None)
        st.session_state.pop("current_report_text", None)


def _get_context(messages):
    if st.session_state.get("current_report_text"):
        return st.session_state.current_report_text
    for msg in messages:
        if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get("content", ""):
            c = msg["content"]
            s = c.find("__REPORT_TEXT__\n") + len("__REPORT_TEXT__\n")
            e = c.find("\n__END_REPORT_TEXT__")
            if e > s:
                text = c[s:e]
                st.session_state.current_report_text = text
                return text
    return ""


# ── sidebar ────────────────────────────────────────────────────────────────────

def show_full_sidebar(messages):
    show_sidebar()

    with st.sidebar:
        has_analysis = any(m["role"] == "assistant" for m in messages if m.get("role") != "system")

        if has_analysis:
            st.markdown("---")

            # PDF download
            patient_name = ""
            for m in messages:
                if m.get("role") == "user" and "Analyzing report for patient:" in m.get("content", ""):
                    patient_name = m["content"].replace("Analyzing report for patient:", "").strip()
                    break
            biomarkers = st.session_state.get("current_biomarkers")
            pdf_bytes = generate_pdf(patient_name, messages, biomarkers)
            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"HIA_{patient_name or 'report'}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            # Translate
            language = st.session_state.get("output_language", "English")
            if language != "English":
                if st.button(f"🌐 Translate → {language}", use_container_width=True):
                    for m in messages:
                        if m.get("role") == "assistant":
                            with st.spinner(f"Translating..."):
                                translated = translate_text(m["content"], language)
                            st.session_state.auth_service.save_chat_message(
                                _sid(), f"[Translated to {language}]\n\n{translated}", role="assistant")
                            st.session_state._cached_msgs = _load_messages()
                            st.rerun()
                            break

            # Biomarker table
            if "current_biomarkers" not in st.session_state:
                recovered = load_biomarkers_from_messages(messages)
                if recovered:
                    st.session_state.current_biomarkers = recovered
            if st.session_state.get("current_biomarkers"):
                with st.expander("🧪 Biomarker Table", expanded=False):
                    show_biomarker_table(st.session_state.current_biomarkers)

            # New analysis
            st.markdown("---")
            with st.expander("🔄 New Analysis", expanded=False):
                show_analysis_form()

        # Mic
        st.markdown("---")
        st.markdown("**🎙️ Voice Input**")
        try:
            from audio_recorder_streamlit import audio_recorder
            audio_bytes = audio_recorder(
                text="Record question",
                recording_color="#e74c3c",
                neutral_color="#3498db",
                icon_size="1x",
                pause_threshold=2.0,
                key="sidebar_mic",
            )
            if audio_bytes and len(audio_bytes) > 1000:
                if st.session_state.get("_last_audio_len") != len(audio_bytes):
                    st.session_state._last_audio_len = len(audio_bytes)
                    with st.spinner("Transcribing..."):
                        transcript = transcribe_audio(audio_bytes)
                    if transcript and not transcript.startswith("Transcription error"):
                        st.session_state._voice_prompt = transcript
                        st.success(f"Heard: *{transcript}*")
                    else:
                        st.error(transcript)
        except ImportError:
            st.caption("audio-recorder-streamlit not installed")


# ── welcome ────────────────────────────────────────────────────────────────────

def show_welcome_screen():
    st.markdown(f"""
    <div style='text-align:center; padding:80px 20px 40px;'>
      <div style='font-size:5rem; margin-bottom:0.5rem'>{APP_ICON}</div>
      <h1 style='font-size:3rem; margin-bottom:0.25rem'>{APP_NAME}</h1>
      <p style='font-size:1.25rem; color:#90caf9; margin-bottom:0.25rem'>{APP_DESCRIPTION}</p>
      <p style='color:#607d8b'>{APP_TAGLINE}</p>
    </div>""", unsafe_allow_html=True)

    _, c, _ = st.columns([2, 3, 2])
    with c:
        if st.button("➕ Create New Analysis Session", use_container_width=True, type="primary"):
            ok, session = SessionManager.create_chat_session()
            if ok:
                st.session_state.current_session = session
                st.rerun()
            else:
                st.error("Failed to create session")


# ── chat area ──────────────────────────────────────────────────────────────────

def show_chat_area():
    _ensure_cache()
    messages = st.session_state._cached_msgs

    has_analysis = any(m["role"] == "assistant" for m in messages if m.get("role") != "system")

    # No analysis yet → show upload form
    if not has_analysis:
        show_analysis_form()
        return

    # Render message history
    for msg in messages:
        if msg.get("role") == "system":
            continue
        role = msg["role"]
        avatar = "👤" if role == "user" else "🩺"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    # Voice prompt from sidebar
    voice_prompt = st.session_state.pop("_voice_prompt", None)

    # Chat input (sticks to bottom automatically)
    prompt = st.chat_input("Ask a question about your report...") or voice_prompt

    if prompt:
        # Show user message immediately
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Save user turn
        st.session_state.auth_service.save_chat_message(_sid(), prompt, role="user")

        # Get + show AI response
        context = _get_context(messages)
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner(""):
                response = get_chat_response(prompt, context, messages)
            st.markdown(response)

            # Optional TTS
            lang_code = LANGUAGE_TO_GTTS.get(st.session_state.get("output_language", "English"), "en")
            if st.button("🔊 Listen to response", key=f"tts_{len(messages)}"):
                audio = text_to_speech(response, lang_code)
                if audio:
                    st.audio(audio, format="audio/mp3")

        # Persist + refresh cache
        st.session_state.auth_service.save_chat_message(_sid(), response, role="assistant")
        st.session_state._cached_msgs = _load_messages()


# ── app ────────────────────────────────────────────────────────────────────────

def main():
    SessionManager.init_session()

    if not SessionManager.is_authenticated():
        show_login_page()
        show_footer()
        return

    _ensure_cache()
    messages = st.session_state.get("_cached_msgs", [])

    show_full_sidebar(messages)

    # Greeting
    if st.session_state.user:
        name = st.session_state.user.get("name") or st.session_state.user.get("email", "")
        st.markdown(f"<div style='text-align:right;color:#64B5F6;padding:0.25rem 0.5rem;font-size:0.9rem'>👋 {name}</div>",
                    unsafe_allow_html=True)

    if st.session_state.get("current_session"):
        st.title(f"📊 {st.session_state.current_session['title']}")
        show_chat_area()
    else:
        show_welcome_screen()


if __name__ == "__main__":
    main()
