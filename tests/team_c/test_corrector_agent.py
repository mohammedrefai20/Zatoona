from agents.corrector_agent import run_corrector
from utils.report_writer import save_report, print_report

def test_corrector():
    report = run_corrector(
        session_id="test-session-001",
        topics=["ai", "python"]
    )
    print_report(report)
    path = save_report(report)
    print(f"  Report saved to: {path}\n")

if __name__ == "__main__":
    test_corrector()