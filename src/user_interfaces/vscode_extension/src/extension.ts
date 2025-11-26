import * as vscode from 'vscode';
import { GraphViewProvider } from './providers/GraphViewProvider';
import { EditDialogProvider } from './providers/EditDialogProvider';
import { NotesLogTabProvider } from './providers/NotesLogTabProvider';
import { GoogleAuthenticationProvider } from './providers/GoogleAuthenticationProvider';
import { PythonServerClient } from './providers/PythonServerClient';
import { AuthManager } from './providers/AuthManager';

export function activate(context: vscode.ExtensionContext) {
    // Register Google Authentication Provider
    const googleAuthProvider = new GoogleAuthenticationProvider(context);
    context.subscriptions.push(googleAuthProvider);

    // Initialize AuthManager and set the auth provider
    const authManager = AuthManager.getInstance(context);
    authManager.setAuthProvider(googleAuthProvider);

    // Monitor authentication changes and update Python client
    context.subscriptions.push(
        vscode.authentication.onDidChangeSessions(async e => {
            if (e.provider.id === 'google') {
                const session = await vscode.authentication.getSession('google', [], { createIfNone: false });
                const pythonClient = PythonServerClient.getInstance();
                
                if (session) {
                    pythonClient.setUserId(session.account.id);
                    // Send auth message to update user_id on existing connection
                    pythonClient.sendMessage({ type: 'auth', user_id: session.account.id });
                } else {
                    pythonClient.setUserId(undefined);
                }
            }
        })
    );

    // Register the webview provider
    const graphViewProvider = new GraphViewProvider(context.extensionUri, context);

    const notesLogTabProvider = new NotesLogTabProvider(context.extensionUri);
    graphViewProvider.setNotesLogTabProvider(notesLogTabProvider);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(GraphViewProvider.viewType, graphViewProvider)
    );

    // --- Close any orphaned edit dialog panels left open after reload ---
    // VS Code does not expose all webview panels directly, but we can close tabs and also try to dispose panels tracked by our provider
    if ((vscode.window as any).tabGroups) {
        const tabGroups = (vscode.window as any).tabGroups.all;
        for (const group of tabGroups) {
            for (const tab of group.tabs) {
                if (tab.input && tab.input.viewType === EditDialogProvider.viewType) {
                    vscode.window.tabGroups.close(tab).then(() => {},
                        (err) => { console.warn('[EXTENSION] Failed to close tab:', tab.label, err); }
                    );
                }
            }
        }
    }

    // Register the edit dialog provider
    const editDialogProvider = new EditDialogProvider(context.extensionUri, (value: string, contextObj: { nodeId: string; field: string; session_id?: string }) => {
        graphViewProvider.handleEditDialogSave(value, contextObj);
    });
   
    context.subscriptions.push(
        vscode.window.registerWebviewPanelSerializer(EditDialogProvider.viewType, editDialogProvider)
    );

    // Store the edit dialog provider in the graph view provider
    graphViewProvider.setEditDialogProvider(editDialogProvider);

    // Register command to show the graph
    context.subscriptions.push(
        vscode.commands.registerCommand('graphExtension.showGraph', () => {
            vscode.commands.executeCommand('graphExtension.graphView.focus');
        })
    );

    // Register command to sign in
    context.subscriptions.push(
        vscode.commands.registerCommand('graphExtension.signIn', async () => {
            try {
                const session = await vscode.authentication.getSession('google', ['openid', 'email', 'profile'], { createIfNone: true });
                if (session) {
                    vscode.window.showInformationMessage(`Signed in as ${session.account.label}`);
                    // Update Python client with user_id
                    const pythonClient = PythonServerClient.getInstance();
                    pythonClient.setUserId(session.account.id);
                    pythonClient.sendMessage({ type: 'auth', user_id: session.account.id });
                }
            } catch (error) {
                vscode.window.showErrorMessage(`Sign in failed: ${error}`);
            }
        })
    );

    // Register command to sign out
    context.subscriptions.push(
        vscode.commands.registerCommand('graphExtension.signOut', async () => {
            const session = await vscode.authentication.getSession('google', [], { createIfNone: false });
            if (session) {
                await googleAuthProvider.removeSession(session.id);
                vscode.window.showInformationMessage('Signed out successfully');
                // Clear user_id from Python client
                const pythonClient = PythonServerClient.getInstance();
                pythonClient.setUserId(undefined);
            }
        })
    );
}