import streamlit as st
from dotenv import load_dotenv

from agents.graph import build_graph

load_dotenv()

st.set_page_config(page_title="Bipartisan Bot", page_icon="\U0001F4F0", layout="wide")

GAZETTE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Spectral:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --paper: #EDEAE2;
    --ink: #1B1B1B;
    --navy: #14213D;
    --gold: #C99A2E;
    --right: #7A2E2E;
    --left: #1F6F6F;
}

.stApp {
    background-color: var(--paper);
    color: var(--ink);
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, .gazette-headline {
    font-family: 'Spectral', serif;
    color: var(--navy);
}

.gazette-mono, .gazette-mono * {
    font-family: 'IBM Plex Mono', monospace !important;
}

.gazette-well {
    border-left: 2px solid var(--navy);
    border-right: 2px solid var(--navy);
    padding: 0 1.5rem;
}

.gazette-section-number {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--gold);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-size: 0.85rem;
}

.side-right {
    border-left: 4px solid var(--right);
    padding-left: 1rem;
}

.side-left {
    border-left: 4px solid var(--left);
    padding-left: 1rem;
}

.gazette-disclaimer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--navy);
    color: var(--paper);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    text-align: center;
    padding: 0.4rem;
    z-index: 999;
}
</style>
"""
st.markdown(GAZETTE_CSS, unsafe_allow_html=True)

EXAMPLE_TOPICS = [
    "India's Uniform Civil Code debate",
    "Agnipath military recruitment scheme",
    "Delimitation of Lok Sabha constituencies",
    "India's new Digital Personal Data Protection Act",
]

st.markdown("<h1>The Bipartisan Gazette</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='gazette-mono'>A structured, fact-grounded debate on Indian public policy</p>",
    unsafe_allow_html=True,
)

topic_input = st.text_input("Topic for debate", placeholder="e.g. India's new labour codes")
preset = st.selectbox("...or pick an example topic", ["(none)"] + EXAMPLE_TOPICS)

topic = topic_input.strip() or (preset if preset != "(none)" else "")

convene = st.button("Convene the Debate", type="primary", disabled=not topic)

if convene:
    status = st.status("Researching…", expanded=True)

    graph = build_graph()
    state = {"topic": topic, "news_context": []}

    from agents.graph import (
        guardrail_node,
        left_opening_node,
        left_rebuttal_node,
        moderator_node,
        research_node,
        right_opening_node,
        right_rebuttal_node,
    )

    state.update(research_node(state))
    status.update(label="Right agent drafting…")
    state.update(right_opening_node(state))
    status.update(label="Left agent drafting…")
    state.update(left_opening_node(state))
    status.update(label="Rebuttals…")
    state.update(right_rebuttal_node(state))
    state.update(left_rebuttal_node(state))
    status.update(label="Moderator synthesizing…")
    state.update(moderator_node(state))
    status.update(label="Safety check…")
    state.update(guardrail_node(state))
    status.update(label="Done", state="complete")

    st.session_state["debate_state"] = state

if "debate_state" in st.session_state:
    state = st.session_state["debate_state"]

    if not state.get("guardrail_passed", True):
        st.error(f"Guardrail flagged this debate: {state.get('guardrail_notes')}")

    st.markdown("<div class='gazette-well'>", unsafe_allow_html=True)

    st.markdown("<p class='gazette-section-number'>I. Opening Statements</p>", unsafe_allow_html=True)
    col_r, col_l = st.columns(2)
    with col_r:
        st.markdown("<div class='side-right'>", unsafe_allow_html=True)
        st.markdown("**Right**")
        st.write(state.get("right_opening", ""))
        st.markdown("</div>", unsafe_allow_html=True)
    with col_l:
        st.markdown("<div class='side-left'>", unsafe_allow_html=True)
        st.markdown("**Left**")
        st.write(state.get("left_opening", ""))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<p class='gazette-section-number'>II. Rebuttals</p>", unsafe_allow_html=True)
    col_r2, col_l2 = st.columns(2)
    with col_r2:
        st.markdown("<div class='side-right'>", unsafe_allow_html=True)
        st.write(state.get("right_rebuttal", ""))
        st.markdown("</div>", unsafe_allow_html=True)
    with col_l2:
        st.markdown("<div class='side-left'>", unsafe_allow_html=True)
        st.write(state.get("left_rebuttal", ""))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<p class='gazette-section-number'>III. The Chair's Summary</p>", unsafe_allow_html=True)
    summary = state.get("moderator_summary") or {}
    st.write(summary.get("topic_summary", ""))

    col_for, col_against, col_common = st.columns(3)
    with col_for:
        st.markdown("**Case For**")
        for item in summary.get("case_for", []):
            st.markdown(f"- {item['point']} _( {item['raised_by']} )_")
    with col_against:
        st.markdown("**Case Against**")
        for item in summary.get("case_against", []):
            st.markdown(f"- {item['point']} _( {item['raised_by']} )_")
    with col_common:
        st.markdown("**Common Ground**")
        for point in summary.get("common_ground", []):
            st.markdown(f"- {point}")

    if summary.get("key_facts"):
        st.markdown("**Key Facts**")
        for fact in summary["key_facts"]:
            st.markdown(f"- {fact}")

    if summary.get("sources"):
        st.markdown("**Sources**")
        st.markdown("<div class='gazette-mono'>", unsafe_allow_html=True)
        for src in summary["sources"]:
            st.markdown(f"- [{src['title']}]({src['url']}) — {src['source']}")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='gazette-disclaimer'>"
    "This tool presents differing viewpoints for educational purposes only "
    "and does not reflect the system's own opinion."
    "</div>",
    unsafe_allow_html=True,
)
