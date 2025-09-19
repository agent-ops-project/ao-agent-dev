# Shared Components Structure

## Overview
Files that can be shared between VSCode extension and webapp, organized by category.

## Folder Structure

```
shared/
├── components/                 # React components (UI layer)
│   ├── graph/
│   │   ├── CustomNode.tsx     # Node rendering with universal messaging
│   │   ├── GraphView.tsx      # Main graph visualization
│   │   ├── NodeToolbar.tsx    # Node interaction toolbar
│   │   └── EdgeComponents.tsx # Edge rendering components
│   ├── experiment/
│   │   ├── ExperimentList.tsx       # List of experiments/sessions
│   │   ├── ExperimentButton.tsx     # Individual experiment item
│   │   └── WorkflowRunDetailsPanel.tsx # Run details panel
│   ├── ui/
│   │   ├── Sidebar.tsx        # Collapsible sidebar
│   │   ├── ToggleButton.tsx   # Show/hide controls
│   │   └── LoadingSpinner.tsx # Loading states
│   └── preview/
│       ├── PreviewPanel.tsx   # File preview component
│       └── PDFViewer.tsx      # PDF viewing component
│
├── types/                     # TypeScript interfaces & types
│   ├── index.ts              # Main export file
│   ├── graph.ts              # GraphNode, GraphEdge interfaces
│   ├── experiment.ts         # Experiment, Session types
│   ├── messaging.ts          # Message type definitions
│   └── layout.ts             # Layout-related types
│
├── utils/                    # Pure utility functions
│   ├── layout/
│   │   ├── core/
│   │   │   ├── types.ts      # Layout algorithm types
│   │   │   ├── constants.ts  # Layout constants
│   │   │   └── convert.ts    # Data conversion utilities
│   │   ├── logic/
│   │   │   ├── layers.ts     # Layer calculation logic
│   │   │   ├── visualLayers.ts # Visual layer management
│   │   │   ├── bands.ts      # Band layout logic
│   │   │   ├── collisions.ts # Collision detection
│   │   │   ├── edges.ts      # Edge routing logic
│   │   │   ├── dimensions.ts # Size calculations
│   │   │   └── bandsCalc.ts  # Band calculations
│   │   ├── paths/
│   │   │   ├── direct.ts     # Direct path routing
│   │   │   └── bands.ts      # Band-based routing
│   │   └── index.ts          # Main layout engine export
│   ├── nodeLayout.ts         # Node positioning algorithms
│   ├── layoutEngine.ts       # Main layout orchestration
│   ├── timeSpan.ts          # Time formatting utilities
│   ├── layoutConstants.ts    # Layout configuration
│   ├── attachmentHtml.ts     # Attachment handling
│   └── themeUtils.ts         # Theme management utilities
│
├── messaging/                # Universal messaging interface
│   ├── UniversalMessenger.ts # Main messaging class
│   ├── adapters/
│   │   ├── WebSocketAdapter.ts    # Direct WebSocket adapter
│   │   ├── VSCodeAdapter.ts       # VSCode postMessage adapter
│   │   └── BridgeAdapter.ts       # WebSocket bridge adapter
│   ├── types.ts              # Messaging-specific types
│   └── commands.ts           # Command helper functions
│
├── hooks/                    # React hooks
│   ├── useLocalStorage.ts    # Local storage management
│   ├── useMessaging.ts       # Universal messaging hook
│   ├── useGraphData.ts       # Graph data management
│   ├── useExperiments.ts     # Experiment list management
│   └── useTheme.ts           # Theme detection/management
│
└── constants/                # Shared constants
    ├── index.ts              # Main constants export
    ├── ports.ts              # Port configurations
    ├── messageTypes.ts       # Message type constants
    └── ui.ts                 # UI constants (sizes, colors, etc.)
```

## File Details

### Components (`shared/components/`)

**graph/CustomNode.tsx**
- Node rendering with click handlers
- Uses universal messaging for edit dialogs
- Handles input/output display
- Context menu functionality

**graph/GraphView.tsx** 
- Main ReactFlow graph component
- Node/edge positioning
- Zoom/pan controls
- Minimap and background

**experiment/ExperimentList.tsx**
- List of sessions/experiments
- Filter and search functionality
- Status indicators

### Types (`shared/types/`)

**graph.ts**
```typescript
export interface GraphNode {
  id: string;
  label: string;
  input?: string;
  output?: string;
  border_color?: string;
  session_id?: string;
  // ... other properties
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  // ... other properties
}
```

**messaging.ts**
```typescript
export interface BaseMessage {
  type: string;
  session_id?: string;
}

export interface GetGraphMessage extends BaseMessage {
  type: 'get_graph';
  session_id: string;
}

export interface GraphUpdateMessage extends BaseMessage {
  type: 'graph_update';
  payload: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
}
```

### Messaging (`shared/messaging/`)

**UniversalMessenger.ts**
- Environment detection
- Adapter pattern for different messaging systems
- Common command methods (getGraph, editInput, etc.)

**adapters/WebSocketAdapter.ts**
```typescript
export class WebSocketAdapter implements MessageAdapter {
  private ws: WebSocket;
  
  send(message: any): void {
    this.ws.send(JSON.stringify(message));
  }
  
  onMessage(handler: (data: any) => void): void {
    this.ws.onmessage = (event) => {
      handler(JSON.parse(event.data));
    };
  }
}
```

**adapters/VSCodeAdapter.ts**
```typescript
export class VSCodeAdapter implements MessageAdapter {
  send(message: any): void {
    (window as any).vscode.postMessage(message);
  }
  
  onMessage(handler: (data: any) => void): void {
    // Handle VSCode message events
    window.addEventListener('message', (event) => {
      handler(event.data);
    });
  }
}
```

### Utils (`shared/utils/`)

**layout/**: All existing layout logic files
- Pure functions for graph positioning
- No environment dependencies
- Mathematical calculations

**nodeLayout.ts**: Node positioning algorithms
**layoutEngine.ts**: Main layout orchestration  
**timeSpan.ts**: Time formatting utilities

### Hooks (`shared/hooks/`)

**useMessaging.ts**
```typescript
export function useMessaging() {
  const messenger = useRef<UniversalMessenger>();
  
  useEffect(() => {
    messenger.current = new UniversalMessenger();
    messenger.current.autoInit();
  }, []);
  
  const sendMessage = useCallback((msg: any) => {
    messenger.current?.send(msg);
  }, []);
  
  return { sendMessage, messenger: messenger.current };
}
```

## Environment-Specific Files (Not Shared)

**VSCode Extension:**
- `providers/GraphViewProvider.ts` - VSCode webview management
- `providers/EditDialogProvider.ts` - VSCode-specific dialogs
- `extension.ts` - Extension entry point

**Webapp:**
- `main.tsx` - Webapp entry point  
- Direct WebSocket connection setup
- Browser-specific routing

## Migration Strategy

1. **Phase 1**: Extract types and utilities (low risk)
2. **Phase 2**: Create universal messaging interface
3. **Phase 3**: Extract React components with messaging abstraction
4. **Phase 4**: Create shared hooks for state management
5. **Phase 5**: Environment-specific adapters and final integration