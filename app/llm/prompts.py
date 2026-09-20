SYSTEM_EDITORIAL_PROMPT = """You are an expert executive news editor for a high-end financial and technology daily newspaper.

Strict Financial Editorial Principles:
1. NEVER invent facts, stock prices, or financial figures.
2. Clearly distinguish reported facts from speculation or market commentary.
3. Preserve exact numbers, dates, rates, and corporate entities.
4. DO NOT provide investment recommendations or advice (never tell readers to buy/sell).
5. Avoid sensationalism, clickbait, and unnecessary verbosity.
6. Always stick strictly to the provided source text.
"""

ARTICLE_SUMMARIZE_PROMPT = """Summarize the following news article for a high-level executive daily brief:

Title: {title}
Source: {source}
Publication Time: {published_at}
Content/Snippet: {content}

Return JSON with:
{{
  "summary": "2-4 crisp sentences explaining what happened based ONLY on the text.",
  "why_it_matters": "1-3 sentences highlighting the broader market, economic, or strategic relevance.",
  "topics": ["topic1", "topic2"]
}}
"""

STORY_SYNTHESIS_PROMPT = """Multiple articles are reporting on the same major event. Synthesize them into a single definitive story report:

Articles:
{articles_text}

Return JSON with:
{{
  "headline": "A clear, compelling newspaper headline.",
  "summary": "2-4 sentence concise summary of the core event.",
  "why_it_matters": "1-3 sentence explanation of economic/business significance.",
  "category": "One of [top_stories, india, markets, companies, technology, global]"
}}
"""

GOLD_SILVER_DRIVER_PROMPT = """Based on today's economic headlines and market updates:
{headlines_summary}

Explain why Gold and Silver prices moved today.
Focus on USD strength, Treasury yields, Fed/RBI policy expectations, inflation, or geopolitical demand.

Return JSON with:
{{
  "gold_driver": "2-3 crisp sentences explaining primary drivers behind today's gold price action.",
  "silver_driver": "1-2 crisp sentences explaining silver price drivers."
}}
"""

CONNECT_DOTS_PROMPT = """Analyze today's major news developments and identify 1-2 causal chain relationships between events (e.g. US Yields ↑ -> Dollar strengthens -> Gold & Emerging Market currencies face pressure -> Foreign capital flows change).

Headlines:
{headlines_summary}

Return JSON with:
{{
  "connections": [
    {{
      "title": "Short descriptive title of connection",
      "premise": "1-2 sentences stating the primary trigger event.",
      "chain_steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
      "why_matters": "2-3 sentences explaining why this causal relationship matters to investors."
    }}
  ]
}}
"""

FINANCE_CONCEPT_PROMPT = """The selected Finance Concept of the Day is: {concept_title}
Base Concept Explanation: {base_explanation}
Numerical Example: {numerical_example}

Today's News Headlines:
{headlines_summary}

Tie this concept directly to today's news headlines.

Return JSON with:
{{
  "concept": "{concept_title}",
  "explanation": "100-200 words plain language educational explanation incorporating how it works.",
  "why_relevant_today": "2-3 sentences tying it directly to today's headline developments.",
  "numerical_example": "{numerical_example}"
}}
"""
