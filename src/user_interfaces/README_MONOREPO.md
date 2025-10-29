# User Interface Monorepo

This directory has been restructured as an npm workspace monorepo containing:

## Structure

```
src/user_interfaces/
├── package.json           # Root workspace configuration
├── vscode_extension/      # VS Code extension workspace
│   ├── src/
│   ├── package.json
│   └── webpack.config.js
└── web_app/               # Web application workspace
    ├── client/            # Vite + React frontend
    │   ├── src/
    │   └── package.json   # Now references vscode_extension as workspace dependency
    ├── server.js          # Express backend
    └── package.json

```

## What Changed

1. **Monorepo Setup**: The VS Code extension and webapp are now separate workspaces under a single root
2. **Shared Dependencies**: React, ReactFlow, and other common dependencies are hoisted to the root
3. **Workspace References**: The webapp client now imports from the extension using `vscode-graph-extension` package name
4. **Consistent Dependencies**: All workspaces share the same dependency versions

## Installation

From the `src/user_interfaces/` directory, run:

```bash
npm install
```

This single command will:
- Install all dependencies for all workspaces
- Create symlinks between workspaces
- Hoist common dependencies to the root `node_modules`

## Building

### Build Everything
```bash
npm run build:all
```

### Build VS Code Extension
```bash
npm run build:extension
```

### Build Webapp Client
```bash
npm run build:webapp-client
```

### Run Webapp Client in Dev Mode
```bash
npm run dev:webapp-client
```

## Publishing the VS Code Extension

The extension can still be packaged and published normally:

```bash
cd vscode_extension
vsce package
vsce publish
```

The `.vscodeignore` file ensures the webapp is excluded from the `.vsix` package.

## Import Changes

The webapp client now imports shared components using the workspace package name:

**Before:**
```typescript
import { GraphView } from "../../../src/webview/components/GraphView";
```

**After:**
```typescript
import { GraphView } from "vscode-graph-extension/src/webview/components/GraphView";
```

## Benefits

1. ✅ Single `npm install` for both projects
2. ✅ Shared dependencies (saves ~200MB disk space)
3. ✅ Consistent versions across projects
4. ✅ Easier development workflow
5. ✅ No impact on VS Code extension publishing

## Troubleshooting

If you encounter issues:

1. **Clean install**: `npm run clean && npm install`
2. **Check workspace links**: `npm ls --workspaces`
3. **Rebuild extension**: `cd vscode_extension && npm run compile`

## Old Structure

The previous structure has been backed up to `src/user_interfaces_old/` (if you need to reference it).
