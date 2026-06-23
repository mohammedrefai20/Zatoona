import json
from pathlib import Path
from schemas.feedback_report import FeedbackReport

OUTPUT_DIR = Path("outputs")

def save_report(report: FeedbackReport, filename: str = None) -> Path:
    # saves the feedback report as a json file in outputs/
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename  = filename or f"report_{report.session_id}.json"
    filepath  = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        json.dump(report.model_dump(), f, indent=2)
    return filepath

def print_report(report: FeedbackReport):
    # pretty prints the report to terminal
    total = len(report.results)
    print("\n" + "="*50)
    print(f"  FEEDBACK REPORT — Session: {report.session_id}")
    print("="*50)
    print(f"  Score         : {report.score} / {total}")
    print(f"  Topics Review : {', '.join(report.topics_to_review) if report.topics_to_review else 'None'}")
    print(f"  Encouragement : {report.encouragement}")
    print("-"*50)

    for r in report.results:
        status = "✓  CORRECT" if r.is_correct else "✗  WRONG"
        print(f"\n  [{status}]  {r.question}")
        print(f"  Your answer : {r.student_answer}")
        print(f"  Feedback    : {r.explanation}")

    print("\n" + "="*50 + "\n")