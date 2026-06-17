import json
from openai import OpenAI

from app.config import OPENAI_API_KEY, CHAT_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def evaluate_answer(question: str, answer: str, contexts: list[str]):
    """
    Uses an LLM judge to score the RAG answer.

    Scores:
    - faithfulness: Is the answer supported by the sources?
    - answer_relevance: Does the answer address the question?
    - context_usefulness: Were the retrieved sources useful?
    """

    context_text = "\n\n".join(
        [f"[Context {i + 1}]\n{context}" for i, context in enumerate(contexts)]
    )

    prompt = f"""
You are a strict evaluator for a Retrieval-Augmented Generation system.

Your job is to evaluate whether the Generated Answer is supported by the Retrieved Contexts.

Question:
{question}

Generated Answer:
{answer}

Retrieved Contexts:
{context_text}

Return ONLY valid JSON with this exact structure:
{{
  "faithfulness": 0.0,
  "answer_relevance": 0.0,
  "context_usefulness": 0.0,
  "explanation": "brief explanation"
}}

Scoring rules:
- faithfulness: 1.0 means every claim is supported by the contexts. 0.0 means unsupported or contradicted.
- answer_relevance: 1.0 means the answer directly answers the question. 0.0 means irrelevant.
- context_usefulness: 1.0 means the retrieved contexts are highly useful. 0.0 means not useful.
- Scores must be between 0 and 1.
"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You evaluate RAG answers and return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    raw_output = response.choices[0].message.content

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "context_usefulness": 0.0,
            "explanation": "Evaluation failed because the model did not return valid JSON."
        }

    return parsed