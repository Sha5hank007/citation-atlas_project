def expand_query(llm, topic):

    prompt = f"""
Generate 5 simple academic search queries for the topic below.

Rules:
- Use only plain keywords
- Do NOT use quotes
- Do NOT use AND/OR
- Do NOT use parentheses

Topic:
{topic}

Return one query per line.
"""

    response = llm.generate(prompt)

    queries = []

    for q in response.split("\n"):

        q = q.strip()

        if q:
            queries.append(q)

    return queries