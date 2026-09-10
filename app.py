import os
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Burmese Audio Labeling", layout="centered")

# --- SUPABASE CONFIG ---
SUPABASE_URL = "https://vwgoawszrclehxrhzfau.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3Z29hd3N6cmNsZWh4cmh6ZmF1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwNDU5MDcsImV4cCI6MjEwNDYyMTkwN30.vLxe427q2VFk2m1IyDGRxwVrC9W76dAuHgTde0u9s_8"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Annotator အကောင့် ၄ ခု
USERS = {
    "annotator1": "pass123",
    "annotator2": "pass456",
    "annotator3": "pass789",
    "annotator4": "pass000",
}
AUDIO_BASE_DIR = "audio_clips"

# --- LOGIN FLOW ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login to Annotate")
    user_input = st.text_input("Username")
    pass_input = st.text_input("Password", type="password")
    if st.button("Login"):
        if user_input in USERS and USERS[user_input] == pass_input:
            st.session_state.user = user_input
            st.rerun()
        else:
            st.error("Username သို့မဟုတ် Password မှားယွင်းနေပါသည်။")
    st.stop()

current_user = st.session_state.user

# --- LIVE METRICS & PROGRESS ---
all_rows = supabase.table("audio_annotations").select("id, status").execute().data
total_clips = len(all_rows)
completed_clips = len([r for r in all_rows if r["status"] in ["done", "need_edit", "delete"]])
progress = (completed_clips / total_clips) if total_clips > 0 else 0

st.sidebar.write(f"Logged in as: **{current_user}**")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

st.title("🎙️ Burmese Audio Annotation")
st.progress(progress)
st.caption(f"📊 စုစုပေါင်း ပြီးမြောက်မှု: **{completed_clips}/{total_clips}** ({(progress * 100):.1f}%)")

# --- FETCH NEXT CLIP ---
pending_data = supabase.table("audio_annotations") \
    .select("*") \
    .eq("status", "pending") \
    .order("id") \
    .execute().data

# Skip လုပ်ထားခြင်း မရှိသော ဖိုင်များကို စစ်ထုတ်ခြင်း
available_data = [
    r for r in pending_data 
    if current_user not in (r.get("skipped_by") or "").split(",")
]

if not available_data:
    st.success("🎉 သင့်အတွက် Annotation လုပ်ရန် ကျန်ရှိသော clip မရှိတော့ပါ!")
    st.stop()

current_row = available_data[0]
row_id = current_row["id"]
clip_rel_path = current_row["filename"]
audio_path = os.path.join(AUDIO_BASE_DIR, clip_rel_path)

st.subheader(f"Audio Clip: `{clip_rel_path}`")
if os.path.exists(audio_path):
    st.audio(audio_path, format="audio/wav")
else:
    st.error(f"Audio file `{audio_path}` ကို ရှာမတွေ့ပါ။")

user_text = st.text_area("စာသားရိုက်ထည့်ပါ (Transcription):", key=f"text_{row_id}")

# --- ACTION BUTTONS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("✅ Submit", type="primary", use_container_width=True):
        if not user_text.strip():
            st.warning("စာသား အရင်ရိုက်ထည့်ပေးပါ။")
        else:
            supabase.table("audio_annotations").update({
                "text": user_text.strip(),
                "status": "done",
                "annotated_by": current_user
            }).eq("id", row_id).execute()
            st.rerun()

with col2:
    if st.button("⏭️ Skip", use_container_width=True):
        existing_skips = [s for s in (current_row.get("skipped_by") or "").split(",") if s]
        if current_user not in existing_skips:
            existing_skips.append(current_user)
        supabase.table("audio_annotations").update({
            "skipped_by": ",".join(existing_skips)
        }).eq("id", row_id).execute()
        st.rerun()

with col3:
    if st.button("⚠️ Need Edit", use_container_width=True):
        supabase.table("audio_annotations").update({
            "status": "need_edit",
            "annotated_by": current_user
        }).eq("id", row_id).execute()
        st.rerun()

with col4:
    if st.button("🗑️ Delete", use_container_width=True):
        supabase.table("audio_annotations").update({
            "status": "delete",
            "annotated_by": current_user
        }).eq("id", row_id).execute()
        st.rerun()