from agents.corrector_agent import run_corrector
from mcp_server.mcp_client import get_relevant_chunks
from utils.report_writer import save_report, print_report

def test_corrector():
    # no paths needed anymore — loaders handle everything
    report = run_corrector(mcp_tool=get_relevant_chunks)

    print_report(report)
    path = save_report(report)
    print(f"  Report saved to: {path}\n")

if __name__ == "__main__":
    test_corrector()