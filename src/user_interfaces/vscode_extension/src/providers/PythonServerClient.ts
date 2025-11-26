import * as net from 'net';
import * as child_process from 'child_process';
import * as vscode from 'vscode';

export class PythonServerClient {
    private static instance: PythonServerClient;
    private client: any = undefined;
    private messageQueue: string[] = [];
    private onMessageCallback?: (msg: any) => void;
    private userId?: string;
    private serverHost: string;
    private serverPort: number;
    private serverUrl?: string;
    private useWebSocket = false;
    private reconnecting = false;
    private reconnectTimer: NodeJS.Timeout | undefined;

    private constructor() {
        // Read server configuration from VSCode settings
        const config = vscode.workspace.getConfiguration('agopsAgentCopilot');
        this.serverHost = config.get('pythonServerHost') || '127.0.0.1';
        this.serverPort = config.get('pythonServerPort') || 5959;
        this.serverUrl = config.get('pythonServerUrl');
        this.useWebSocket = !!(this.serverUrl && typeof this.serverUrl === 'string' && this.serverUrl.startsWith('ws'));

        this.connect();
    }

    public static getInstance(): PythonServerClient {
        return PythonServerClient.instance ??= new PythonServerClient();
    }

    public setUserId(userId: string | undefined) {
        this.userId = userId;
    }

    private connect() {
        if (this.reconnecting) {
            console.log('[PythonServerClient] Reconnection already in progress, skipping duplicate attempt');
            return;
        }

        if (this.useWebSocket && this.serverUrl) {
            this.connectWebSocket(this.serverUrl);
            return;
        }

        console.log(`[PythonServerClient] Connecting to ${this.serverHost}:${this.serverPort}`);
        this.client = new net.Socket();
        this.client.connect(this.serverPort, this.serverHost, async () => {
            // Get current user_id if authenticated
            let userId = this.userId;

            // Try to get from authentication if not already set
            if (!userId) {
                try {
                    const session = await vscode.authentication.getSession('google', [], { createIfNone: false });
                    if (session) {
                        userId = session.account.id;
                    }
                } catch (e) {
                    // User not authenticated, continue without user_id
                }
            }

            const handshake: any = {
                type: "hello",
                role: "ui",
                script: "vscode-extension"
            };

            // Add user_id to handshake if authenticated
            if (userId) {
                handshake.user_id = userId;
            }

            this.client.write(JSON.stringify(handshake) + "\n");
            this.messageQueue.forEach(msg => this.client.write(msg));
            this.messageQueue = [];
        });

        let buffer = '';
        this.client.on('data', (data: Buffer) => {
            buffer += data.toString();
            let idx;
            while ((idx = buffer.indexOf('\n')) !== -1) {
                const line = buffer.slice(0, idx);
                buffer = buffer.slice(idx + 1);
                try {
                    const msg = JSON.parse(line);
                    this.onMessageCallback?.(msg);
                } catch (e) {
                    console.error('Failed to parse message from backend', e);
                }
            }
        });

        this.client.on('close', () => {
            console.log('[PythonServerClient] TCP connection closed, will retry in 2s');
            this.scheduleReconnect();
        });

        this.client.on('error', (err: any) => {
            console.error('[PythonServerClient] TCP connection error:', err?.message || err);
            this.scheduleReconnect();
        });
    }

    private connectWebSocket(url: string) {
        // lazy-require 'ws' to keep environment flexible
        let WS: any = null;
        try {
            // eslint-disable-next-line @typescript-eslint/no-var-requires
            WS = require('ws');
        } catch (e) {
            console.error('[PythonServerClient] WebSocket library "ws" not installed. Install with `npm install ws`');
            // fallback to TCP connect
            this.useWebSocket = false;
            this.connect();
            return;
        }

        console.log(`[PythonServerClient] Connecting to WebSocket ${url}`);
        this.client = new WS(url);

        this.client.on('open', async () => {
            console.log('[PythonServerClient] WebSocket connected');
            this.reconnecting = false;
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = undefined;
            }

            let userId = this.userId;
            if (!userId) {
                try {
                    const session = await vscode.authentication.getSession('google', [], { createIfNone: false });
                    if (session) userId = session.account.id;
                } catch (e) {}
            }

            const handshake: any = { type: 'hello', role: 'ui', script: 'vscode-extension' };
            if (userId) handshake.user_id = userId;

            this.client.send(JSON.stringify(handshake));
            this.messageQueue.forEach(msg => this.client.send(msg));
            this.messageQueue = [];
        });

        this.client.on('message', (data: any) => {
            try {
                const text = data.toString();
                // accept multiple newline-delimited messages in one frame
                const parts = text.split('\n').filter(Boolean);
                for (const part of parts) {
                    try {
                        const msg = JSON.parse(part);
                        this.onMessageCallback?.(msg);
                    } catch (err) {
                        // ignore non-JSON messages (logs, HTML, etc.) but keep a short warning
                        try { console.warn('[PythonServerClient] Ignored non-JSON WS message:', part.slice(0,200)); } catch {};
                    }
                }
            } catch (e) {
                console.error('Failed to handle WS message', e);
            }
        });

        this.client.on('close', () => {
            console.log('[PythonServerClient] WebSocket closed, will retry in 2s');
            this.scheduleReconnect();
        });
        
        this.client.on('error', (err: any) => {
            console.error('[PythonServerClient] WebSocket error:', err?.message || err);
            this.scheduleReconnect();
        });
    }

    public sendMessage(message: any) {
        const msgStr = JSON.stringify(message) + "\n";
        // WebSocket client (ws) has send() and numeric readyState
        if (this.client) {
            // WebSocket
            if (typeof this.client.send === 'function') {
                const isOpen = (typeof this.client.readyState === 'number' && this.client.readyState === 1); // 1 === OPEN
                if (isOpen) {
                    try { this.client.send(msgStr); } catch (e) { this.messageQueue.push(msgStr); }
                } else {
                    this.messageQueue.push(msgStr);
                }
                return;
            }

            // TCP socket (net.Socket)
            if (typeof this.client.write === 'function') {
                if (this.client.writable) {
                    try { this.client.write(msgStr); } catch (e) { this.messageQueue.push(msgStr); }
                } else {
                    this.messageQueue.push(msgStr);
                }
                return;
            }
        }

        // fallback: queue message
        this.messageQueue.push(msgStr);
    }

    public startServerIfNeeded() {
        child_process.spawn('python', ['src/server/develop_server.py', 'start'], {
            detached: true,
            stdio: 'ignore'
        }).unref();
    }

    public stopServer() {
        this.sendMessage({ type: "shutdown" });
    }

    public onMessage(cb: (msg: any) => void) {
        this.onMessageCallback = cb;
    }

    private scheduleReconnect() {
        if (this.reconnecting) {
            return; // Already scheduled
        }
        
        this.reconnecting = true;
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnecting = false;
            this.reconnectTimer = undefined;
            this.connect();
        }, 2000);
    }
} 