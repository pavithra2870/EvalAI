import { useState } from "react";
import { evaluateAnswer } from "./api";
import ResultCard from "./components/ResultCard";
import "./styles.css";

export default function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await evaluateAnswer(question.trim(), answer.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="container">
        <header className="header">
          <h1>Mini Answer Evaluator</h1>
          <p className="subtitle">RAG + LLM powered academic answer grader</p>
        </header>

        <form onSubmit={handleSubmit} className="form">
          <div className="field">
            <label htmlFor="question">Question</label>
            <textarea
              id="question"
              rows={3}
              placeholder="Enter the exam question here…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="answer">Student Answer</label>
            <textarea
              id="answer"
              rows={6}
              placeholder="Enter the student's answer here…"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? "Evaluating…" : "Evaluate Answer"}
          </button>
        </form>

        {error && <div className="error-box">{error}</div>}
        {result && <ResultCard result={result} />}
      </div>
    </div>
  );
}
