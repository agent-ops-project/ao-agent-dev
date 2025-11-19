import React, { useState, useEffect } from 'react';
import { GraphView } from '../../../shared_components/components/graph/GraphView';
import { GraphData, ProcessInfo } from '../../../shared_components/types';
import { MessageSender } from '../../../shared_components/types/MessageSender';
import { useIsVsCodeDarkTheme } from '../../../shared_components/utils/themeUtils';
import { WorkflowRunDetailsPanel } from '../../../shared_components/components/experiment/WorkflowRunDetailsPanel';
import { NodeEditModal } from './NodeEditModal';

// Global type augmentation for window.vscode
declare global {
  interface Window {
    vscode?: {
      postMessage: (message: any) => void;
    };
    sessionId?: string;
    isGraphTab?: boolean;
  }
}

export const GraphTabApp: React.FC = () => {
  const [experiment, setExperiment] = useState<ProcessInfo | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isGraphReady, setIsGraphReady] = useState(false);
  const [showNodeEditModal, setShowNodeEditModal] = useState(false);
  const [nodeEditData, setNodeEditData] = useState<{ nodeId: string; field: 'input' | 'output'; label: string; value: string } | null>(null);
  const isDarkTheme = useIsVsCodeDarkTheme();

  // Override body overflow to allow scrolling
  useEffect(() => {
    document.body.style.overflow = 'auto';
    return () => {
      document.body.style.overflow = 'hidden'; // Reset on cleanup
    };
  }, []);

  // Create MessageSender for VS Code environment
  const messageSender: MessageSender = {
    send: (message: any) => {
      // Handle showNodeEditModal locally by dispatching window event
      if (message.type === 'showNodeEditModal') {
        window.dispatchEvent(new CustomEvent('show-node-edit-modal', {
          detail: message.payload
        }));
      } else if (window.vscode) {
        window.vscode.postMessage(message);
      }
    }
  };


  // Initialize and listen for messages
  useEffect(() => {
    // Get session ID from window
    if (window.sessionId) {
      setSessionId(window.sessionId);
    }

    const handleMessage = (event: MessageEvent) => {
      const message = event.data;

      switch (message.type) {
        case 'init':
          // Initialize the tab with experiment data
          const initExperiment = message.payload.experiment;
          // Handle transition from title to run_name for backwards compatibility
          const normalizedExperiment = {
            ...initExperiment,
            run_name: initExperiment.run_name || initExperiment.title || '',
          };
          setExperiment(normalizedExperiment);
          setSessionId(message.payload.sessionId);
          break;
        case 'graph_update':
          if (message.session_id === sessionId || message.session_id === window.sessionId) {
            setIsGraphReady(false); // Reset ready state
            setGraphData(message.payload);
          }
          break;
        case 'configUpdate':
          // Forward config updates to config bridge
          window.dispatchEvent(new CustomEvent('configUpdate', { detail: message.detail }));
          break;
        case 'updateNode':
          // Handle node updates from edit dialogs
          if (message.payload && graphData) {
            const { nodeId, field, value, session_id } = message.payload;
            if (session_id === sessionId) {
              handleNodeUpdate(nodeId, field, value, session_id);
            }
          }
          break;
        case 'experiment_update':
          // Update experiment data if it matches our session
          if (message.session_id === sessionId && message.experiment) {
            setExperiment(message.experiment);
          }
          break;
        case 'experiment_list':
          // Handle experiment list updates from server
          if (message.experiments && sessionId) {
            const updatedExperiment = message.experiments.find(
              (exp: any) => exp.session_id === sessionId
            );
            if (updatedExperiment) {
              // Map server experiment format to ProcessInfo format
              const processInfo = {
                session_id: updatedExperiment.session_id,
                status: updatedExperiment.status,
                timestamp: updatedExperiment.timestamp,
                run_name: updatedExperiment.run_name,
                result: updatedExperiment.success,
                notes: updatedExperiment.notes,
                log: updatedExperiment.log,
                color_preview: updatedExperiment.color_preview
              };
              setExperiment(processInfo);
              
              // Update tab title when experiment data changes
              if (window.vscode && processInfo.run_name) {
                window.vscode.postMessage({
                  type: 'updateTabTitle',
                  payload: {
                    sessionId: sessionId,
                    title: processInfo.run_name
                  }
                });
              }
            }
          }
          break;
        case 'vscode-theme-change':
          // Theme changes are handled by the useIsVsCodeDarkTheme hook
          break;
      }
    };

    window.addEventListener('message', handleMessage);

    // Listen for custom events
    const handleShowNodeEditModal = (event: CustomEvent) => {
      const { nodeId, field, label, value } = event.detail;
      setNodeEditData({ nodeId, field, label, value });
      setShowNodeEditModal(true);
    };

    window.addEventListener('show-node-edit-modal', handleShowNodeEditModal as EventListener);

    // Send ready message to indicate the webview is loaded
    if (window.vscode) {
      window.vscode.postMessage({ type: 'ready' });
    }

    return () => {
      window.removeEventListener('message', handleMessage);
      window.removeEventListener('show-node-edit-modal', handleShowNodeEditModal as EventListener);
    };
  }, [sessionId]);

  // Reset graph ready state when graph data changes and set a short delay
  useEffect(() => {
    if (graphData) {
      setIsGraphReady(false);
      // Use a shorter, more reasonable delay
      const timeout = setTimeout(() => {
        setIsGraphReady(true);
      }, 100); // Much shorter delay
      
      return () => clearTimeout(timeout);
    }
  }, [graphData]);

  const handleNodeUpdate = (
    nodeId: string,
    field: string,
    value: string,
    sessionIdParam?: string,
    attachments?: any
  ) => {
    const currentSessionId = sessionIdParam || sessionId;
    if (currentSessionId && window.vscode) {
      const baseMsg = {
        session_id: currentSessionId,
        node_id: nodeId,
        value,
        ...(attachments && { attachments }),
      };
      
      if (field === "input") {
        window.vscode.postMessage({ type: "edit_input", ...baseMsg });
      } else if (field === "output") {
        window.vscode.postMessage({ type: "edit_output", ...baseMsg });
      } else {
        window.vscode.postMessage({
          type: "updateNode",
          session_id: currentSessionId,
          nodeId,
          field,
          value,
          ...(attachments && { attachments }),
        });
      }
    }
  };


  if (!experiment || !sessionId) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: isDarkTheme ? "#252525" : "#F0F0F0",
          color: "var(--vscode-editor-foreground)"
        }}
      >
      </div>
    );
  }

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

      {/* Main content area */}
      <div
        style={{
          flex: 1,
          overflow: "hidden",
          display: "flex",
          flexDirection: "row",
        }}
      >
        {/* Graph View */}
        {graphData && (
          <div style={{ flex: 1, overflow: "auto", position: "relative", minWidth: 0 }}>
            {/* Loading overlay */}
            {!isGraphReady && (
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: "var(--vscode-editor-background)",
                  zIndex: 1000,
                }}
              />
            )}
            
            {/* Graph (always rendered, but hidden until ready) */}
            <div 
              style={{ 
                width: "100%", 
                height: "100%",
                visibility: isGraphReady ? "visible" : "hidden" 
              }}
            >
              <GraphView
                nodes={graphData.nodes || []}
                edges={graphData.edges || []}
                onNodeUpdate={(nodeId, field, value) => {
                  const nodes = graphData.nodes || [];
                  const node = nodes.find((n: any) => n.id === nodeId);
                  const attachments = node?.attachments || undefined;
                  handleNodeUpdate(
                    nodeId,
                    field,
                    value,
                    sessionId,
                    attachments
                  );
                }}
                session_id={sessionId}
                experiment={experiment}
                messageSender={messageSender}
                isDarkTheme={isDarkTheme}
              />
            </div>
          </div>
        )}

        {/* Metadata Panel - Always visible on right side */}
        {experiment && (
          <div
            style={{
              width: '350px',
              borderLeft: `1px solid ${isDarkTheme ? '#3c3c3c' : '#e0e0e0'}`,
              overflow: 'auto',
              flexShrink: 0,
            }}
          >
            <WorkflowRunDetailsPanel
              runName={experiment.run_name || experiment.session_id}
              result={experiment.result || ''}
              notes={experiment.notes || ''}
              log={experiment.log || ''}
              sessionId={sessionId || ''}
            />
          </div>
        )}

        {/* Node Edit Modal */}
        {showNodeEditModal && nodeEditData && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10001, // Higher than run details modal
            }}
            onMouseDown={(e) => {
              if (e.target === e.currentTarget) {
                setShowNodeEditModal(false);
              }
            }}
          >
            <div
              style={{
                backgroundColor: 'var(--vscode-editor-background)',
                border: '1px solid var(--vscode-editorWidget-border)',
                borderRadius: '6px',
                width: 'auto',
                height: 'auto',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <NodeEditModal
                nodeId={nodeEditData.nodeId}
                field={nodeEditData.field}
                label={nodeEditData.label}
                value={nodeEditData.value}
                onClose={() => setShowNodeEditModal(false)}
                onSave={(nodeId, field, value) => {
                  // Send the update using the existing handleNodeUpdate function
                  const nodes = graphData?.nodes || [];
                  const node = nodes.find((n: any) => n.id === nodeId);
                  const attachments = node?.attachments || undefined;
                  handleNodeUpdate(nodeId, field, value, sessionId, attachments);
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};