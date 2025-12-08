import { useState, useRef, useEffect } from "react";
import "../App.css";

// Backend upload URL
const BACKEND_ANALYZE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, "")}/analyze-chair`
  : "http://127.0.0.1:8000/analyze-chair";

function Dashboard() {
  const [isModalOpen, setModalOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState(
    "No design started. Upload an image, draw a sketch, or choose a template to begin."
  );
  const [resultData, setResultData] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState("");

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function openModal() {
    setFile(null);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
  }

  function sendChatMessage() {
    if (!chatInput || !chatInput.trim()) return;

    const message = {
      text: chatInput.trim(),
      sender: "user",
    };

    setChatHistory((prev) => [...prev, message]);
    setChatInput("");
    setStatus(`Message sent: ${message.text}`);
  }

  async function upload() {
    if (!file) return setStatus("Please choose a file first.");
    setLoading(true);
    setStatus("Analyzing chair...");

    try {
      const form = new FormData();
      form.append("file", file);

      const resp = await fetch(BACKEND_ANALYZE, {
        method: "POST",
        body: form,
      });

      if (!resp.ok) {
        const text = await resp.text();
        setStatus(`Error: ${resp.status} ${text}`);
        setResultData(null);
        return;
      }

      const data = await resp.json();
      setResultData(data);
      setStatus("Chair analyzed successfully!");
      setModalOpen(false);
    } catch (err) {
      console.error(err);
      setStatus(`Upload failed: ${err.message}`);
      setResultData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-root">
      <aside className="side">
        <div className="logo-title">DesignableAI</div>
        <div className="panel-card">
          <div className="panel-head">
            <div>
              <div className="panel-title">Documents</div>
              <div className="muted small">
                Upload images to extract text
              </div>
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <button className="btn" onClick={openModal}>
              📤 Upload
            </button>
            <button className="btn" style={{ marginTop: 8 }}>
              ✏️ Draw
            </button>
            <button className="btn" style={{ marginTop: 8 }}>
              📋 Templates
            </button>
          </div>
        </div>

        <div className="profile-button">
          <div className="profile-image">
            <div className="profile-placeholder">F</div>
          </div>
          <span>Fahad</span>
        </div>

        <div className="tip muted">
          Tip: Upload images for text extraction, Draw to create sketches, or
          browse Templates for quick designs.
        </div>
      </aside>

      <main className="main">
        <div className="heading">
          <h2>Dashboard</h2>
        </div>

        <div className="panel-card">
          <div id="status" className="muted">
            {status}
          </div>

          {preview && <img src={preview} alt="preview" className="preview" />}

          {/* ANALYSIS RESULTS DISPLAY */}
          {resultData && (
            <div className="analysis-output" style={{ marginTop: "20px" }}>
              <h3 style={{ marginBottom: "12px" }}>🔍 Analysis Results</h3>

              {/* Identified Chair Type */}
              {resultData.identified_type && (
                <div style={{ marginBottom: "20px", padding: "12px", backgroundColor: "#f5f5f5", borderRadius: "6px" }}>
                  <h4 style={{ marginBottom: "8px", color: "#333" }}>Detected Chair Type:</h4>
                  <p style={{ fontWeight: "bold", fontSize: "1.2em", color: "#1976d2", margin: 0 }}>
                    {resultData.identified_type}
                  </p>
                </div>
              )}

              {/* Canonical Parts */}
              {resultData.canonical_parts && resultData.canonical_parts.length > 0 && (
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ marginBottom: "10px" }}>Detected Components:</h4>
                  <ul style={{ margin: "0 0 0 20px", padding: 0 }}>
                    {resultData.canonical_parts.map((part, i) => (
                      <li key={i} style={{ marginBottom: "6px" }}>
                        {part}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Linked Data / Measurements */}
              {resultData.linked_data && resultData.linked_data.length > 0 && (
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ marginBottom: "10px" }}>Linked Measurements:</h4>
                  <div style={{ display: "grid", gap: "8px" }}>
                    {resultData.linked_data.map((item, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "8px",
                          backgroundColor: "#fafafa",
                          borderLeft: "3px solid #1976d2",
                          borderRadius: "4px",
                        }}
                      >
                        <strong>{item.text}</strong> → {item.segment_class}{" "}
                        <span style={{ color: "#666", fontSize: "0.9em" }}>
                          (distance: {item.distance.toFixed(2)})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SAM Segments */}
              {resultData.segments && resultData.segments.length > 0 && (
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ marginBottom: "10px" }}>Detected Segments (SAM):</h4>
                  <div style={{ display: "grid", gap: "10px" }}>
                    {resultData.segments.map((segment, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "10px",
                          backgroundColor: "#fafafa",
                          border: "1px solid #ddd",
                          borderRadius: "6px",
                        }}
                      >
                        <div style={{ fontWeight: "bold", marginBottom: "6px" }}>
                          {segment.component_type}
                        </div>
                        <div style={{ fontSize: "0.9em", color: "#666" }}>
                          <strong>BBox:</strong> [{segment.bbox.join(", ")}]
                        </div>
                        <div style={{ fontSize: "0.9em", color: "#666" }}>
                          <strong>Area:</strong> {segment.area} | <strong>IOU:</strong>{" "}
                          {segment.predicted_iou.toFixed(2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw JSON Response */}
              <details style={{ marginTop: "20px" }}>
                <summary style={{ cursor: "pointer", fontWeight: "bold", color: "#1976d2" }}>
                  View Raw JSON Response
                </summary>
                <pre
                  style={{
                    marginTop: "12px",
                    padding: "12px",
                    backgroundColor: "#f5f5f5",
                    borderRadius: "6px",
                    overflow: "auto",
                    fontSize: "0.85em",
                  }}
                >
                  {JSON.stringify(resultData, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>

        {/* Chat Window */}
        <div className="chat-window">
          {chatHistory.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.sender}`}>
              {msg.text}
            </div>
          ))}
        </div>

        {/* Chat Input */}
        <div className="chatbar">
          <input
            className="chat-input"
            placeholder="Ask the design assistant..."
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendChatMessage();
            }}
          />
          <button className="btn chat-send" onClick={sendChatMessage}>
            ➤
          </button>
        </div>
      </main>

      {/* Upload Modal */}
      {isModalOpen && (
        <div className="modal-backdrop" role="dialog">
          <div className="modal panel-card">
            <div className="modal-head">
              <div className="modal-title">Upload Image</div>
              <button className="btn ghost" onClick={closeModal}>
                ✕
              </button>
            </div>

            <div className="muted small">
              Choose an image (jpg, png). Max file size depends on backend.
            </div>
            <input
              ref={inputRef}
              className="file-input"
              type="file"
              accept="image/*"
              onChange={(e) =>
                setFile(e.target.files && e.target.files[0])
              }
            />

            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
              <button className="btn" onClick={upload} disabled={loading}>
                {loading ? "Uploading..." : "Upload & Extract"}
              </button>
              <button className="btn ghost" onClick={closeModal}>
                Cancel
              </button>
            </div>

            <div className="muted small" style={{ marginTop: 10 }}>
              {loading ? "Working..." : ""}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;