import WebSocket from 'ws';
import * as child_process from 'child_process';

export class PythonServerClient {
    private static instance: PythonServerClient;
    private client: WebSocket | null = null;
    private isConnected = false;
    private messageQueue: string[] = [];
    private reconnectTimeout: NodeJS.Timeout | null = null;
    private onMessageCallback: ((msg: any) => void) | null = null;

    private constructor() {
        this.connect();
    }

    public static getInstance(): PythonServerClient {
        if (!PythonServerClient.instance) {
            PythonServerClient.instance = new PythonServerClient();
        }
        return PythonServerClient.instance;
    }

    private connect() {
        this.client = new WebSocket('ws://127.0.0.1:4000');
        
        this.client.on('open', () => {
            this.isConnected = true;
            // Send handshake
            this.sendRaw(JSON.stringify({
                type: "hello",
                role: "ui",
                script: "vscode-extension"
            }));
            // Flush any queued messages
            while (this.messageQueue.length > 0) {
                this.sendRaw(this.messageQueue.shift()!);
            }
        });

        this.client.on('message', (data) => {
            try {
                const msg = JSON.parse(data.toString());
                if (this.onMessageCallback) {
                    this.onMessageCallback(msg);
                }
            } catch (e) {
                // Ignore parse errors
            }
        });

        this.client.on('close', () => {
            this.isConnected = false;
            this.scheduleReconnect();
        });

        this.client.on('error', (err) => {
            this.isConnected = false;
            this.scheduleReconnect();
        });
    }

    private scheduleReconnect() {
        if (this.reconnectTimeout) return;
        this.reconnectTimeout = setTimeout(() => {
            this.reconnectTimeout = null;
            this.connect();
        }, 2000);
    }

    private sendRaw(message: string) {
        if (this.isConnected && this.client && this.client.readyState === WebSocket.OPEN) {
            this.client.send(message);
        } else {
            this.messageQueue.push(message);
        }
    }

    public sendMessage(message: any) {
        const msgStr = JSON.stringify(message);        
        this.sendRaw(msgStr);
    }

    public startServerIfNeeded() {
        // Start the Python TCP server
        const pythonProc = child_process.spawn('python', ['src/server/develop_server.py', 'start'], {
            detached: true,
            stdio: 'ignore'
        });
        pythonProc.unref();

        // Start the WebSocket bridge server
        const wsProc = child_process.spawn('node', ['src/webapp/server.js'], {
            detached: true,
            stdio: 'ignore'
        });
        wsProc.unref();
    }

    public stopServer() {
        this.sendMessage({ type: "shutdown" });
    }

    public onMessage(cb: (msg: any) => void) {
        this.onMessageCallback = cb;
    }
} 
