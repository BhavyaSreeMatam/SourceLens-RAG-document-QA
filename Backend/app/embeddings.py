from openai import OpenAI

from app.config import OPENAI_API_KEY, EMBEDDING_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def create_embedding(text: str):
    """
    Convert text into a vector embedding using OpenAI.
    """
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding