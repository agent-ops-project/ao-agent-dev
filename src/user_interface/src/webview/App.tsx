import React, { useState, useEffect } from 'react';
import { GraphView } from './components/GraphView';
import { ExperimentsView } from './components/ExperimentsView';
import { GraphNode, GraphEdge, GraphData } from './types';
import { sendReady } from './utils/messaging';
import { useIsVsCodeDarkTheme } from './utils/themeUtils';

declare const vscode: any;

const exampleGraph: GraphData = {
  nodes: [
    { id: '1', input: 'User input data', output: 'Processed user data', codeLocation: 'file.py:15', label: 'User Input Handler', border_color: '#ff3232' },
    { id: '2', input: 'Processed user data', output: 'Validated data', codeLocation: 'file.py:42', label: 'Data Validator', border_color: '#00c542' },
    { id: '3', input: 'Validated data', output: 'Database query', codeLocation: 'file.py:78', label: 'Query Builder', border_color: '#ffba0c' },
    { id: '4', input: 'Database query', output: 'Query results', codeLocation: 'file.py:23', label: 'Query Executor', border_color: '#ffba0c' },
    { id: '5', input: 'Query results', output: 'Formatted response', codeLocation: 'file.py:56', label: 'Response Formatter', border_color: '#00c542' },
    { id: '6', input: 'Validated data', output: 'Cache key', codeLocation: 'file.py:12', label: 'Cache Key Generator', border_color: '#ff3232' },
    { id: '7', input: 'Cache key', output: 'Cache status', codeLocation: 'file.py:34', label: 'Cache Manager', border_color: '#00c542' },
  ],
  edges: [
    { id: 'e1-2', source: '1', target: '2' },
    { id: 'e2-3', source: '2', target: '3' },
    { id: 'e3-4', source: '3', target: '4' },
    { id: 'e4-5', source: '4', target: '5' },
    { id: 'e2-6', source: '2', target: '6' },
    { id: 'e6-7', source: '6', target: '7' },
    { id: 'e7-5', source: '7', target: '5' },
  ],
};

export const App: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'overview' | 'experiments' | 'experiment-graph'>('overview');
    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    const [processes, setProcesses] = useState<Array<{
        pid: number;
        script_name: string;
        session_id: string;
        status: string;
        role?: string;
    }>>([]);
    const [selectedExperiment, setSelectedExperiment] = useState<{ pid: number; script_name: string; session_id: string; status: string; role?: string } | null>(null);

    const isDarkTheme = useIsVsCodeDarkTheme();

    useEffect(() => {
        // Listen for messages from the extension
        const handleMessage = (event: MessageEvent) => {
            const message = event.data;
            console.log('Received message:', message); // Debug log
            switch (message.type) {
                case 'addNode':
                    console.log('Adding node:', message.payload); // Debug log
                    setNodes(prev => [...prev, message.payload]);
                    break;
                case 'setGraph':
                    console.log('Setting graph:', message.payload); // Debug log
                    if (message.payload.nodes) {
                        setNodes(message.payload.nodes);
                    }
                    if (message.payload.edges) {
                        setEdges(message.payload.edges);
                    }
                    break;
                case 'process_list':
                    console.log('Received process list:', message.processes); // Debug log
                    setProcesses(message.processes || []);
                    break;
            }
        };

        window.addEventListener('message', handleMessage);
        
        // Notify extension that webview is ready
        console.log('Sending ready message'); // Debug log
        sendReady();

        return () => {
            window.removeEventListener('message', handleMessage);
        };
    }, []);

    // Debug log for state changes
    useEffect(() => {
        console.log('Nodes updated:', nodes);
        console.log('Edges updated:', edges);
    }, [nodes, edges]);

    const handleNodeUpdate = (nodeId: string, field: string, value: string) => {
        setNodes(prev => prev.map(node => 
            node.id === nodeId ? { ...node, [field]: value } : node
        ));
    };

    // Filter for shim-control only
    const shimControlProcesses = processes.filter(p => p.role === 'shim-control');
    const runningProcesses = shimControlProcesses.filter(p => p.status === 'running');
    const finishedProcesses = shimControlProcesses.filter(p => p.status === 'finished');

    const handleExperimentCardClick = (process: any) => {
        setSelectedExperiment(process);
        setActiveTab('experiment-graph');
    };

    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: isDarkTheme ? "#252525" : "#F0F0F0",
        }}
      >
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid var(--vscode-editorWidget-border)",
          }}
        >
          <button
            onClick={() => setActiveTab("overview")}
            style={{
              padding: "10px 20px",
              border: "none",
              backgroundColor:
                activeTab === "overview"
                  ? "var(--vscode-button-background)"
                  : "transparent",
              color:
                activeTab === "overview"
                  ? "var(--vscode-button-foreground)"
                  : "var(--vscode-editor-foreground)",
              cursor: "pointer",
            }}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab("experiments")}
            style={{
              padding: "10px 20px",
              border: "none",
              backgroundColor:
                activeTab === "experiments"
                  ? "var(--vscode-button-background)"
                  : "transparent",
              color:
                activeTab === "experiments"
                  ? "var(--vscode-button-foreground)"
                  : "var(--vscode-editor-foreground)",
              cursor: "pointer",
            }}
          >
            Experiments
          </button>
          {activeTab === 'experiment-graph' && selectedExperiment && (
            <button
              onClick={() => setActiveTab('experiment-graph')}
              style={{
                padding: "10px 20px",
                border: "none",
                backgroundColor: "var(--vscode-button-background)",
                color: "var(--vscode-button-foreground)",
                cursor: "pointer",
              }}
            >
              {selectedExperiment.script_name}
            </button>
          )}
        </div>
        <div style={{ flex: 1, overflow: "hidden" }}>
          {activeTab === "overview" ? (           
              <GraphView
                nodes={nodes}
                edges={edges}
                onNodeUpdate={handleNodeUpdate}
              />
          ) : activeTab === "experiments" ? (
            <ExperimentsView runningProcesses={runningProcesses} finishedProcesses={finishedProcesses} onCardClick={handleExperimentCardClick} />
          ) : activeTab === 'experiment-graph' && selectedExperiment ? (
            <GraphView
              nodes={exampleGraph.nodes}
              edges={exampleGraph.edges}
              onNodeUpdate={() => {}}
            />
          ) : null}
        </div>
      </div>
    );
};