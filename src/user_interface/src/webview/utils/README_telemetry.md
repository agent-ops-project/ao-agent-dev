# UI Telemetry Implementation

This document describes the telemetry implementation for tracking user interactions in the TypeScript UI components.

## Overview

The telemetry system tracks two main types of events:
1. **Experiment List Clicks**: When users click on experiment cards in the ExperimentsView
2. **Node Input/Output Views**: When users view input or output content of graph nodes

## Architecture

### Files Added/Modified

- `src/webview/utils/telemetry.ts` - Main telemetry client using Supabase
- `src/webview/utils/config.ts` - Configuration management for credentials
- `src/webview/components/ProcessCard.tsx` - Added experiment click tracking
- `src/webview/components/CustomNode.tsx` - Added node input/output view tracking
- `src/providers/GraphViewProvider.ts` - Injects configuration into webview
- `package.json` - Added `@supabase/supabase-js` dependency

### Configuration

The telemetry system gets its configuration from:

1. **VS Code Settings** (preferred):
   ```json
   {
     "agent-copilot.telemetry.supabaseUrl": "your-supabase-url",
     "agent-copilot.telemetry.supabaseKey": "your-anon-key",
     "agent-copilot.telemetry.userId": "user-identifier"
   }
   ```

2. **Environment Variables** (fallback):
   ```bash
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-anon-key
   USER_ID=user-identifier
   ```

### Events Tracked

#### 1. Experiment Click
- **Event Type**: `experiment_click`
- **Trigger**: User clicks on a ProcessCard in ExperimentsView
- **Data**: `{ experiment_name: string }`

#### 2. Node Input/Output View
- **Event Type**: `node_input_output_view`
- **Trigger**: User clicks "Edit Input" or "Edit Output" on a graph node
- **Data**: `{ node_id: string, view_type: 'input'|'output', node_type: string }`

## Database Schema

Events are stored in the `user_actions` table with the following structure:
```sql
CREATE TABLE user_actions (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id TEXT,
  event_type TEXT NOT NULL,
  event_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Usage

The telemetry functions are imported and called automatically in the relevant components:

```typescript
import { trackExperimentClick, trackNodeInputOutputView } from '../utils/telemetry';

// Track experiment click
await trackExperimentClick(experimentName, sessionId);

// Track node input/output view
await trackNodeInputOutputView(nodeId, 'input', sessionId, nodeType);
```

## Error Handling

- If Supabase credentials are not configured, telemetry is silently disabled
- Failed telemetry calls are logged to console but don't interrupt UI functionality
- All telemetry calls are asynchronous and non-blocking

## Privacy & Performance

- All telemetry data is sent asynchronously without blocking UI interactions
- Only essential interaction data is collected (no content or sensitive information)
- Users can disable telemetry by not providing Supabase configuration 