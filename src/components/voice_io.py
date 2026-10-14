import io
import streamlit as st
from groq import Groq


def transcribe_audio(audio_bytes: bytes) -> str:
    """Send audio bytes to Groq Whisper for transcription."""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=audio_file,
            response_format="text",
        )
        return transcription.strip()
    except Exception as e:
        return f"Transcription error: {str(e)}"


def text_to_speech(text: str, lang_code: str = "en") -> bytes | None:
    """Convert text to speech using gTTS. Returns MP3 bytes."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text[:3000], lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


LANGUAGE_TO_GTTS = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Arabic": "ar",
    "Chinese (Simplified)": "zh-CN",
    "Portuguese": "pt",
    "Tamil": "ta",
}


def show_mic_input() -> str | None:
    """Render mic recorder. Returns transcribed text or None."""
    try:
        from audio_recorder_streamlit import audio_recorder
        st.markdown("**🎙️ Or ask by voice:**")
        audio_bytes = audio_recorder(
            text="Click to record",
            recording_color="#e74c3c",
            neutral_color="#3498db",
            icon_size="2x",
            pause_threshold=2.0,
            key="mic_recorder",
        )
        if audio_bytes and len(audio_bytes) > 1000:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_bytes)
            if transcript and not transcript.startswith("Transcription error"):
                st.success(f"Heard: *{transcript}*")
                return transcript
            elif transcript.startswith("Transcription error"):
                st.error(transcript)
        return None
    except ImportError:
        st.warning("audio-recorder-streamlit not installed.")
        return None


def play_response(text: str):
    """Convert AI response to audio and auto-play."""
    language = st.session_state.get("output_language", "English")
    lang_code = LANGUAGE_TO_GTTS.get(language, "en")
    audio_bytes = text_to_speech(text, lang_code)
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
