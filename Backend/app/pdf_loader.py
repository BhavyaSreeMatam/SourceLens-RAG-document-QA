from pypdf import PdfReader


def extract_pdf_text(file_path: str):
    """
    Extract text from each page of a PDF.

    Returns:
        [
            {"page": 1, "text": "..."},
            {"page": 2, "text": "..."}
        ]
    """
    reader = PdfReader(file_path)
    pages = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        pages.append({
            "page": index + 1,
            "text": text
        })

    return pages