from agents.corrector_agent import run_corrector
from tests.team_c.mock_mcp_tool import get_relevant_chunks
from utils.report_writer import save_report, print_report

def test_corrector():
    report = run_corrector(
        exam_path    = "tests/team_c/mock_data/mock_exam_object.json",
        answers_path = "tests/team_c/mock_data/mock_student_answers.json",
        mcp_tool     = get_relevant_chunks
    )

    # pretty print to terminal
    print_report(report)

    # save to outputs/
    path = save_report(report)
    print(f"  Report saved to: {path}\n")

if __name__ == "__main__":
    test_corrector()