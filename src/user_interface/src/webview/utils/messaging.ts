import { NodeUpdateMessage, GraphNode } from '../types';

declare const vscode: any;

export function sendMessage(message: any) {
    console.log("[UI] sendMessage called with:", message);
    console.log("[UI] About to call vscode.postMessage with:", message);
    vscode.postMessage(message);
    console.log("[UI] vscode.postMessage called successfully");
}

export function sendNodeUpdate(nodeId: string, field: keyof GraphNode, value: string, session_id?: string) {
    const msg = {
        type: 'updateNode',
        nodeId,
        field,
        value,
        session_id
    };
    console.log('[UI] Sending node update message:', msg);
    sendMessage(msg);
}

export function sendReady() {
    vscode.postMessage({
        type: 'ready'
    });
}

export function sendNavigateToCode(codeLocation: string) {
    vscode.postMessage({
        type: 'navigateToCode',
        payload: { codeLocation }
    });
}

export function sendReset() {
    sendMessage({ type: 'reset', id: Math.floor(Math.random() * 100000) });
}