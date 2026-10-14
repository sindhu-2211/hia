import streamlit as st
from config.prompts import SPECIALIST_PROMPTS
from utils.pdf_extractor import extract_text_from_pdf, extract_text_from_image
from config.sample_data import SAMPLE_REPORT
from config.app_config import MAX_UPLOAD_SIZE_MB


def show_analysis_form():
    # Initialize report source in session state for new sessions
    if (
        "current_session" in st.session_state
        and "report_source" not in st.session_state
    ):
        st.session_state.report_source = "Upload PDF"

    report_source = st.radio(
        "Choose report source",
        ["Upload PDF", "Use Sample PDF"],
        index=0 if st.session_state.get("report_source") == "Upload PDF" else 1,
        horizontal=True,
        key="report_source",
    )

    pdf_contents = get_report_contents(report_source)

    if pdf_contents:  # Only show form if we have report content
        render_patient_form(pdf_contents)


IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}

def get_report_contents(report_source):
    if report_source == "Upload PDF":
        uploaded_file = st.file_uploader(
            f"Upload blood report (PDF, JPG, PNG — Max {MAX_UPLOAD_SIZE_MB}MB)",
            type=["pdf", "jpg", "jpeg", "png"],
            help=f"Maximum file size: {MAX_UPLOAD_SIZE_MB}MB. PDF or image of a medical report.",
        )
        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            if file_size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(
                    f"File size ({file_size_mb:.1f}MB) exceeds the {MAX_UPLOAD_SIZE_MB}MB limit."
                )
                return None

            if uploaded_file.type in IMAGE_TYPES:
                contents = extract_text_from_image(uploaded_file)
            elif uploaded_file.type == "application/pdf":
                contents = extract_text_from_pdf(uploaded_file)
            else:
                st.error("Unsupported file type. Upload a PDF, JPG, or PNG.")
                return None

            if isinstance(contents, str) and (
                contents.startswith(
                    ("File size exceeds", "Invalid file type", "Error validating", "OCR error", "Could not")
                )
                or "error" in contents.lower()
            ):
                st.error(contents)
                return None
            with st.expander("View Extracted Report"):
                st.text(contents)
            return contents
    else:
        with st.expander("View Sample Report"):
            st.text(SAMPLE_REPORT)
        return SAMPLE_REPORT
    return None


def render_patient_form(pdf_contents):
    with st.form("analysis_form"):
        patient_name = st.text_input("Patient Name")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        if st.form_submit_button("Analyze Report"):
            handle_form_submission(patient_name, age, gender, pdf_contents)


def handle_form_submission(patient_name, age, gender, pdf_contents):
    if not all([patient_name, age, gender]):
        st.error("Please fill in all fields")
        return

    # Check rate limit first, outside of spinner
    from services.ai_service import generate_analysis

    can_analyze, error_msg = generate_analysis(None, None, check_only=True)
    if not can_analyze:
        st.error(error_msg)
        st.stop()
        return

    with st.spinner("Analyzing report..."):
        # Save report content for follow-up chat (session state for immediate use)
        st.session_state.current_report_text = pdf_contents

        # Save user message and proceed with analysis
        st.session_state.auth_service.save_chat_message(
            st.session_state.current_session["id"],
            f"Analyzing report for patient: {patient_name}",
        )

        # Build prompt — inject language if not English
        base_prompt = SPECIALIST_PROMPTS["comprehensive_analyst"]
        language = st.session_state.get("output_language", "English")
        if language != "English":
            base_prompt += f"\n\nIMPORTANT: Write your entire response in {language}. All headings, labels, and content must be in {language}."

        # Generate analysis
        result = generate_analysis(
            {
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "report": pdf_contents,
            },
            base_prompt,
        )

        if result["success"]:
            # Store report text as a system message for persistence
            report_metadata = f"__REPORT_TEXT__\n{pdf_contents}\n__END_REPORT_TEXT__"
            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session["id"], report_metadata, role="system"
            )

            # Extract and persist structured biomarkers
            from services.ai_service import extract_biomarkers
            import json
            biomarkers = extract_biomarkers(pdf_contents)
            if biomarkers:
                st.session_state.current_biomarkers = biomarkers
                biomarker_metadata = f"__BIOMARKERS__\n{json.dumps(biomarkers)}\n__END_BIOMARKERS__"
                st.session_state.auth_service.save_chat_message(
                    st.session_state.current_session["id"], biomarker_metadata, role="system"
                )

            # Add model used information if available
            content = result["content"]
            if "model_used" in result:
                model_info = f"\n\n*Analysis generated using {result['model_used']}*"
                content += model_info

            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session["id"], content, role="assistant"
            )
            # Force cache invalidation so next render reloads messages from DB
            st.session_state.pop("_cached_sid", None)
            st.session_state.pop("_cached_msgs", None)
            st.rerun()
        else:
            st.error(result["error"])
            st.stop()
