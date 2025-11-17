import streamlit as st
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import os

API_BASE = os.getenv("JOURNAL_API", "http://localhost:8001")

st.set_page_config(page_title="AI Journal POC", layout="wide")
st.title("AI-Powered Journal Assistant (POC)")

with st.form("entry_form"):
    text = st.text_area("Write your journal entry", height=200, value="")
    submitted = st.form_submit_button("Save & Analyze")

if submitted and text.strip():
    # POST to backend
    resp = requests.post(f"{API_BASE}/entries", json={"text": text})
    if resp.status_code != 200:
        st.error(f"Error from API: {resp.status_code} {resp.text}")
    else:
        data = resp.json()
        st.success("Saved and analyzed ✅")
        st.header("AI Corrected Text")
        st.write(data.get("corrected_text") or "—")
        st.header("AI Insights")
        insights = data.get("ai_insights") or {}
        st.subheader("Themes")
        st.write(insights.get("themes"))
        st.subheader("Insights")
        for s in insights.get("insights", []):
            st.write("- " + s)
        st.subheader("Follow-up prompts")
        for p in insights.get("follow_up_prompts", []):
            st.write("- " + p)
        st.subheader("Supportive message")
        st.info(insights.get("supportive_message", ""))

st.markdown("---")
st.header("Past Entries & Mood Timeline")
# fetch entries
entries = requests.get(f"{API_BASE}/entries").json()
if not entries:
    st.write("No entries yet.")
else:
    # show the 5 most recent
    st.subheader("Recent entries")
    for e in entries[:5]:
        created = datetime.fromisoformat(e["created_at"])
        st.markdown(f"**{created.strftime('%Y-%m-%d %H:%M')}** — mood: *{e.get('mood')}* ({e.get('mood_score')})")
        st.write(e["original_text"][:300] + ("…" if len(e["original_text"]) > 300 else ""))

    # analytics
    analytics = requests.get(f"{API_BASE}/analytics").json()
    timeline = analytics.get("timeline", [])
    if timeline:
        dates = [datetime.fromisoformat(x["created_at"]) for x in timeline]
        scores = [x["mood_score"] for x in timeline]
        fig, ax = plt.subplots()
        ax.plot(dates, scores, marker='o')
        ax.set_xlabel("Date")
        ax.set_ylabel("Mood score (0-100)")
        ax.set_ylim(0, 100)
        ax.set_title("Mood over time")
        st.pyplot(fig)
