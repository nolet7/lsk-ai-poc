"""
FILE PURPOSE: Reviewer Agent

This file performs quality checks on the generated report. It verifies that
required report sections exist and that the report is long enough for
executive review.

Flow:
Writer -> Reviewer -> Save Report when approved
                  -> Writer when rejected
"""


def reviewer_agent(state: dict) -> dict:
    """Review the draft report and record an approval decision."""

    # Increment before routing so rejected reports cannot loop forever.
    state["review_attempts"] = state.get("review_attempts", 0) + 1

    # Read the draft produced by the Writer Agent.
    report = state["draft_report"]

    # Create a list for quality-review messages.
    notes: list[str] = []

    # Start with an approved status.
    # Failed checks will change this to False.
    approved = True

    # Define all sections required in the final report.
    required_sections = [
        "Question",
        "Execution Plan",
        "Retrieved Enterprise Context",
        "Analysis",
        "Recommendations",
        "Conclusion",
    ]

    # Check every required report section.
    for section in required_sections:

        # Reject the report when a required section is missing.
        if section not in report:
            notes.append(f"Missing section: {section}")
            approved = False

    # Reject reports that are too short for executive review.
    if len(report) < 500:
        notes.append("Report is too short for executive review.")
        approved = False

    # Add a success message when all checks pass.
    if approved:
        notes.append(
            "Approved. Report is complete and portfolio-ready."
        )

        # Promote the approved draft to final report content.
        state["final_report"] = report

    if not approved and state["review_attempts"] >= 3:
        notes.append("Maximum review attempts reached; no report was published.")

    # Store all review notes as one newline-separated string.
    state["review_notes"] = "\n".join(notes)

    # Store the Boolean decision used by the graph router.
    state["approved"] = approved

    # Return the updated state.
    # The original code omitted this return statement.
    return state
