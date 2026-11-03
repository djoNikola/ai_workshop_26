import asyncio
import json
import os
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MODEL = "gemma4:26b-a4b-it-qat"
WORKSPACE = (Path.home() / "MCP-Workspace").resolve()
MAX_TOOL_ROUNDS = 8

# Require approval before potentially destructive operations.
DESTRUCTIVE_TOOLS = {
    "write_file",
    "edit_file",
    "move_file",
    "delete_file",
    "delete_directory",
}


def confirm_operation(name, arguments):
    """Ask the human to approve a modifying tool call."""
    print(f"\nWARNING: MCP tool '{name}' may change your files.")
    print(json.dumps(arguments, indent=2, ensure_ascii=False))

    try:
        answer = input("Approve this operation? [y/N]: ")
    except (EOFError, KeyboardInterrupt):
        return False

    return answer.strip().lower() == "y"


async def main():
    # 1. Ensure workspace exists
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    # 2. DEFINE THE SERVER HERE
    # This tells the client to run: npx -y
@modelcontextprotocol/server-filesystem <your_workspace_path>
    server = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", str(WORKSPACE)],
        env=os.environ.copy()
    )

    # 3. Start the client
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

            # Map the MCP tools to Ollama's function format
            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": https://urldefense.com/v3/__http://tool.name__;!!LQkDIss!VxMVcMbnsjZ6HQ6g2geqhYT0IHRkXWJWQCny093smmzu6bBM_4lIgOEDjlZyzp4_VHDbfeJ3PHcrbjYc1Dtl5_U$,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in https://urldefense.com/v3/__http://result.tools__;!!LQkDIss!VxMVcMbnsjZ6HQ6g2geqhYT0IHRkXWJWQCny093smmzu6bBM_4lIgOEDjlZyzp4_VHDbfeJ3PHcrbjYcTcqHe7w$
            ]

            available_tools = {https://urldefense.com/v3/__http://tool.name__;!!LQkDIss!VxMVcMbnsjZ6HQ6g2geqhYT0IHRkXWJWQCny093smmzu6bBM_4lIgOEDjlZyzp4_VHDbfeJ3PHcrbjYc1Dtl5_U$ for tool in https://urldefense.com/v3/__http://result.tools__;!!LQkDIss!VxMVcMbnsjZ6HQ6g2geqhYT0IHRkXWJWQCny093smmzu6bBM_4lIgOEDjlZyzp4_VHDbfeJ3PHcrbjYcTcqHe7w$}

            print(f"\nConnected to MCP Server (Filesystem).")
            print(f"Workspace: {WORKSPACE}")
            print("Type 'exit' to quit.")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a local filesystem assistant. "
                        f"Work only within {WORKSPACE}. "
                        "Use filesystem tools when appropriate. "
                        "Do not claim an operation succeeded unless "
                        "the tool result confirms it."
                    ),
                }
            ]

            while True:
                try:
                    user_text = input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye.")
                    break

                if user_text.lower() in {"exit", "quit"}:
                    break
                if not user_text:
                    continue

                messages.append({"role": "user", "content": user_text})

                try:
                    for _ in range(MAX_TOOL_ROUNDS):
                        # Run blocking ollama call in a thread
                        response = await asyncio.to_thread(
                            https://urldefense.com/v3/__http://ollama.chat__;!!LQkDIss!VxMVcMbnsjZ6HQ6g2geqhYT0IHRkXWJWQCny093smmzu6bBM_4lIgOEDjlZyzp4_VHDbfeJ3PHcrbjYcbzfBfkc$,
                            model=MODEL,
                            messages=messages,
                            tools=ollama_tools,
                        )

                        assistant_message = response.message
                        msg_dict =
assistant_message.model_dump(exclude_none=True)
                        messages.append(msg_dict)

                        # Print Chain of Thought / Reasoning if present
                        reasoning = getattr(assistant_message,
'reasoning', None) or getattr(assistant_message, 'thought', None)
                        if reasoning:
                            print(f"\n[CoT] {reasoning}")

                        calls = assistant_message.tool_calls or []

                        if not calls:
                            if assistant_message.content:
                                print(f"\nGemma: {assistant_message.content}")
                            break

                        for call in calls:
                            name = https://urldefense.com/v3/__http://call.function.name__;!!LQkDIss!VxMVcMbnsjZ6HQ6g2geqhYT0IHRkXWJWQCny093smmzu6bBM_4lIgOEDjlZyzp4_VHDbfeJ3PHcrbjYc7NdORJM$
                            arguments = call.function.arguments
                            tool_call_id = getattr(call, 'id', None)

                            print(f"\nMCP tool requested: {name}")

                            if name not in available_tools:
                                output = f"Error: Unknown tool '{name}'"
                            elif name in DESTRUCTIVE_TOOLS and not
confirm_operation(name, arguments):
                                output = "Error: Operation rejected by user."
                            else:
                                try:
                                    tool_result = await
session.call_tool(name, arguments)

                                    content_parts = []
                                    for block in (tool_result.content or []):
                                        if hasattr(block, 'text'):
                                            content_parts.append(block.text)
                                        elif hasattr(block, 'image'):
# Handle images if necessary

content_parts.append(f"[Image Data]")

                                    output = "\n".join(content_parts)

                                    if tool_result.isError:
                                        output = f"Tool Error: {output}"

                                    if not output:
                                        output = "Tool executed successfully (no output)."

                                except Exception as exc:
                                    output = f"Execution failed: {str(exc)}"

                            tool_response = {
                                "role": "tool",
                                "content": output,
                            }
                            if tool_call_id:
                                tool_response["tool_call_id"] = tool_call_id
                            else:
                                tool_response["name"] = name

                            messages.append(tool_response)

                    else:
                        print("\n[System] Maximum tool rounds reached.")

                except Exception as exc:
                    print(f"\n[Error] Loop error: {exc}")


if __name__ == "__main__":
    asyncio.run(main())