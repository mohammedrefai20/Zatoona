import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


import json
import streamlit as st
from pathlib import Path
from agents.corrector_agent import run_corrector
from agents.exam_loader import load_exam
from mcp_server.mcp_client import get_chunk_by_id
from utils.report_writer import save_report

# ── page config ─────────────────────────────────────────────
st.set_page_config(
    page_title = "Classroom Exam Agent",
    page_icon  = "📚",
    layout     = "centered"
)

# ── session state init ───────────────────────────────────────
# keeps data alive between page interactions
if "page"    not in st.session_state: st.session_state.page    = "exam"
if "exam"    not in st.session_state: st.session_state.exam    = None
if "answers" not in st.session_state: st.session_state.answers = {}
if "report"  not in st.session_state: st.session_state.report  = None

# ── load exam once ───────────────────────────────────────────
if st.session_state.exam is None:
    st.session_state.exam = load_exam()

exam = st.session_state.exam

# ════════════════════════════════════════════════════════════
# PAGE 1 — EXAM
# ════════════════════════════════════════════════════════════
if st.session_state.page == "exam":

    st.title("📚 Classroom Exam Agent")
    st.markdown(f"**Session:** `{exam.session_id}`")
    st.markdown(f"**Topics covered:** {', '.join(exam.topics)}")
    st.divider()

    st.subheader("Answer the following questions")
    st.caption("Fill in all answers before submitting.")

    answers = {}

    for i, question in enumerate(exam.questions, 1):
        st.markdown(f"**Q{i}. {question.question}**")
        st.caption(f"Topic: {question.topic}")
        answer = st.text_input(
            label      = f"Your answer for Q{i}",
            key        = f"answer_{question.question_id}",
            label_visibility = "collapsed",
            placeholder= "Type your answer here..."
        )
        answers[question.question_id] = answer
        st.divider()

    if st.button("Submit Exam", type="primary", use_container_width=True):

        # check all answers are filled
        if any(a.strip() == "" for a in answers.values()):
            st.warning("Please answer all questions before submitting.")
        else:
            # build answers dict in the format corrector expects
            st.session_state.answers = {
                "session_id": exam.session_id,
                "answers": [
                    {"question_id": qid, "student_answer": ans}
                    for qid, ans in answers.items()
                ]
            }
            st.session_state.page = "loading"
            st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE 2 — LOADING (grading in progress)
# ════════════════════════════════════════════════════════════
elif st.session_state.page == "loading":

    st.title("📚 Classroom Exam Agent")
    st.divider()

    with st.spinner("Grading your exam... please wait"):
        report = run_corrector(
            mcp_tool = get_chunk_by_id,
            exam     = st.session_state.exam,
            answers  = st.session_state.answers
        )
        st.session_state.report = report
        save_report(report)

    st.session_state.page = "report"
    st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE 3 — FEEDBACK REPORT
# ════════════════════════════════════════════════════════════
elif st.session_state.page == "report":

    report = st.session_state.report
    total  = len(report.results)

    st.title("📋 Your Feedback Report")
    st.markdown(f"**Session:** `{report.session_id}`")
    st.divider()

    # score summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Score", f"{report.score} / {total}")
    with col2:
        percentage = int((report.score / total) * 100)
        st.metric("Percentage", f"{percentage}%")

    # progress bar
    st.progress(report.score / total)
    st.divider()

    # encouragement
    st.info(f"💬 {report.encouragement}")

    # topics to review
    if report.topics_to_review:
        st.warning(f"📖 Topics to review: {', '.join(report.topics_to_review)}")
    else:
        st.success("🎉 Great job — no topics need review!")

    st.divider()

    # per question results
    st.subheader("Question by Question")

    for i, result in enumerate(report.results, 1):
        if result.is_correct:
            with st.expander(f"✅ Q{i}. {result.question}"):
                st.markdown(f"**Your answer:** {result.student_answer}")
                st.success(f"**Feedback:** {result.explanation}")
        else:
            with st.expander(f"❌ Q{i}. {result.question}", expanded=True):
                st.markdown(f"**Your answer:** {result.student_answer}")
                st.error(f"**Feedback:** {result.explanation}")
                st.caption(f"📄 From your notes: {result.source_chunk}")

    st.divider()

    # restart button
    if st.button("Start New Exam", use_container_width=True):
        for key in ["page", "exam", "answers", "report"]:
            del st.session_state[key]
        st.rerun()