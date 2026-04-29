const API_BASE = "http://localhost:8000/api";

export async function evaluateAnswer(question, answer) {
  const response = await fetch(`${API_BASE}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, answer }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Evaluation failed");
  }

  return response.json();
}
