# Telemetry Debug Guide

## Step 1: Configure VS Code Settings

The credentials in `telemetry-settings.json` are just a template. You need to copy them to your **VS Code User Settings**:

1. **Open VS Code Settings**: `Cmd+,` (Mac) or `Ctrl+,` (Windows/Linux)
2. **Click "Open Settings (JSON)"** (top-right icon)
3. **Add these lines** to your `settings.json`:

```json
{
  "agent-copilot.telemetry.supabaseUrl": "https://whkpqpoqntwaraiwssga.supabase.co",
  "agent-copilot.telemetry.supabaseKey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indoa3BxcG9xbnR3YXJhaXdzc2dhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1MDUzMzcsImV4cCI6MjA3MTA4MTMzN30.SZQ_V8rOZXY2GZW0gaxP8K_bWUVKkMvm_SWCBok49V0",
  "agent-copilot.telemetry.userId": "test_user"
}
```

## Step 2: Check Developer Tools

1. **Open Extension Development Host** (when testing the extension)
2. **Open Developer Tools**: `Cmd+Option+I` (Mac) or `F12` (Windows/Linux)
3. **Go to Console tab**
4. **Look for telemetry logs** starting with:
   - 🔧 Initializing telemetry client...
   - 📋 Telemetry config:
   - 🎯 trackExperimentClick called:
   - ✅ UI event logged successfully:

## Step 3: Test Configuration Injection

Add this to your console to check if config is injected:

```javascript
console.log('Window globals:', {
  SUPABASE_URL: window.SUPABASE_URL,
  SUPABASE_ANON_KEY: window.SUPABASE_ANON_KEY ? 'SET' : 'MISSING',
  USER_ID: window.USER_ID
});
```

## Step 4: Manual Test

Try this in the Developer Tools console:

```javascript
// Import and test telemetry directly
import('/src/webview/utils/telemetry.js').then(async (telemetry) => {
  console.log('Testing telemetry...');
  const result = await telemetry.trackExperimentClick('test_experiment', 'test_session');
  console.log('Test result:', result);
});
```

## Step 5: Check Database

In Supabase dashboard:

1. Go to **Table Editor**
2. Select **ui_events** table
3. Check if any rows appear after interactions

## Common Issues

### 1. Settings Not Applied
- **Solution**: Restart VS Code after adding settings
- **Check**: VS Code settings are in User Settings, not Workspace Settings

### 2. Extension Not Injecting Config
- **Solution**: Make sure you're testing in the Extension Development Host
- **Check**: Console should show "🔧 Initializing telemetry client..."

### 3. Database Connection Issues
- **Solution**: Verify Supabase URL and key are correct
- **Check**: Error messages in console about Supabase connection

### 4. CORS Issues
- **Solution**: Make sure your Supabase project allows requests from VS Code
- **Check**: Network tab in Developer Tools for failed requests

## Debug Environment Variables (Alternative)

If VS Code settings don't work, try setting environment variables:

```bash
export SUPABASE_URL="https://whkpqpoqntwaraiwssga.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indoa3BxcG9xbnR3YXJhaXdzc2dhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1MDUzMzcsImV4cCI6MjA3MTA4MTMzN30.SZQ_V8rOZXY2GZW0gaxP8K_bWUVKkMvm_SWCBok49V0"
export USER_ID="test_user"
```

Then restart VS Code from that terminal session. 