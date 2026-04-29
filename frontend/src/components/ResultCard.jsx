export default function ResultCard({ result }) {
  const { rubric, marks_awarded, max_marks, feedback, justification } = result;
  const percentage = Math.round((marks_awarded / max_marks) * 100);
  const scoreColor =
    percentage >= 70 ? "#16a34a" : percentage >= 40 ? "#d97706" : "#dc2626";

  return (
    <div className="result-card">
      {/* Score banner */}
      <div className="score-banner">
        <span className="score" style={{ color: scoreColor }}>
          {marks_awarded} / {max_marks}
        </span>
        <span className="percentage" style={{ color: scoreColor }}>
          ({percentage}%)
        </span>
      </div>

      {/* Rubric details */}
      <div className="section">
        <h3 className="section-title">Rubric Used</h3>
        <p className="rubric-meta">
          <strong>Subject:</strong> {rubric.subject}&nbsp;&nbsp;|&nbsp;&nbsp;
          <strong>Topic:</strong> {rubric.topic}
        </p>
        <ul className="criteria-list">
          {rubric.criteria.map((c) => (
            <li key={c.name} className="criterion-item">
              <span className="crit-name">{c.name}</span>
              <span className="crit-marks">({c.marks_weight} mk)</span>
              <span className="crit-desc">{c.description}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Feedback */}
      <div className="section">
        <h3 className="section-title">Feedback</h3>
        <p className="body-text">{feedback}</p>
      </div>

      {/* Justification */}
      <div className="section no-border">
        <h3 className="section-title">Justification</h3>
        <p className="body-text">{justification}</p>
      </div>
    </div>
  );
}
