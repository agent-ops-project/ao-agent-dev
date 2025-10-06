import { useEffect, useState, useRef} from "react";
import "./App.css";
import type { GraphNode, GraphEdge } from "../../../user_interface/src/webview/types";
import { GraphView } from "../../../user_interface/src/webview/components/GraphView";
import type { MessageSender } from "../../../user_interface/src/webview/shared/MessageSender";

interface Experiment {
  session_id: string;
  title: string;
  status: string;
  timestamp: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface WSMessage {
  type: string;
  experiments?: Experiment[];
  payload?: GraphData;
  session_id?: string;
}

function App() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editDialog, setEditDialog] = useState<{
    nodeId: string;
    field: string;
    value: string;
    label: string;
    attachments?: any;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Detect dark theme
  const isDarkTheme = window.matchMedia?.('(prefers-color-scheme: dark)').matches || false;

  // Create webapp MessageSender
  const messageSender: MessageSender = {
    send: (message: any) => {
      if (message.type === "showEditDialog") {
        setEditDialog(message.payload);
      } else if (message.type === "trackNodeInputView" || message.type === "trackNodeOutputView") {
        // No-op for webapp (could send to analytics if needed)
        console.log('Telemetry:', message.type, message.payload);
      } else if (message.type === "navigateToCode") {
        // No-op for webapp (not available)
        console.log('Code navigation not available in webapp');
      } else if (ws) {
        // Send other messages via WebSocket
        ws.send(JSON.stringify(message));
      }
    }
  };

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:4000");
    setWs(socket);

    socket.onopen = () => console.log("Connected to backend");

    socket.onmessage = (event: MessageEvent) => {
      const msg: WSMessage = JSON.parse(event.data);
      if (msg.type === "experiment_list" && msg.experiments) {
        setExperiments(msg.experiments);
      } else if (msg.type === "graph_update" && msg.payload) {
        setGraphData(msg.payload);
      }
    };

    return () => socket.close();
  }, []);

  const handleNodeUpdate = (nodeId: string, field: keyof GraphNode, value: string) => {
    if (selectedExperiment && ws) {
      ws.send(JSON.stringify({
        type: "updateNode",
        session_id: selectedExperiment.session_id,
        nodeId,
        field,
        value
      }));
    }
  };

  const handleExperimentClick = (experiment: Experiment) => {
    setSelectedExperiment(experiment);
    if (ws) ws.send(JSON.stringify({ type: "get_graph", session_id: experiment.session_id }));
  };

  return (
    <div className="app-container">
      {sidebarOpen && (
        <div className="sidebar">
          <h2 className="sidebar-title">Experiments</h2>
          <div className="experiment-list">
            {experiments.map((exp) => (
              <button
                key={exp.session_id}
                className="experiment-button"
                onClick={() => handleExperimentClick(exp)}
              >
                {exp.title}
                <br />
                <small className="experiment-status">({exp.status})</small>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="graph-container" ref={containerRef}>
        <button className="toggle-button" onClick={() => setSidebarOpen(!sidebarOpen)}>
          {sidebarOpen ? "Hide Experiments" : "Show Experiments"}
        </button>

        {selectedExperiment && graphData ? (
          <GraphView
            nodes={graphData.nodes}
            edges={graphData.edges}
            onNodeUpdate={handleNodeUpdate}
            session_id={selectedExperiment.session_id}
            experiment={selectedExperiment}
            messageSender={messageSender}
            isDarkTheme={isDarkTheme}
          />
        ) : (
          <div className="no-graph">
            {selectedExperiment ? "Loading graph..." : "Select an experiment to view its graph"}
          </div>
        )}

        {editDialog && (
          <div className="edit-dialog-overlay">
            <div className="edit-dialog">
              <h3>Edit {editDialog.label}</h3>
              <textarea
                value={editDialog.value}
                onChange={(e) => setEditDialog({ ...editDialog, value: e.target.value })}
                rows={10}
                cols={50}
              />
              <div className="dialog-buttons">
                <button
                  onClick={() => {
                    handleNodeUpdate(editDialog.nodeId, editDialog.field as keyof GraphNode, editDialog.value);
                    setEditDialog(null);
                  }}
                >
                  Save
                </button>
                <button onClick={() => setEditDialog(null)}>Cancel</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;