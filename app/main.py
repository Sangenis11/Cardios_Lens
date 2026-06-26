import streamlit as st
import requests
import time
import re
import os
import sys
import html
import streamlit.components.v1 as components

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="CardioLens_CCDC",
    page_icon="🫀",
    layout="wide"
)

API_BASE = "http://127.0.0.1:8000"
API_RUN = f"{API_BASE}/process-ecg/"
API_STATUS = f"{API_BASE}/status/"
API_LOGS = f"{API_BASE}/logs/"
API_DOWNLOAD = f"{API_BASE}/download/"
API_STOP = f"{API_BASE}/stop/"
API_CLEAN = f"{API_BASE}/cleanup/"

# =========================
# SESSION STATE
# =========================
if "run_id" not in st.session_state:
    st.session_state.run_id = None

if "status" not in st.session_state:
    st.session_state.status = "idle"


# =========================
# 🎨 STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #eef2f7, #e6ecf5);
}

.card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    margin-bottom: 20px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
}

.stButton>button {
    background: linear-gradient(135deg, #1565c0, #42a5f5);
    color: white;
    border-radius: 10px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =========================
# ASSETS
# =========================
def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    return os.path.join('assets', filename)

# =========================
# HEADER
# =========================
col_logo1, col_title, col_logo2 = st.columns([1.5, 3, 1.5])

with col_logo1:
    st.image(get_asset_path("logo.png"), width=140)

with col_title:
    st.markdown("""
    <div style="text-align:center;">
        <h1>🫀 CardioLens_CCDC</h1>
        <h3 style="color:#3A7BD5;">Clinical ECG Processing & HRV Platform</h3>
    </div>
    """, unsafe_allow_html=True)

with col_logo2:
    st.image(get_asset_path("ccdc_logo.png"), width=140)

st.markdown("---")

col1, col2 = st.columns([1, 2])

# =========================
# LEFT PANEL
# =========================
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload ECG ZIP",
        type=["zip"],
        disabled=st.session_state.status == "running"
    )

    if st.button("🚀 Run", disabled=st.session_state.status == "running"):
        if uploaded is None:
            st.warning("Please upload a ZIP file first")
        else:
            files = {"file": (uploaded.name, uploaded.getvalue())}
            res = requests.post(API_RUN, files=files).json()

            st.session_state.run_id = res["run_id"]
            st.session_state.status = "running"

    if st.session_state.status == "running":
        if st.button("🛑 Stop"):
            requests.post(API_STOP + st.session_state.run_id)
            st.session_state.status = "stopping"

    if st.session_state.status in ["completed", "failed", "stopped"]:
        if st.button("🔄 New Run"):
            st.session_state.run_id = None
            st.session_state.status = "idle"

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RIGHT PANEL
# =========================
with col2:

    # STATUS
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Status")

    status_data = {}

    if st.session_state.run_id:
        try:
            status_data = requests.get(API_STATUS + st.session_state.run_id).json()
            st.session_state.status = status_data["status"]
        except:
            st.session_state.status = "error"

    status = st.session_state.status

    if status == "running":
        st.markdown("### 🔄 Processing ECG...")
    elif status == "completed":
        st.markdown("### ✅ Processing completed")
    elif status == "failed":
        st.markdown("### ❌ Processing failed")
    elif status == "stopped":
        st.markdown("### ⚠️ Stopped by user")
    elif status == "stopping":
        st.markdown("### ⏳ Stopping...")
    else:
        st.markdown("### 💤 Idle")

    st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # LOGS + PROGRESS + ETA
    # =========================
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📜 Live Logs")

    logs = ""
    progress = 0

    if st.session_state.run_id:
        try:
            logs = requests.get(API_LOGS + st.session_state.run_id).text

            match = re.findall(r"\[PROGRESS\] (\d+)", logs)
            if match:
                progress = int(match[-1])
        except:
            logs = "Error fetching logs"

    st.progress(progress / 100 if progress else 0)

    # ETA
    time_box = st.empty()

    if "estimated_time" in status_data and "start_time" in status_data:
        try:
            elapsed = time.time() - float(status_data["start_time"])
            remaining = max(0, float(status_data["estimated_time"]) - elapsed)
            remaining = int(remaining)

            mins = remaining // 60
            secs = remaining % 60

            if remaining <= 10:
                time_box.info("⏱ Almost done...")
            elif mins > 0:
                time_box.info(f"⏱ {mins} min {secs} sec remaining")
            else:
                time_box.info(f"⏱ {secs} sec remaining")
        except:
            time_box.info("⏱ Estimating...")
    else:
        time_box.info("⏱ Estimating...")

    # =========================
    # AUTO-SCROLL LOG PANEL
    # =========================
    safe_logs = html.escape(logs)

    components.html(f"""
    <div id="logbox" style="
        background-color:#0f172a;
        color:#22c55e;
        padding:14px;
        border-radius:10px;
        height:400px;
        overflow-y:auto;
        font-family:monospace;
        font-size:12.5px;
        border:1px solid #1f2937;
        white-space:pre-wrap;
    ">
    {safe_logs}
    </div>

    <script>
    var logDiv = document.getElementById("logbox");
    if (logDiv) {{
        logDiv.scrollTop = logDiv.scrollHeight;
    }}
    </script>
    """, height=420)

    st.markdown('</div>', unsafe_allow_html=True)

    # DOWNLOAD
    st.markdown('<div class="card">', unsafe_allow_html=True)

    if status == "completed":
        st.subheader("📥 Download Results")

        if st.button("Prepare Download"):
            with st.spinner("Preparing ZIP..."):
                response = requests.get(API_DOWNLOAD + st.session_state.run_id)
                st.session_state.download_data = response.content

        if "download_data" in st.session_state:
            st.download_button(
                label="⬇ Download ZIP",
                data=st.session_state.download_data,
                file_name="cardiolens_results.zip"
            )

        if st.button("🧹 Cleanup"):
            requests.delete(API_CLEAN + st.session_state.run_id)
            st.success("Cleaned successfully")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# AUTO REFRESH
# =========================
if st.session_state.status in ["running", "stopping"]:
    time.sleep(1)
    st.rerun()