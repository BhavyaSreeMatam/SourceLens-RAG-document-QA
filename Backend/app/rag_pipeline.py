from openai import OpenAI

from app.config import OPENAI_API_KEY, CHAT_MODEL
from app.embeddings import create_embedding

client = OpenAI(api_key=OPENAI_API_KEY)


def build_context(retrieved_chunks):
    context_blocks = []

    for index, chunk in enumerate(retrieved_chunks):
        source_number = index + 1

        block = f"""
[Source {source_number}]
Filename: {chunk["filename"]}
Page: {chunk["page"]}
Chunk ID: {chunk["chunk_id"]}

{chunk["text"]}
"""
        context_blocks.append(block)

    return "\n\n".join(context_blocks)


def generate_answer(question: str, retrieved_chunks):
    context = build_context(retrieved_chunks)

    prompt = f"""
You are SourceLens, a document question-answering assistant.

Rules:
1. Answer using only the provided context.
2. If the answer is not in the context, say:
   "I could not find this information in the uploaded documents."
3. Cite sources in your answer using [Source 1], [Source 2], etc.
4. Keep the answer clear and concise.

Context:
{context}

Question:
{question}
"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You answer questions using only the retrieved document context."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


def answer_question(question: str, vector_store, top_k: int = 5):
    question_embedding = create_embedding(question)

    retrieved_chunks = vector_store.search(
        query_vector=question_embedding,
        top_k=top_k
    )

    if not retrieved_chunks:
        return {
            "answer": "No documents have been indexed yet. Please upload a PDF first.",
            "sources": []
        }

    answer = generate_answer(question, retrieved_chunks)

    sources = []

    for index, chunk in enumerate(retrieved_chunks):
        sources.append({
            "source_number": index + 1,
            "filename": chunk.get("filename", ""),
            "page": chunk.get("page", ""),
            "chunk_id": chunk.get("chunk_id", ""),
            "text_preview": chunk.get("text", "")[:350],
            "distance": chunk.get("distance", 0)
        })

    return {
        "answer": answer,
        "sources": sources
    }