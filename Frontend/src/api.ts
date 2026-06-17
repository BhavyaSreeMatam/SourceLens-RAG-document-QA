import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function uploadPDF(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function askQuestion(question: string, topK: number = 3) {
  const response = await axios.post(`${API_BASE_URL}/ask`, {
    question: question,
    top_k: topK,
  });

  return response.data;
}

export async function getDocuments() {
  const response = await axios.get(`${API_BASE_URL}/documents`);
  return response.data;
}

export async function deleteDocument(filename: string) {
  const response = await axios.delete(
    `${API_BASE_URL}/documents/${encodeURIComponent(filename)}`
  );

  return response.data;
}

export async function deleteAllDocuments() {
  const response = await axios.delete(`${API_BASE_URL}/documents`);
  return response.data;
}

export async function evaluateAnswer(
  question: string,
  answer: string,
  contexts: string[]
) {
  const response = await axios.post(`${API_BASE_URL}/evaluate`, {
    question: question,
    answer: answer,
    contexts: contexts,
  });

  return response.data;
}