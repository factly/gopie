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

Follow these STRICT guidelines:

1. QUERY ASSESSMENT:
   - Determine if the query can be handled in a single agent cycle
   - Consider complexity, number of distinct data operations, and
     interdependent steps
   - Be EXTREMELY conservative about breaking down queries

2. DECISION CRITERIA:
   - ONLY decide to break down the query if it's genuinely too complex
     for a single operation
   - Default position should be NOT to break down queries unless
     absolutely necessary
   - Break down ONLY if the query explicitly requires multiple unrelated
     tasks or operations
   - Simple queries about a single topic, even if they need multiple
     data points, should NOT be broken down
   - If unsure, DO NOT break down the query

3. COMPLEXITY INDICATORS (requiring breakdown):
   - Multiple unrelated questions in a single query
   - Explicitly requested multi-step analysis with dependencies
   - Questions requiring data from completely different domains
   - Analysis that requires results from previous operations

4. EXPLANATION:
   - Provide a very brief explanation (1-2 sentences) of what you
     decided about the query
   - Explain whether it needs to be broken down and why
   - Keep it simple and client-friendly

RESPONSE FORMAT:
{{
  "needs_breakdown": true/false,
  "explanation": "Brief explanation of decision"
}}

IMPORTANT: The default position is to NOT break down queries.
           Only do so when absolutely necessary.
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
subqueries. Generate effective subqueries following these STRICT guidelines:

BREAKDOWN RULES:
  - Generate 2-3 sub-queries based on actual complexity (never just 1)
  - Each sub-query must be in natural language only - NEVER generate SQL
  - Each sub-query should address a distinct aspect of the main question
  - Each sub-query should be self-contained and not assume knowledge
    of system architecture or data organization
  - Make each sub-query clear, specific, and focused on a single task
  - Ensure subqueries directly relate to the user's original intent
  - Focus on WHAT information is needed, not HOW to retrieve it

STRICT PROHIBITIONS:
  - NEVER generate SQL code or database queries
  - NEVER include implementation details about HOW to get information
  - NEVER hallucinate additional context or requirements
  - NEVER break down the query into process steps
    (like "first search for X, then analyze Y")
  - NEVER generate just 1 subquery
  - NEVER generate step-by-step information retrieval subqueries
    without knowing the actual system structure or data organization
  - NEVER create subqueries like "first get information about X"
    followed by "then get information about Y" unless you have
    explicit context about how this information is stored or organized
  - NEVER assume sequential data retrieval patterns without
    understanding the underlying data architecture
  - NEVER generate subqueries that imply a specific order of data
    collection without context about how the system is organized
  - Focus on generating conceptually distinct questions, not
    procedural steps for information gathering

RESPONSE FORMAT:
{{
  "subqueries": ["subquery1", "subquery2", "subquery3"]
}}

IMPORTANT: Ensure each subquery is a natural language question
           that a human would ask.
"""
