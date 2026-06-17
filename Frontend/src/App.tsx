import { useEffect, useState } from "react";
import {
  uploadPDF,
  askQuestion,
  getDocuments,
  deleteDocument,
  deleteAllDocuments,
  evaluateAnswer,
} from "./api";
import "./App.css";

type Source = {
  source_number: number;
  filename: string;
  page: number;
  chunk_id: number;
  text_preview: string;
  distance: number;
};

type Evaluation = {
  faithfulness: number;
  answer_relevance: number;
  context_usefulness: number;
  explanation: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  questionForEvaluation?: string;
  evaluation?: Evaluation;
  isEvaluating?: boolean;
};

type DocumentInfo = {
  filename: string;
  chunks: number;
  pages: number;
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [vectorsIndexed, setVectorsIndexed] = useState(0);

  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);

  async function loadDocuments() {
    try {
      setIsLoadingDocuments(true);
      const result = await getDocuments();
      setDocuments(result.documents || []);
      setVectorsIndexed(result.vectors_indexed || 0);
    } catch (error) {
      console.error("Failed to load documents:", error);
      setUploadStatus("Could not load indexed documents.");
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleUpload() {
    if (!file) {
      setUploadStatus("Please select a PDF first.");
      return;
    }

    try {
      setIsUploading(true);
      setUploadStatus("Uploading and indexing PDF...");

      const result = await uploadPDF(file);

      setUploadStatus(
        `Uploaded ${result.filename}. Created ${result.chunks_created} chunks.`
      );

      await loadDocuments();
    } catch (error) {
      console.error(error);
      setUploadStatus("Upload failed. Make sure the backend is running.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAsk() {
  if (!question.trim()) return;

  if (documents.length === 0) {
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "Please upload and index at least one PDF before asking questions.",
      },
    ]);
    return;
  }

  const userQuestion = question;
  setQuestion("");

  setMessages((prev) => [
    ...prev,
    { role: "user", content: userQuestion },
  ]);

  try {
    setIsAsking(true);

    const result = await askQuestion(userQuestion, 3);

    console.log("Ask result from backend:", result);

    if (!result || typeof result !== "object") {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "No valid response was returned from the backend.",
          sources: [],
          questionForEvaluation: userQuestion,
        },
      ]);
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: result.answer || "No answer returned from backend.",
        sources: Array.isArray(result.sources) ? result.sources : [],
        questionForEvaluation: userQuestion,
      },
    ]);
  } catch (error) {
    console.error("Question asking failed:", error);

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content:
          "Something went wrong. Make sure the backend is running and at least one PDF is indexed.",
        sources: [],
        questionForEvaluation: userQuestion,
      },
    ]);
  } finally {
    setIsAsking(false);
  }
}

  async function handleEvaluate(messageIndex: number) {
    const message = messages[messageIndex];

    if (!message.questionForEvaluation || !message.sources) {
      return;
    }

    const contexts = message.sources.map((source) => source.text_preview);

    setMessages((prev) =>
      prev.map((msg, index) =>
        index === messageIndex ? { ...msg, isEvaluating: true } : msg
      )
    );

    try {
      const result = await evaluateAnswer(
        message.questionForEvaluation,
        message.content,
        contexts
      );

      setMessages((prev) =>
        prev.map((msg, index) =>
          index === messageIndex
            ? { ...msg, evaluation: result, isEvaluating: false }
            : msg
        )
      );
    } catch (error) {
      console.error(error);

      setMessages((prev) =>
        prev.map((msg, index) =>
          index === messageIndex
            ? {
                ...msg,
                isEvaluating: false,
                evaluation: {
                  faithfulness: 0,
                  answer_relevance: 0,
                  context_usefulness: 0,
                  explanation: "Evaluation failed. Check backend terminal.",
                },
              }
            : msg
        )
      );
    }
  }

  async function handleDeleteDocument(filename: string) {
    const confirmed = window.confirm(`Delete "${filename}" from the index?`);

    if (!confirmed) return;

    try {
      await deleteDocument(filename);
      setUploadStatus(`Deleted ${filename}.`);
      await loadDocuments();
    } catch (error) {
      console.error(error);
      setUploadStatus("Could not delete document.");
    }
  }

  async function handleDeleteAllDocuments() {
    const confirmed = window.confirm(
      "Delete all indexed PDFs? This cannot be undone."
    );

    if (!confirmed) return;

    try {
      await deleteAllDocuments();
      setMessages([]);
      setUploadStatus("Deleted all indexed documents.");
      await loadDocuments();
    } catch (error) {
      console.error(error);
      setUploadStatus("Could not delete all documents.");
    }
  }

  function clearChat() {
    setMessages([]);
  }

  function formatScore(score: number) {
    return score.toFixed(2);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <h1>SourceLens</h1>
          <p>Upload PDFs and ask source-grounded questions.</p>
        </div>

        <div className="card">
          <div className="section-header">
            <h2>Upload PDF</h2>
          </div>

          <p className="helper-text">
            Upload a PDF. The backend extracts text, chunks it, embeds it, and
            stores it in FAISS.
          </p>

          <input
            className="file-input"
            type="file"
            accept="application/pdf"
            onChange={(event) => {
              const selectedFile = event.target.files?.[0] || null;
              setFile(selectedFile);
            }}
          />

          {file && <p className="selected-file">Selected: {file.name}</p>}

          <button
            className="button primary"
            onClick={handleUpload}
            disabled={isUploading}
          >
            {isUploading ? "Uploading..." : "Upload and Index"}
          </button>

          {uploadStatus && <p className="status-message">{uploadStatus}</p>}
        </div>

        <div className="card">
          <div className="section-header">
            <h2>Indexed Documents</h2>
            <button
              className="button secondary small"
              onClick={loadDocuments}
              disabled={isLoadingDocuments}
            >
              {isLoadingDocuments ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          <p className="helper-text">Total vectors indexed: {vectorsIndexed}</p>

          <div className="doc-actions">
            <button
              className="button danger small"
              onClick={handleDeleteAllDocuments}
              disabled={documents.length === 0}
            >
              Delete All
            </button>
          </div>

          {documents.length === 0 ? (
            <p className="empty-state">No indexed PDFs yet.</p>
          ) : (
            <div className="document-list">
              {documents.map((doc) => (
                <div key={doc.filename} className="document-item">
                  <div className="document-info">
                    <p className="document-name">{doc.filename}</p>
                    <p className="document-meta">
                      {doc.pages} pages · {doc.chunks} chunks
                    </p>
                  </div>

                  <button
                    className="button secondary small"
                    onClick={() => handleDeleteDocument(doc.filename)}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      <main className="chat-panel">
        <div className="chat-panel-header">
          <div>
            <h2>Chat with your documents</h2>
            <p className="helper-text">
              Ask questions and get answers grounded in the indexed PDFs.
            </p>
          </div>

          <button className="button secondary small" onClick={clearChat}>
            Clear Chat
          </button>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-placeholder">
              <p>No messages yet.</p>
              <span>Upload a PDF and ask your first question.</span>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`message-row ${
                  message.role === "user" ? "user-row" : "assistant-row"
                }`}
              >
                <div
                  className={`message-bubble ${
                    message.role === "user" ? "user-bubble" : "assistant-bubble"
                  }`}
                >
                  <p>{message.content}</p>

                  {message.sources && message.sources.length > 0 && (
                    <div className="sources-block">
                      <h4>Sources</h4>
                      {message.sources.map((source) => (
                        <div key={source.source_number} className="source-card">
                          <strong>
                            Source {source.source_number}: {source.filename || "Unknown file"}, page{" "}
                            {source.page || "?"}
                          </strong>
                          <p>{source.text_preview || "No preview available."}...</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                    <div className="evaluation-actions">
                      <button
                        className="button secondary small"
                        onClick={() => handleEvaluate(index)}
                        disabled={message.isEvaluating}
                      >
                        {message.isEvaluating
                          ? "Evaluating..."
                          : "Evaluate Answer"}
                      </button>
                    </div>
                  )}

                  {message.evaluation && (
                    <div className="evaluation-card">
                      <h4>Evaluation</h4>

                      <div className="score-grid">
                        <div className="score-box">
                          <span>Faithfulness</span>
                          <strong>
                            {formatScore(message.evaluation.faithfulness)}
                          </strong>
                        </div>

                        <div className="score-box">
                          <span>Answer Relevance</span>
                          <strong>
                            {formatScore(message.evaluation.answer_relevance)}
                          </strong>
                        </div>

                        <div className="score-box">
                          <span>Context Usefulness</span>
                          <strong>
                            {formatScore(message.evaluation.context_usefulness)}
                          </strong>
                        </div>
                      </div>

                      <p className="evaluation-explanation">
                        {message.evaluation.explanation}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {isAsking && (
            <div className="message-row assistant-row">
              <div className="message-bubble assistant-bubble">
                <p>Thinking...</p>
              </div>
            </div>
          )}
        </div>

        <div className="chat-input-bar">
          <input
            className="chat-input"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={
              documents.length === 0
                ? "Upload a PDF first..."
                : "Ask a question about your PDF..."
            }
            disabled={documents.length === 0 || isAsking}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleAsk();
              }
            }}
          />

          <button
            className="button primary"
            onClick={handleAsk}
            disabled={documents.length === 0 || isAsking}
          >
            Send
          </button>
        </div>
      </main>
    </div>
  );
}

export default App;