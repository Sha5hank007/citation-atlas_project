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


def filter_relevant_papers(llm, topic, papers, max_papers=40):

    # ── STEP 1: strong citation pre-filter ───────────────
    papers = sorted(papers, key=lambda x: x["citations"], reverse=True)[:60]

    # ── STEP 2: LLM relevance scoring (NOT hard filtering) ─
    lines = []
    for p in papers:
        lines.append(
            f"{p['id']} | {p['title']} | citations: {p['citations']}"
        )

    prompt = f"""
You are ranking research papers for relevance.

Topic:
{topic}

Score each paper from 0 to 10 based on:
- direct relevance
- foundational importance
- influence on this topic

IMPORTANT:
- foundational papers (e.g. transformers, diffusion) MUST get high score
- datasets or unrelated domains must get low score

Return format:
id | score

Papers:
{chr(10).join(lines)}
"""

    response = llm.generate(prompt)

    scores = {}
    for line in response.split("\n"):
        parts = line.split("|")
        if len(parts) >= 2:
            pid = parts[0].strip()
            try:
                score = float(parts[1].strip())
                scores[pid] = score
            except:
                continue

    # ── STEP 3: combine citation + LLM score ─────────────
    def final_score(p):
        llm_score = scores.get(p["id"], 0)
        citation_score = min(p["citations"] / 1000, 10)  # normalize
        return llm_score * 0.7 + citation_score * 0.3

    ranked = sorted(papers, key=final_score, reverse=True)

    # ── STEP 4: guarantee foundational papers ────────────
    top_cited = sorted(papers, key=lambda x: x["citations"], reverse=True)[:5]

    final = ranked[:max_papers]

    ids = {p["id"] for p in final}
    for p in top_cited:
        if p["id"] not in ids:
            final.append(p)

    return final[:max_papers]