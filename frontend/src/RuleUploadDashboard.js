// RuleUploadDashboard.js
// World-class, enterprise-grade UI for rule upload, validation, and results
// Designed in the spirit of Langdor & Fitch: clarity, elegance, and usability

import React, { useRef, useState } from "react";

function RuleUploadDashboard({ onUpload, results }) {
  const ruleInput = useRef();
  const studyInput = useRef();
  const [ruleId, setRuleId] = useState("");
  const [studyId, setStudyId] = useState("");
  const [ruleUploading, setRuleUploading] = useState(false);
  const [studyUploading, setStudyUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [reportUrl, setReportUrl] = useState("");

  const uploadFile = async (file, endpoint) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData
    });
    if (!response.ok) throw new Error("Upload failed");
    return await response.json();
  };

  const handleRuleUpload = async () => {
    setError("");
    setSuccess(false);
    const file = ruleInput.current.files[0];
    if (!file) {
      setError("Please select a rule/spec file to upload.");
      return;
    }
    setRuleUploading(true);
    try {
      const data = await uploadFile(file, "/api/v1/rule/upload");
      setRuleId(data.rule_id);
    } catch (err) {
      setError("Rule upload error: " + err.message);
    } finally {
      setRuleUploading(false);
    }
  };

  const handleStudyUpload = async () => {
    setError("");
    setSuccess(false);
    const file = studyInput.current.files[0];
    if (!file) {
      setError("Please select a study file to upload.");
      return;
    }
    setStudyUploading(true);
    try {
      const data = await uploadFile(file, "/api/v1/study/upload");
      setStudyId(data.study_id);
    } catch (err) {
      setError("Study upload error: " + err.message);
    } finally {
      setStudyUploading(false);
    }
  };

  const handleValidate = async () => {
    setError("");
    setSuccess(false);
    setValidating(true);
    setValidationResult(null);
    setReportUrl("");
    try {
      const response = await fetch(`/api/v1/rule/validate`, {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_id: ruleId, study_id: studyId })
      });
      if (!response.ok) throw new Error("Validation failed");
      const result = await response.json();
      setValidationResult(result);
      setSuccess(true);
      if (onUpload) onUpload();
      setReportUrl(`/api/v1/rule/report?rule_id=${ruleId}&study_id=${studyId}&fmt=html`);
    } catch (err) {
      setError("Validation error: " + err.message);
    } finally {
      setValidating(false);
    }
  };

  return (
    <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 24, background: "#fff", marginTop: 32, maxWidth: 600, marginLeft: "auto", marginRight: "auto" }}>
      <h3 style={{ color: "#0074D9" }}>Upload Rule/Spec and Study File</h3>
      <div style={{ marginBottom: 18 }}>
        <label style={{ fontWeight: 500 }}>Rule/Spec File:</label>
        <input type="file" ref={ruleInput} style={{ marginLeft: 8 }} disabled={ruleUploading} />
        <button onClick={handleRuleUpload} style={{ marginLeft: 12, padding: "6px 14px", background: ruleUploading ? "#ccc" : "#0074D9", color: "#fff", border: "none", borderRadius: 4 }} disabled={ruleUploading}>
          {ruleUploading ? "Uploading..." : ruleId ? "Re-upload" : "Upload"}
        </button>
        {ruleId && <span style={{ color: "#28a745", marginLeft: 10 }}>Uploaded</span>}
      </div>
      <div style={{ marginBottom: 18 }}>
        <label style={{ fontWeight: 500 }}>Study File:</label>
        <input type="file" ref={studyInput} style={{ marginLeft: 8 }} disabled={studyUploading} />
        <button onClick={handleStudyUpload} style={{ marginLeft: 12, padding: "6px 14px", background: studyUploading ? "#ccc" : "#FF9500", color: "#fff", border: "none", borderRadius: 4 }} disabled={studyUploading}>
          {studyUploading ? "Uploading..." : studyId ? "Re-upload" : "Upload"}
        </button>
        {studyId && <span style={{ color: "#28a745", marginLeft: 10 }}>Uploaded</span>}
      </div>
      <div style={{ marginBottom: 18 }}>
        <button
          onClick={handleValidate}
          style={{ padding: "10px 24px", background: ruleId && studyId && !validating ? "#7F4FBF" : "#ccc", color: "#fff", border: "none", borderRadius: 4, fontWeight: 600 }}
          disabled={!ruleId || !studyId || validating}
        >
          {validating ? "Validating..." : "Validate"}
        </button>
      </div>
      {error && <div style={{ color: "#d9534f", marginTop: 10 }}>{error}</div>}
      {success && <div style={{ color: "#28a745", marginTop: 10 }}>Validation complete!</div>}
      {results && results.length > 0 ? (
        <ul style={{ textAlign: "left" }}>
          {results.map((r, idx) => (
            <li key={idx} style={{ marginBottom: 6 }}>
              <strong>{r.ruleId || "Rule"}:</strong> {r.status} {r.explanation && <span>- {r.explanation}</span>}
              {/* Feedback Button */}
              <button style={{ marginLeft: 12 }} onClick={() => setFeedbackModal({ open: true, idx })}>Feedback</button>
              {/* Causal Path Button */}
              <button style={{ marginLeft: 6 }} onClick={() => handleShowCausalPath(r.ruleId, r.studyId)}>Show Causal Path</button>
            </li>
          ))}
        </ul>
      ) : (
        <div style={{ color: "#888" }}>No results yet.</div>
      )}
      {/* Feedback Modal */}
      {feedbackModal && feedbackModal.open && (
        <div style={{ position: "fixed", top: 100, left: 0, right: 0, background: "#fff", border: "1px solid #0074D9", borderRadius: 8, maxWidth: 400, margin: "0 auto", zIndex: 1000, padding: 24 }}>
          <h4>Submit Feedback</h4>
          <select value={feedbackType} onChange={e => setFeedbackType(e.target.value)}>
            <option value="correct">Correct</option>
            <option value="incorrect">Incorrect</option>
            <option value="improve">Needs Improvement</option>
          </select>
          <textarea style={{ width: "100%", marginTop: 12 }} rows={3} placeholder="Additional comments..." value={feedbackComment} onChange={e => setFeedbackComment(e.target.value)} />
          <div style={{ marginTop: 12 }}>
            <button onClick={handleSubmitFeedback}>Submit</button>
            <button style={{ marginLeft: 12 }} onClick={() => setFeedbackModal(null)}>Cancel</button>
          </div>
        </div>
      )}
      {/* Causal Path Modal */}
      {causalPathModal && (
        <div style={{ position: "fixed", top: 120, left: 0, right: 0, background: "#fff", border: "1px solid #7F4FBF", borderRadius: 8, maxWidth: 500, margin: "0 auto", zIndex: 1000, padding: 24 }}>
          <h4>Causal Path</h4>
          <ul>
            {causalPathModal.path.map((step, i) => <li key={i}>{step}</li>)}
          </ul>
          <button style={{ marginTop: 12 }} onClick={() => setCausalPathModal(null)}>Close</button>
        </div>
      )}
      {/* Rule Suggestion */}
      <div style={{ marginTop: 32, padding: 16, background: "#f8f8ff", borderRadius: 8 }}>
        <button onClick={handleSuggestRule}>Suggest New Rule</button>
        {suggestedRule && (
          <div style={{ marginTop: 12, color: "#0074D9" }}>
            <strong>Suggested Rule:</strong> {suggestedRule}
          </div>
        )}
      </div>
      {reportUrl && (
        <div style={{ marginTop: 10 }}>
          <a href={reportUrl} target="_blank" rel="noopener noreferrer" style={{ color: "#0074D9", fontWeight: 500 }}>Download Validation Report (HTML)</a>
        </div>
      )}
    </div>
  );
}

export default RuleUploadDashboard;
