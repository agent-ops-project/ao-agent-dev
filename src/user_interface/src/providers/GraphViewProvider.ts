import * as vscode from 'vscode';
import { EditDialogProvider } from './EditDialogProvider';
import { NotesLogTabProvider } from './NotesLogTabProvider';
import { PythonServerClient } from './PythonServerClient';

export class GraphViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'graphExtension.graphView';
    private _view?: vscode.WebviewView;
    private _editDialogProvider?: EditDialogProvider;
    private _notesLogTabProvider?: NotesLogTabProvider;
    private _pendingMessages: any[] = [];
    private _pythonClient: PythonServerClient | null = null;
    // The Python server connection is deferred until the webview sends 'ready'.
    // Buffering is needed to ensure no messages are lost if the server sends messages before the webview is ready.

    constructor(private readonly _extensionUri: vscode.Uri) {
        // Set up Python server message forwarding with buffering
        // Removed _pendingEdit
    }

    public setNotesLogTabProvider(provider: NotesLogTabProvider): void {
        this._notesLogTabProvider = provider;
    }

    // Robustly show or reveal the webview
    public showWebview(context: vscode.ExtensionContext) {
        if (!this._view || (this._view as any)._disposed) {
            // Create new webview view
            vscode.commands.executeCommand('workbench.view.extension.graphExtension-sidebar');
            // The view will be resolved via resolveWebviewView
        } else {
            this._view.show?.(true);
        }
    }

    public setEditDialogProvider(provider: EditDialogProvider): void {
        this._editDialogProvider = provider;
    }

    public handleEditDialogSave(value: string, context: { nodeId: string; field: string; session_id?: string; attachments?: any }): void {
        if (this._view) {
            this._view.webview.postMessage({
                type: 'updateNode',
                payload: {
                    nodeId: context.nodeId,
                    field: context.field,
                    value,
                    session_id: context.session_id, // should be present!
                }
            });
        } else {
            console.warn('Tried to send message to disposed or missing webview');
        }
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        // Clean up reference when disposed
        webviewView.onDidDispose(() => {
            this._view = undefined;
        });

        // Flush any pending messages to the webview
        this._pendingMessages.forEach(msg => {
            if (this._view) {
                this._view.webview.postMessage(msg);
            }
        });
        this._pendingMessages = [];

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
        this._sendCurrentTheme();
        vscode.window.onDidChangeActiveColorTheme(() => {
            this._sendCurrentTheme();
        });

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(data => {
            if (data.type === 'restart') {
                if (!data.session_id) {
                    console.error('Restart message missing session_id! Not forwarding to Python server.');
                    return;
                }
                if (this._pythonClient) {
                    this._pythonClient.sendMessage({ type: 'restart', session_id: data.session_id });
                }
            }
            switch (data.type) {
                case 'open_notes_tab_side_by_side':
                    if (this._notesLogTabProvider) {
                        this._notesLogTabProvider.openNotesTab(data.payload);
                    } else {
                        console.error('NotesLogTabProvider instance not set!');
                    }
                    break;
                case 'open_log_tab_side_by_side':
                    if (this._notesLogTabProvider) {
                        this._notesLogTabProvider.openLogTab(data.payload);
                    } else {
                        console.error('NotesLogTabProvider instance not set!');
                    }
                    break;
                case 'updateNode':
                    if (this._pythonClient) {
                        this._pythonClient.sendMessage(data);
                    }
                    break;
                case 'edit_input':
                    if (this._pythonClient) {
                        this._pythonClient.sendMessage(data);
                    }
                    break;
                case 'edit_output':
                    if (this._pythonClient) {
                        this._pythonClient.sendMessage(data);
                    }
                    break;
                case 'get_graph':
                    if (this._pythonClient) {
                        this._pythonClient.sendMessage(data);
                    }
                    break;
                case 'ready':
                    // Webview is ready - now connect to the Python server and set up message forwarding
                    if (!this._pythonClient) {
                        this._pythonClient = PythonServerClient.getInstance();
                        // Forward all messages from the Python server to the webview, buffer if not ready
                        this._pythonClient.onMessage((msg) => {
                            if (this._view) {
                                this._view.webview.postMessage(msg);
                            } else {
                                this._pendingMessages.push(msg);
                            }
                        });
                        this._pythonClient.startServerIfNeeded();
                    }
                    break;
                case 'navigateToCode':
                    // Handle code navigation
                    const { filePath, line } = this._parseCodeLocation(data.payload.codeLocation);
                    if (filePath && line) {
                        vscode.workspace.openTextDocument(filePath).then(document => {
                            vscode.window.showTextDocument(document, {
                                selection: new vscode.Range(line - 1, 0, line - 1, 0)
                            });
                        });
                    }
                    break;
                case 'showEditDialog':
                    if (this._editDialogProvider) {
                        // Show the edit dialog with the provided data
                        this._editDialogProvider.show(
                            `${data.payload.label} ${data.payload.field === 'input' ? 'Input' : 'Output'}`,
                            data.payload.value,
                            {
                                nodeId: data.payload.nodeId,
                                field: data.payload.field,
                                session_id: data.payload.session_id,
                                attachments: data.payload.attachments
                            }
                        );
                    }
                    break;
                case 'erase':
                    if (this._pythonClient) {
                        this._pythonClient.sendMessage(data);
                    }
                    break;
            }
        });
    }

    private _sendCurrentTheme() {
        const isDark = vscode.window.activeColorTheme.kind === vscode.ColorThemeKind.Dark;
        this._view?.webview.postMessage({
            type: 'vscode-theme-change',
            payload: {
                theme: isDark ? 'vscode-dark' : 'vscode-light',
            },
        });
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        const fs = require('fs');
        const path = require('path');
        const os = require('os');
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'dist', 'webview.js'));
        const templatePath = path.join(
            this._extensionUri.fsPath,
            'src',
            'webview',
            'templates',
            'graphView.html'
        );
        let html = fs.readFileSync(templatePath, 'utf8');
        
        // Try to read telemetry configuration from global config file
        let supabaseUrl: string | undefined;
        let supabaseKey: string | undefined;
        let userId: string | undefined;
        
        try {
            const configPath = path.join(os.homedir(), '.cache', 'agent-copilot', 'config.yaml');
            console.log('🔍 Trying to read config from:', configPath);
            
            if (fs.existsSync(configPath)) {
                const configContent = fs.readFileSync(configPath, 'utf8');
                console.log('📄 Config file content:', configContent);
                
                // Simple YAML parsing for our specific format
                const lines = configContent.split('\n');
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (trimmed.startsWith('SUPABASE_URL:')) {
                        supabaseUrl = trimmed.split('SUPABASE_URL:')[1].trim();
                    } else if (trimmed.startsWith('SUPABASE_ANON_KEY:')) {
                        supabaseKey = trimmed.split('SUPABASE_ANON_KEY:')[1].trim();
                    } else if (trimmed.startsWith('USER_ID:')) {
                        userId = trimmed.split('USER_ID:')[1].trim();
                    }
                }
                console.log('✅ Parsed config from YAML:', {
                    supabaseUrl: supabaseUrl ? 'present' : 'missing',
                    supabaseKey: supabaseKey ? 'present' : 'missing',
                    userId
                });
            } else {
                console.log('❌ Config file not found at:', configPath);
            }
        } catch (error) {
            console.error('❌ Error reading config file:', error);
        }
        
        // Fallback to VS Code settings or environment variables if config file doesn't have the values
        const config = vscode.workspace.getConfiguration('agent-copilot');
        supabaseUrl = supabaseUrl || config.get('telemetry.supabaseUrl') || process.env.SUPABASE_URL;
        supabaseKey = supabaseKey || config.get('telemetry.supabaseKey') || process.env.SUPABASE_ANON_KEY;
        userId = userId || config.get('telemetry.userId') || process.env.USER_ID || 'default_user';
        
        // Debug logging
        console.log('🔧 GraphViewProvider final telemetry config:', {
            finalUrl: supabaseUrl ? 'present' : 'missing',
            finalKey: supabaseKey ? 'present' : 'missing',
            finalUserId: userId
        });
        
        // Inject telemetry configuration
        const telemetryConfig = `
            window.SUPABASE_URL = ${supabaseUrl ? `"${supabaseUrl}"` : 'undefined'};
            window.SUPABASE_ANON_KEY = ${supabaseKey ? `"${supabaseKey}"` : 'undefined'};
            window.USER_ID = "${userId}";
        `;
        
        console.log('🚀 Injecting telemetry config into webview');
        
        html = html.replace('const vscode = acquireVsCodeApi();', 
            `${telemetryConfig}\n        const vscode = acquireVsCodeApi();`);
        html = html.replace(/{{scriptUri}}/g, scriptUri.toString());
        return html;
    }

    private _parseCodeLocation(codeLocation: string): { filePath: string | undefined; line: number | undefined } {
        const match = codeLocation.match(/(.+):(\d+)/);
        if (match) {
            const [, filePath, lineStr] = match;
            return {
                filePath,
                line: parseInt(lineStr, 10)
            };
        }
        return { filePath: undefined, line: undefined };
    }
}