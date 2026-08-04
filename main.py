"""
CLI runner: processes every ticket in data/sample_tickets.json through the
triage agent and prints a readable result for each. This is the actual
end-to-end proof the system works, not just its individual pieces.

Usage:
    python main.py                       # runs data/sample_tickets.json
    python main.py path/to/other.json    # runs a different ticket file
"""

import json
import sys
from pathlib import Path

from agent import triage_ticket

DEFAULT_TICKETS_PATH = Path(__file__).parent / "data" / "sample_tickets.json"


def load_tickets(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_ticket(ticket: dict, index: int, total: int) -> str:
    """Runs one ticket through the agent, prints the result, and returns
    the action taken ('resolved' or 'escalated') so main() can tally a
    summary at the end."""
    print(f"\n{'=' * 70}")
    print(
        f"[{index}/{total}] {ticket.get('id', '?')}  "
        f"({ticket.get('channel', '?')})  from {ticket.get('customer_name', '?')}"
    )
    print(f"{'-' * 70}")
    print(f"Ticket: {ticket['message']}\n")

    # Deliberately only ticket['message'] is sent to the agent - fields
    # like note_for_us are for our own reading, never sent to Claude.
    result = triage_ticket(ticket["message"])

    if result.action == "resolved":
        print(f"-> RESOLVED  [{result.category}]")
        print(f"   Reply:   {result.reply}")
        cited = ", ".join(result.cited_docs) if result.cited_docs else "(none cited)"
        print(f"   Sources: {cited}")
    else:
        print(f"-> ESCALATED  [{result.category}]")
        print(f"   Reason:  {result.escalation_reason}")

    return result.action


def main():
    tickets_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TICKETS_PATH
    tickets = load_tickets(tickets_path)

    print(f"Running {len(tickets)} ticket(s) through the triage agent...")

    resolved = escalated = errors = 0
    for i, ticket in enumerate(tickets, start=1):
        try:
            action = run_ticket(ticket, i, len(tickets))
        except Exception as e:
            print(f"-> ERROR: {e}")
            errors += 1
            continue
        if action == "resolved":
            resolved += 1
        else:
            escalated += 1

    print(f"\n{'=' * 70}")
    summary = f"Done. {resolved} resolved, {escalated} escalated"
    if errors:
        summary += f", {errors} errored"
    print(f"{summary}, {len(tickets)} total.")


if __name__ == "__main__":
    main()
