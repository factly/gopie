import dspy


class EvaluateQueryResponse(dspy.Signature):
    generated_answer: str = dspy.InputField(
        desc=(
            "Comprehensive response object as JSON string containing: "
            "ai_response (text), datasets_used (array), sql_queries_generated (array), "
            "processing_steps (array), visualization_results (array), and metadata (counts)"
        )
    )
    expected_result: str = dspy.InputField(
        desc=(
            "Expected result criteria - either a string description of what should be returned "
            "or a structured object with specific criteria like expected_datasets (only for multi-dataset queries), "
            "sql_query_count, visualization_needed, etc. "
            "Note: For single-dataset queries, dataset identification is not required."
        )
    )
    evaluation_score: float = dspy.OutputField(
        desc=(
            "Numeric evaluation score on 0-10 scale based on how well the response addresses the query. "
            "Consider correctness, relevance, completeness, and quality. "
            "Higher scores indicate better responses. Score can be any value from 0 to 10."
        )
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation for the score - why points were deducted or what was done well"
    )
    summary: str = dspy.OutputField(
        desc="One-line summary of the evaluation result (always required regardless of score)"
    )
