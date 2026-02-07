import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/* ---------- Helpers ---------- */
function formatPath(path) {
  if (!path) return "";
  const idx = path.indexOf("repo_clone_");
  if (idx === -1) return path;
  return path.slice(idx).replace(/^repo_clone_[^/]+\//, "");
}

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [ingestStatus, setIngestStatus] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);

  const [level, setLevel] = useState("developer");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [lastResults, setLastResults] = useState([]);

  async function handleIngest(e) {
    e?.preventDefault();
    if (!repoUrl) return;

    setIngestLoading(true);
    setIngestStatus(null);

    try {
      const res = await fetch(`${API_BASE}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setIngestStatus({ success: true, data });
    } catch (err) {
      setIngestStatus({ success: false, error: String(err) });
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleSendQuestion(e) {
    e?.preventDefault();
    if (!question) return;

    const q = question.trim();
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, level, top_k: 5 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));

      setMessages((m) => [...m, { role: "assistant", text: data.prompt }]);
      setLastResults(data.results || []);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Error: ${String(err)}` },
      ]);
    }
  }

  return (
    <div style={{ background: "#f1f5f9", minHeight: "100vh", padding: 32 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>

        {/* Gradient Header */}
        <div
          style={{
            background: "linear-gradient(135deg, #2563eb, #4f46e5)",
            color: "#fff",
            padding: "36px 32px",
            borderRadius: 16,
            marginBottom: 32,
            boxShadow: "0 12px 24px rgba(37,99,235,0.25)",
          }}
        >
          <h1 style={{ fontSize: 38, fontWeight: 800, marginBottom: 10 }}>
            Code Doc Navigator
          </h1>
          <p style={{ opacity: 0.95, maxWidth: 700, fontSize: 16 }}>
            Explore, understand, and reason about large codebases using
            AI-powered semantic search and retrieval.
          </p>
        </div>

        {/* Ingest Section */}
        <section style={card}>
          <h2 style={sectionTitle}>🚀 Ingest GitHub Repository</h2>

          <form onSubmit={handleIngest} style={{ display: "flex", gap: 10 }}>
            <input
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              style={input}
            />
            <button type="submit" disabled={ingestLoading} style={primaryButton}>
              {ingestLoading ? "Ingesting…" : "Ingest"}
            </button>
          </form>

          {ingestStatus?.success && (
            <div style={successBox}>
              Ingested <strong>{ingestStatus.data.ingested_files}</strong> files ·{" "}
              <strong>{ingestStatus.data.chunks}</strong> chunks
            </div>
          )}

          {ingestStatus && !ingestStatus.success && (
            <div style={errorBox}>{ingestStatus.error}</div>
          )}
        </section>

        {/* Query Section */}
        <section style={card}>
          <h2 style={sectionTitle}>💬 Ask Questions About the Code</h2>

          <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              style={{ ...input, maxWidth: 180 }}
            >
              <option value="beginner">Beginner</option>
              <option value="developer">Developer</option>
              <option value="architect">Architect</option>
            </select>

            <form onSubmit={handleSendQuestion} style={{ display: "flex", flex: 1, gap: 10 }}>
              <input
                placeholder="Ask a question about the repository..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                style={input}
              />
              <button type="submit" style={primaryButton}>
                Send
              </button>
            </form>
          </div>

          <div style={{ display: "flex", gap: 24 }}>
            {/* Chat */}
            <div style={{ flex: 2 }}>
              <h3>Conversation</h3>
              <div style={chatBox}>
                {messages.length === 0 && (
                  <p style={{ color: "#64748b" }}>No messages yet.</p>
                )}
                {messages.map((m, i) => (
                  <div key={i} style={{ marginBottom: 14 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {m.role === "user" ? "You" : "Assistant"}
                    </div>
                    <pre
                      style={{
                        ...message,
                        background: m.role === "user" ? "#e0e7ff" : "#ffffff",
                        borderLeft:
                          m.role === "assistant" ? "4px solid #2563eb" : "none",
                      }}
                    >
                      {m.text}
                    </pre>
                  </div>
                ))}
              </div>
            </div>

            {/* Referenced Files */}
            <div style={{ flex: 1, maxWidth: 380 }}>
              <h3>Referenced Files</h3>
              {lastResults.length === 0 && (
                <p style={{ color: "#64748b" }}>No results yet.</p>
              )}
              <ul style={{ paddingLeft: 0, listStyle: "none" }}>
                {lastResults.map((r, i) => (
                  <li key={i} style={fileCard}>
                    <div
                      title={r.file_path}
                      style={{
                        fontWeight: 600,
                        wordBreak: "break-all",
                        marginBottom: 4,
                      }}
                    >
                      {formatPath(r.file_path)}
                    </div>
                    <div style={{ fontSize: 12, color: "#475569" }}>
                      similarity score: {r.score?.toFixed(3)}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <footer style={{ marginTop: 32, fontSize: 12, color: "#64748b" }}>
          Backend running at <strong>{API_BASE}</strong>
        </footer>
      </div>
    </div>
  );
}

/* ---------- Styles ---------- */

const card = {
  background: "#ffffff",
  borderRadius: 16,
  padding: 24,
  marginBottom: 28,
  boxShadow: "0 8px 16px rgba(0,0,0,0.06)",
};

const sectionTitle = {
  fontSize: 22,
  fontWeight: 700,
  marginBottom: 16,
};

const input = {
  padding: "10px 12px",
  borderRadius: 8,
  border: "1px solid #cbd5f5",
  flex: 1,
  fontSize: 14,
};

const primaryButton = {
  background: "linear-gradient(135deg, #2563eb, #4f46e5)",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  padding: "10px 18px",
  fontWeight: 600,
  cursor: "pointer",
  boxShadow: "0 6px 14px rgba(37,99,235,0.35)",
};

const chatBox = {
  minHeight: 220,
  maxHeight: 420,
  overflowY: "auto",
  background: "#f8fafc",
  padding: 16,
  borderRadius: 12,
};

const message = {
  padding: 12,
  borderRadius: 10,
  whiteSpace: "pre-wrap",
  fontSize: 13,
};

const fileCard = {
  background: "#f8fafc",
  padding: 12,
  borderRadius: 10,
  marginBottom: 10,
};

const successBox = {
  marginTop: 14,
  padding: 12,
  background: "#dcfce7",
  color: "#166534",
  borderRadius: 8,
};

const errorBox = {
  marginTop: 14,
  padding: 12,
  background: "#fee2e2",
  color: "#991b1b",
  borderRadius: 8,
};
