from langgraph.graph import END, StateGraph

from config.settings import MAX_VALIDATION_ITERATIONS
from graph.edges import route_after_validate
from graph.nodes import fetch_chunks, generate, validate
from graph.state import ExamState
from schemas.exam_object import ExamObject


class ExamPipelineError(Exception):
    """Raised when exam validation fails after max iterations."""


def build_exam_graph():
    graph = StateGraph(ExamState)

    graph.add_node("fetch_chunks", fetch_chunks)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)

    graph.set_entry_point("fetch_chunks")

    graph.add_edge("fetch_chunks", "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", route_after_validate)

    return graph.compile()


def run_exam_pipeline(session_id: str, topics: list[str]) -> ExamObject:
    """Run the full exam creation pipeline and return a validated ExamObject."""
    app = build_exam_graph()

    initial_state: ExamState = {
        "session_id": session_id,
        "topics": topics,
        "chunks": [],
        "exam": None,
        "validation": None,
        "iteration": 0,
        "max_iterations": MAX_VALIDATION_ITERATIONS,
    }

    final_state = app.invoke(initial_state)
    exam = final_state.get("exam")
    validation = final_state.get("validation")

    if exam is None:
        raise ExamPipelineError("Pipeline finished without producing an exam.")

    if exam.status == "validated":
        return exam

    raise ExamPipelineError(
        f"Exam validation failed after {final_state['iteration']} attempt(s). "
        f"Feedback: {validation.feedback if validation else 'unknown'}"
    )


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run Team B exam creation pipeline")
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument(
        "--topics",
        required=True,
        help="Comma-separated list of topics",
    )
    args = parser.parse_args()

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    exam = run_exam_pipeline(session_id=args.session, topics=topics)
    print(exam.model_dump_json(indent=2))
