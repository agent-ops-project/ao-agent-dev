import * as vscode from 'vscode';
import { SidebarProvider } from './providers/SidebarProvider';
import { GraphTabProvider } from './providers/GraphTabProvider';
// Google auth disabled - feature not yet visible in UI
// import { GoogleAuthenticationProvider } from './providers/GoogleAuthenticationProvider';
import { PythonServerClient } from './providers/PythonServerClient';
// import { AuthManager } from './providers/AuthManager';

export async function activate(context: vscode.ExtensionContext) {
    // testing only
    // await context.globalState.update('hasShownInstallPrompt', undefined);

    // Show installation prompt on first activation via status bar
    const hasShownInstallPrompt = context.globalState.get<boolean>('hasShownInstallPrompt');
    if (!hasShownInstallPrompt) {
        const pipCommand = 'pip install agent-copilot';

        // Status bar that stays until clicked
        const statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            1000 
        );
        statusBarItem.text = '$(terminal) Setup: pip install agent-copilot';
        statusBarItem.tooltip = 'Click to copy install command';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        statusBarItem.command = 'agentCopilot.copyInstallCommand';
        statusBarItem.show();

        // Command to handle click
        const disposable = vscode.commands.registerCommand('agentCopilot.copyInstallCommand', async () => {
            // Hide status bar when clicked
            statusBarItem.dispose();
            await context.globalState.update('hasShownInstallPrompt', true);

            const selection = await vscode.window.showInformationMessage(
                '👋 Run "pip install agent-copilot" to complete setup',
                'Copy Command',
                'Open Terminal'
            );

            if (selection === 'Copy Command') {
                await vscode.env.clipboard.writeText(pipCommand);
                vscode.window.showInformationMessage('Command copied to clipboard!');
            } else if (selection === 'Open Terminal') {
                const terminal = vscode.window.createTerminal('Agent Copilot Setup');
                terminal.show();
                terminal.sendText(pipCommand, false);
            }
        });

        context.subscriptions.push(statusBarItem, disposable);
    }

    // Google Authentication Provider disabled - feature not yet visible in UI
    // const googleAuthProvider = new GoogleAuthenticationProvider(context);
    // context.subscriptions.push(googleAuthProvider);

    // AuthManager disabled - feature not yet visible in UI
    // const authManager = AuthManager.getInstance(context);
    // authManager.setAuthProvider(googleAuthProvider);

    // Create and connect the Python client
    // ensureConnected() will check for authentication before connecting
    const pythonClient = PythonServerClient.getInstance();
    await pythonClient.ensureConnected();

    // Google auth session monitoring disabled - feature not yet visible in UI
    /*
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
    */

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

    // Sign in/out commands disabled - feature not yet visible in UI
    /*
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
    */
}