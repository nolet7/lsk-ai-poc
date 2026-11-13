"""
FILE PURPOSE: Command-Line Demo Runner

This file runs the complete Production AI Platform workflow without starting
the FastAPI web service.

It performs the following steps:

1. Ingest enterprise documents into ChromaDB.
2. Submit a sample business question to the LangGraph workflow.
3. Run the Planner, Researcher, Analyst, Writer, Reviewer, and Save Report agents.
4. Evaluate the completed workflow output.
5. Print the final report path, reviewer notes, and evaluation result.

Use this file for:

- Local development testing
- Portfolio demonstrations
- End-to-end workflow validation
- Confirming that RAG, agents, evaluation, and report saving work together

Execution flow:

run_demo.py
    -> ingest_documents()
    -> run_platform(question)
    -> evaluate_output(result)
    -> print workflow summary
"""

# Import the function that loads enterprise text into ChromaDB.
from rag.ingest import ingest_documents

# Import the function that runs the complete LangGraph multi-agent workflow.
from agents.graph import run_platform

# Import the function that evaluates the completed platform output.
from evaluation.evaluator import evaluate_output


def main() -> None:
    """
    Run the complete local Production AI Platform demonstration.

    The function performs ingestion, agent execution, evaluation, and
    terminal reporting in sequence.
    """

    # Define the sample enterprise AI architecture question.
    # Replace this value with another question to test a different scenario.
    question = (
        "How should an enterprise deploy governed AI agents "
        "with RAG, monitoring, and approval workflows?"
    )

    # Display the first workflow stage in the terminal.
    print("Ingesting documents...")

    # Load text documents, create embeddings, and upsert them into ChromaDB.
    ingest_result = ingest_documents()

    # Print the number of document chunks indexed.
    print("Ingestion result:", ingest_result)

    # Display the start of the multi-agent workflow.
    print("\nRunning production AI platform...")

    # Submit the sample question to the LangGraph workflow.
    # The returned state includes the plan, research context, analysis,
    # report, reviewer notes, approval status, and saved report path.
    result = run_platform(question)

    # Display the evaluation stage.
    print("\nEvaluating output...")

    # Run deterministic quality checks against the completed workflow state.
    evaluation = evaluate_output(result)

    # Print a clear completion heading.
    print("\nProduction AI Platform Complete")
    print("-------------------------------")

    # Echo the question processed by the agents.
    print("Question:", result["question"])

    # Show where the approved Markdown report was saved.
    print("Report saved to:", result["report_path"])

    # Display the Reviewer Agent's approval or correction notes.
    print("Review notes:", result["review_notes"])

    # Display the evaluation scores and pass/fail result.
    print("Evaluation:", evaluation)


# Execute main() only when this file is run directly.
# Importing run_demo.py from another module will not start the demo.
if __name__ == "__main__":
    main()
