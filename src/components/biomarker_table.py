import streamlit as st
import json


STATUS_CONFIG = {
    "normal":        {"color": "#2e7d32", "bg": "#e8f5e9", "label": "Normal",        "icon": "✅"},
    "low":           {"color": "#1565c0", "bg": "#e3f2fd", "label": "Low",           "icon": "🔵"},
    "high":          {"color": "#e65100", "bg": "#fff3e0", "label": "High",          "icon": "🟠"},
    "critical_low":  {"color": "#b71c1c", "bg": "#ffebee", "label": "Critical Low",  "icon": "🔴"},
    "critical_high": {"color": "#b71c1c", "bg": "#ffebee", "label": "Critical High", "icon": "🔴"},
    "unknown":       {"color": "#555555", "bg": "#f5f5f5", "label": "Unknown",       "icon": "⚪"},
}


def _row_html(bm):
    status = bm.get("status", "unknown").lower()
    cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["unknown"])
    return f"""
    <tr style="background:{cfg['bg']};">
      <td style="padding:8px 12px; font-weight:500; color:#212121;">{bm.get('name','—')}</td>
      <td style="padding:8px 12px; text-align:center; font-weight:600;">{bm.get('value','—')}</td>
      <td style="padding:8px 12px; text-align:center; color:#555;">{bm.get('unit','—')}</td>
      <td style="padding:8px 12px; text-align:center; color:#555;">{bm.get('reference_range','—')}</td>
      <td style="padding:8px 12px; text-align:center;">
        <span style="color:{cfg['color']}; font-weight:600;">{cfg['icon']} {cfg['label']}</span>
      </td>
    </tr>"""


def show_biomarker_table(biomarkers):
    if not biomarkers:
        return

    abnormal = [b for b in biomarkers if b.get("status", "unknown") not in ("normal", "unknown")]

    st.markdown("### 🧪 Biomarker Summary")

    if abnormal:
        st.warning(f"**{len(abnormal)} abnormal value(s) detected** — see highlighted rows below.")

    header = """
    <table style="width:100%; border-collapse:collapse; font-size:0.9em; margin-top:8px;">
      <thead>
        <tr style="background:#1a237e; color:white;">
          <th style="padding:10px 12px; text-align:left;">Biomarker</th>
          <th style="padding:10px 12px; text-align:center;">Value</th>
          <th style="padding:10px 12px; text-align:center;">Unit</th>
          <th style="padding:10px 12px; text-align:center;">Reference Range</th>
          <th style="padding:10px 12px; text-align:center;">Status</th>
        </tr>
      </thead>
      <tbody>"""

    rows = "".join(_row_html(b) for b in biomarkers)
    footer = "</tbody></table>"

    st.markdown(header + rows + footer, unsafe_allow_html=True)

    # Legend
    st.markdown(
        "<br><small>"
        "✅ Normal &nbsp;|&nbsp; 🔵 Low &nbsp;|&nbsp; 🟠 High &nbsp;|&nbsp; 🔴 Critical &nbsp;|&nbsp; ⚪ Unknown"
        "</small>",
        unsafe_allow_html=True,
    )


def load_biomarkers_from_messages(messages):
    """Recover stored biomarkers from Supabase system messages."""
    for msg in messages:
        if msg.get("role") == "system" and "__BIOMARKERS__" in msg.get("content", ""):
            content = msg["content"]
            start = content.find("__BIOMARKERS__\n") + len("__BIOMARKERS__\n")
            end = content.find("\n__END_BIOMARKERS__")
            if start > len("__BIOMARKERS__\n") - 1 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
    return None
