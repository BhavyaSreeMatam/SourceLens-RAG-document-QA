import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import UPLOAD_DIR, INDEX_DIR
from app.pdf_loader import extract_pdf_text
from app.chunker import chunk_text
from app.embeddings import create_embedding
from app.vector_store import VectorStore
from app.schemas import AskRequest, EvaluateRequest
from app.evaluation import evaluate_answer
from app.rag_pipeline import answer_question as run_rag_pipeline

app = FastAPI(title="SourceLens RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

INDEX_PATH = os.path.join(INDEX_DIR, "faiss.index")
METADATA_PATH = os.path.join(INDEX_DIR, "metadata.pkl")

vector_store = VectorStore()

loaded_existing_index = vector_store.load(INDEX_PATH, METADATA_PATH)

if loaded_existing_index:
    print(f"Loaded existing FAISS index with {vector_store.count()} vectors.")
else:
    print("No existing FAISS index found. Starting with empty vector store.")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "SourceLens backend is running",
        "vectors_indexed": vector_store.count()
    }


@app.get("/documents")
def list_documents():
    return {
        "documents": vector_store.list_documents(),
        "vectors_indexed": vector_store.count()
    }


@app.delete("/documents/{filename}")
def delete_document(filename: str):
    deleted, removed_chunks = vector_store.delete_document(filename)

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")

    uploaded_file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(uploaded_file_path):
        try:
            os.remove(uploaded_file_path)
        except Exception:
            pass

    vector_store.save(INDEX_PATH, METADATA_PATH)

    return {
        "message": f"Deleted document: {filename}",
        "removed_chunks": removed_chunks,
        "vectors_indexed_total": vector_store.count()
    }


@app.delete("/documents")
def delete_all_documents():
    vector_store.clear_all()
    vector_store.save(INDEX_PATH, METADATA_PATH)

    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    return {
        "message": "All indexed documents deleted.",
        "vectors_indexed_total": vector_store.count()
    }


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"File saving failed: {str(e)}"
        )

    try:
        pages = extract_pdf_text(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF text extraction failed: {str(e)}"
        )

    chunks = chunk_text(pages)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from this PDF."
        )

    vectors = []
    metadata = []

    for chunk in chunks:
        try:
            embedding = create_embedding(chunk["text"])
            vectors.append(embedding)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Embedding creation failed: {str(e)}"
            )

        metadata.append({
            "filename": file.filename,
            "page": chunk["page"],
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "embedding": embedding
        })

    try:
        vector_store.add_vectors(vectors, metadata)
        vector_store.save(INDEX_PATH, METADATA_PATH)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"FAISS indexing or saving failed: {str(e)}"
        )

    return {
        "message": "PDF uploaded, chunked, embedded, indexed, and saved successfully",
        "filename": file.filename,
        "pages": len(pages),
        "chunks_created": len(chunks),
        "vectors_indexed_total": vector_store.count()
    }


@app.post("/ask")
def ask_question_endpoint(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = run_rag_pipeline(
            question=request.question,
            vector_store=vector_store,
            top_k=request.top_k
        )

        if result is None:
            raise HTTPException(
                status_code=500,
                detail="RAG pipeline returned None."
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question answering failed: {str(e)}"
        )
    
@app.post("/evaluate")
def evaluate_rag_answer(request: EvaluateRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not request.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    if not request.contexts:
        raise HTTPException(status_code=400, detail="Contexts cannot be empty.")

    try:
        result = evaluate_answer(
            question=request.question,
            answer=request.answer,
            contexts=request.contexts
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )

    return result