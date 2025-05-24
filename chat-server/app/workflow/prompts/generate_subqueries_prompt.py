def create_assess_query_complexity_prompt(user_input: str) -> str:
    """
    Create a prompt to assess if a user query needs to be broken down into
    subqueries.

    Args:
        user_input: The natural language query from the user

    Returns:
        A formatted prompt string
    """
    return f"""
      User Query: {user_input}

      Analyze the user query and determine if it needs to be broken down into
      sub-queries or simply improved.

      Follow these guidelines:

      1. QUERY ASSESSMENT:
         - Determine if the query can be handled in a single agent cycle
         - Consider complexity, number of distinct data operations, and
           interdependent steps

      2. DECISION CRITERIA:
         - ONLY decide to break down the query if it's genuinely too complex
           for a single operation
         - If the query is straightforward or can be handled in one step,
           DO NOT break it down
         - Consider whether the query requires multiple distinct datasets or
           operations that depend on previous results

      3. EXPLANATION:
         - Provide a very brief explanation (1-2 sentences) of what you
           decided about the query
         - Explain whether it needs to be broken down and why
         - Keep it simple and client-friendly

      RESPONSE FORMAT:
      {{
        "needs_breakdown": true/false,
        "explanation": "Brief explanation of decision"
      }}

      IMPORTANT: Prioritize NOT breaking down queries unless absolutely
      necessary for successful execution.
    """


def create_generate_subqueries_prompt(user_input: str) -> str:
    """
    Create a prompt for breaking down a user query into specific subqueries.

    This should only be called after determining the query needs breakdown.

    Args:
        user_input: The natural language query from the user

    Returns:
        A formatted prompt string
    """
    return f"""
      User Query: {user_input}

      This query has been determined to need breaking down into smaller
      subqueries. Generate effective subqueries following these guidelines:

      BREAKDOWN RULES:
        - Maximum 3 sub-queries allowed
        - Each sub-query should address a distinct aspect of the main question
        - Order sub-queries logically: place data retrieval/analysis queries
          first, followed by queries that depend on previous results
        - Make each sub-query clear, specific, and focused on a single task

      RESPONSE FORMAT:
      {{
        "subqueries": ["subquery1", "subquery2", "subquery3"]
      }}

      IMPORTANT: Ensure each subquery is clear, specific.
    """
