"""Example: instrument a raw Anthropic SDK agent with TraceGrade.

Usage:
    pip install anthropic tracegrade-sdk
    export ANTHROPIC_API_KEY=sk-...
    python agent.py
"""

import anthropic

from tracegrade_sdk import instrument

# --- 3 lines to instrument ---
instrument(
    service_name="example-agent",
    endpoint="http://localhost:8000/v1/traces",
    session_id="example-session-001",
)

# --- Normal agent code below (unchanged) ---

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_time",
        "description": "Get the current time for a timezone",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "IANA timezone"},
            },
            "required": ["timezone"],
        },
    },
]


def handle_tool(name: str, input: dict) -> str:
    if name == "get_weather":
        return f"72F and sunny in {input['location']}"
    if name == "get_time":
        return f"2:30 PM in {input['timezone']}"
    return "Unknown tool"


def run_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return response.content[0].text

        # Handle tool use
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = handle_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    answer = run_agent("What's the weather in San Francisco and the current time in UTC?")
    print(f"Agent response: {answer}")
