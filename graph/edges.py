from typing import Literal

from langgraph.graph import END

from graph.state import ExamState


def route_after_validate(state: ExamState) -> Literal["generate", "__end__"]:
    validation = state.get("validation")
    if validation is None:
        return END

    if validation.approved:
        return END

    if state["iteration"] < state["max_iterations"]:
        return "generate"

    return END
