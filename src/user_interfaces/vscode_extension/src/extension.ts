import * as vscode from 'vscode';
import { SidebarProvider } from './providers/SidebarProvider';
import { GraphTabProvider } from './providers/GraphTabProvider';
import { GoogleAuthenticationProvider } from './providers/GoogleAuthenticationProvider';
import { PythonServerClient } from './providers/PythonServerClient';
import { AuthManager } from './providers/AuthManager';

export async function activate(context: vscode.ExtensionContext) {
    // Register Google Authentication Provider
    const googleAuthProvider = new GoogleAuthenticationProvider(context);
    context.subscriptions.push(googleAuthProvider);

    // Initialize AuthManager and set the auth provider
    const authManager = AuthManager.getInstance(context);
    authManager.setAuthProvider(googleAuthProvider);

    // Create and connect the Python client
    // ensureConnected() will check for authentication before connecting
    const pythonClient = PythonServerClient.getInstance();
    await pythonClient.ensureConnected();

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

    // Register the sidebar provider
    const sidebarProvider = new SidebarProvider(context.extensionUri, context);

    // Register the graph tab provider
    const graphTabProvider = new GraphTabProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider)
    );

    context.subscriptions.push(
        vscode.window.registerWebviewPanelSerializer(GraphTabProvider.viewType, graphTabProvider)
    );

    // Connect sidebar and graph tab providers
    sidebarProvider.setGraphTabProvider(graphTabProvider);

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