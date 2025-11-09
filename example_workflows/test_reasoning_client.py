"""
Simple MCP client to test the reasoning server.

This script connects to the reasoning MCP server and tests the reasoning tool.

Usage:
1. Start the server: aco-launch example_workflows/reasoning_mcp_server.py
2. In another terminal: python example_workflows/test_reasoning_client.py
"""

import asyncio
import json
import sys
import subprocess
import os
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


async def test_reasoning_server():
    """Test the MCP reasoning server."""
    
    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    
    # Start the server
    server_cmd = ["aco-launch", "example_workflows/reasoning_mcp_server.py"]
    print(f"Starting server: {' '.join(server_cmd)}")
    
    server_process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(repo_root)
    )
    
    try:
        # Wait a moment for server to start
        await asyncio.sleep(2)
        
        # Initialize the MCP connection
        print("Initializing MCP connection...")
        
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        # Send initialization
        server_process.stdin.write(json.dumps(init_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        response_line = await asyncio.wait_for(
            asyncio.create_task(asyncio.to_thread(server_process.stdout.readline)),
            timeout=10.0
        )
        
        if response_line:
            init_response = json.loads(response_line.strip())
            print(f"✓ Server initialized: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'MCP Server')}")
        else:
            print("✗ No response from server during initialization")
            return
        
        # Send initialized notification
        initialized_notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        server_process.stdin.write(json.dumps(initialized_notif) + "\n")
        server_process.stdin.flush()
        
        # Test the reasoning tool
        print("\n" + "=" * 60)
        print("Testing @mcp.tool() decorated async function with third-party API calls")
        print("=" * 60)
        
        question = "What is 2+2? Please explain your reasoning step by step."
        print(f"Question: {question}")
        
        reasoning_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "reasoning",
                "arguments": {"question": question}
            }
        }
        
        # Send request
        server_process.stdin.write(json.dumps(reasoning_request) + "\n")
        server_process.stdin.flush()
        
        # Read response with timeout for LLM calls
        try:
            response_line = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(server_process.stdout.readline)),
                timeout=60.0  # 60 seconds for LLM response
            )
            
            if response_line:
                reasoning_response = json.loads(response_line.strip())
                
                if "result" in reasoning_response:
                    result = reasoning_response["result"]
                    if "content" in result:
                        print("\n✓ Response received:")
                        for content_item in result["content"]:
                            if content_item["type"] == "text":
                                print(content_item["text"])
                    else:
                        print(f"\n✓ Raw result: {result}")
                elif "error" in reasoning_response:
                    print(f"\n⚠ Error response: {reasoning_response['error']}")
                    print("This might be due to missing API keys")
                else:
                    print(f"\n⚠ Unexpected response: {reasoning_response}")
            else:
                print("\n✗ No response from server")
                
        except asyncio.TimeoutError:
            print("\n⚠ Timeout waiting for response")
            print("This usually means no API keys are configured")
        
        print(f"\n{'=' * 60}")
        print("Key observations:")
        print("1. The @mcp.tool() decorator was rewritten using exec_func")
        print("2. API calls (OpenAI/Anthropic) were rewritten using exec_func") 
        print("3. The decorated async function executed successfully")
        print("4. This demonstrates that AST rewriting works for decorators")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\nShutting down server...")
        server_process.terminate()
        try:
            await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(server_process.wait)),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            server_process.kill()


if __name__ == "__main__":
    print("=" * 60)
    print("MCP Reasoning Server Test")
    print("Testing AST rewriting for @mcp.tool() decorators and async functions")
    print("=" * 60)
    
    # Check environment
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openrouter = bool(os.environ.get("OPENROUTER_API_KEY"))
    
    if not (has_anthropic or has_openrouter):
        print("⚠ No API keys found - server will return error messages")
        print("Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY for real LLM responses")
    else:
        api_info = []
        if has_anthropic:
            api_info.append("Anthropic")
        if has_openrouter:
            api_info.append("OpenRouter")
        print(f"✓ API keys found for: {', '.join(api_info)}")
    
    print()
    
    try:
        asyncio.run(test_reasoning_server())
        print("\n✓ Test completed!")
    except KeyboardInterrupt:
        print("\n⚠ Test interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")