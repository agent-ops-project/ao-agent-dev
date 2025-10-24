import { useEffect, useState, useRef} from "react";
import "./App.css";
import type { GraphNode, GraphEdge, ProcessInfo } from "../../../user_interface/src/webview/types";
import { GraphView } from "../../../user_interface/src/webview/components/GraphView";
import { ExperimentsView} from "../../../user_interface/src/webview/components/ExperimentsView";
import type { MessageSender } from "../../../user_interface/src/webview/shared/MessageSender";
import { EditDialog } from "../../../user_interface/src/webview/components/EditDialog";

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
  const [experiments, setExperiments] = useState<ProcessInfo[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<ProcessInfo | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  // const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editDialog, setEditDialog] = useState<{
    nodeId: string;
    field: string;
    value: string;
    label: string;
    attachments?: any;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Detect dark theme
  const isDarkTheme = window.matchMedia?.("(prefers-color-scheme: dark)").matches || false;

  // Create webapp MessageSender
  const messageSender: MessageSender = {
    send: (message: any) => {
      if (message.type === "showEditDialog") {
        setEditDialog(message.payload);
      } else if (
        message.type === "trackNodeInputView" ||
        message.type === "trackNodeOutputView"
      ) {
        console.log("Telemetry:", message.type, message.payload);
      } else if (message.type === "navigateToCode") {
        console.log("Code navigation not available in webapp");
      } else if (ws) {
        ws.send(JSON.stringify(message));
      }
    },
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
      if (field == "input") {
        ws.send(
          JSON.stringify({
            type: "edit_input",
            session_id: selectedExperiment.session_id,
            node_id: nodeId,
            value,
          })
        )
      } else if (field == "output") {
        ws.send(
          JSON.stringify({
            type: "edit_output",
            session_id: selectedExperiment.session_id,
            node_id: nodeId,
            value,
          })
        )
      } else {
        ws.send(
          JSON.stringify({
            type: "updateNode",
            session_id: selectedExperiment.session_id,
            nodeId,
            field,
            value,
          })
        );
      }
    }
  };

  const handleExperimentClick = (experiment: ProcessInfo) => {
    setSelectedExperiment(experiment);
    if (ws) ws.send(JSON.stringify({ type: "get_graph", session_id: experiment.session_id }));
  };

  // const running = experiments.filter((e) => e.status === "running");
  // const finished = experiments.filter((e) => e.status === "finished");

  const sortedExperiments = [...experiments].sort((a, b) => {
    if (!a.timestamp) return 1;
    if (!b.timestamp) return -1;
    return b.timestamp.localeCompare(a.timestamp);
  });
  
  const running = sortedExperiments.filter((e) => e.status === "running");
  const finished = sortedExperiments.filter((e) => e.status === "finished");

  return (
    <div className="app-container">
      <div className="sidebar">
        <ExperimentsView
          runningProcesses={running}
          finishedProcesses={finished}
          onCardClick={handleExperimentClick}
          isDarkTheme={isDarkTheme}
        />
      </div>

      <div className="graph-container" ref={containerRef}>
        {/* <button className="toggle-button" onClick={() => setSidebarOpen(!sidebarOpen)}>
          {sidebarOpen ? "Hide Experiments" : "Show Experiments"}
        </button> */}

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

        {/* {editDialog && (
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
                    handleNodeUpdate(
                      editDialog.nodeId,
                      editDialog.field as keyof GraphNode,
                      editDialog.value
                    );
                    setEditDialog(null);
                  }}
                >
                  Save
                </button>
                <button onClick={() => setEditDialog(null)}>Cancel</button>
              </div>
            </div>
          </div>
        )} */}
        {editDialog && (
          <EditDialog
            title={`Edit ${editDialog.label}`}
            value={editDialog.value}
            onSave={(newValue) => {
              handleNodeUpdate(
                editDialog.nodeId,
                editDialog.field as keyof GraphNode,
                newValue
              );
              setEditDialog(null);
            }}
            onCancel={() => setEditDialog(null)}
          />
        )}
      </div>
    </div>
  );
}

export default App;