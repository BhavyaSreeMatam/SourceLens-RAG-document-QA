def chunk_text(pages, chunk_size=900, overlap=150):
    """
    Split PDF page text into smaller overlapping chunks.

    pages example:
    [
        {"page": 1, "text": "long page text..."}
    ]

    returns:
    [
        {"chunk_id": 0, "page": 1, "text": "chunk text..."}
    ]
    """
    chunks = []
    chunk_id = 0

    for page in pages:
        page_number = page["page"]
        text = page["text"]

        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page_number,
                    "text": chunk
                })
                chunk_id += 1

            start += chunk_size - overlap

    return chunks