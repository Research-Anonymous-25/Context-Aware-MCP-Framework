#wedding_planner_traditional.py

import os
import json
import asyncio
import time
import re
from fastmcp import Client
from openai import OpenAI

def make_json_safe(obj):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return str(obj)

# --- OpenAI client ---
client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"]) 

# --- MCP server config (matching the 3 servers) ---
CONFIG = {
    "mcpServers": {
        "arrival": {"command": "python", "args": ["arrival_ftracker.py"]},
        "errand": {"command": "python", "args": ["errand_ftracker.py"]},
        "transport": {"command": "python", "args": ["transport_ftracker.py"]}
    }
}

# --- System Prompt with tool descriptions ---
SYSTEM_PROMPT = """
You are an AI Wedding Planner.

You have access to the following tools (functions), each from a different MCP server:

1. track_guest_arrivals()
2. list_errands()
3. list_vehicles()

Your job:
- Gather all tool results and then create a comprehensive transport plan.
- Plan and schedule all guest pickups and errands so that everything is completed before 18:00.
- Ensure vehicle capacity is respected at all times.
- Respect dependencies: Flowers before Decorations; Cake before Reception.
- Steps must be chronological.

The output must be valid JSON **exactly in this structure**:

{
  "guests": [  # List of guest arrivals
    {
      "name": "...",
      "arrival_location": "...",
      "arrival_time": "HH:MM",
      "needs_ride": true|false,
      "status": "requested"
    },
    ...
  ],
  "vehicles": [  # List of vehicles
    {
      "name": "...",
      "capacity": <int>,
      "location": "..."
    },
    ...
  ],
  "errands": [  # List of errands
    {
      "name": "...",
      "status": "requested"
    },
    ...
  ],
  "constraints": {
    "errand_dependencies": [
      ["flowers", "decorations"],
      ["cake", "reception"]
    ],
    "wedding_deadline": "18:00"
  },
  "goals": [
    "Coordinate all guest arrivals",
    "Complete all errands",
    "Optimize vehicle usage"
  ],
  "transport_requests": [],  # Keep empty
  "transport_plan": [  # chronological plan
    {
      "vehicle": "...",
      "action": "pickup_guest" | "pickup_errand",
      "item": "...",
      "from": "...",
      "to": "...",
      "start_time": "HH:MM",
      "end_time": "HH:MM"
    },
    ...
  ],
  "final_summary": "...",  # Human-readable summary of plan
  "metrics": {
    "llm_calls": <int>,
    "tool_calls": <int>,
    "execution_time_sec": <float>
  }
}

- Fill in all sections completely, even if some fields are empty lists.
- Metrics must reflect real execution time and counts from the program, **do not fake them**. Keep them as a separate section at the end as shown in output structure.
- Make `final_summary` a human-readable step-by-step plan.

Always return a **single JSON object** only, without extra text or commentary.
"""

GOAL_PROMPT = "Plan and validate the complete logistics for the wedding using the provided tools."

def extract_json_from_response(response_content):
    """Extract the last JSON code block from LLM output"""
    matches = list(re.finditer(r"```json(.*?)```", response_content, re.DOTALL))
    if not matches:
        try:
            return json.loads(response_content)  # maybe pure JSON
        except:
            return None
    json_block = matches[-1].group(1)
    try:
        return json.loads(json_block)
    except Exception:
        return None

def run_mcp():
    metrics = {
        "llm_calls": 0,
        "tool_calls": 0,
        "execution_time_sec": None,
        "final_plan": None,
        "tool_results": None
    }

    async def main():
        nonlocal metrics
        start = time.time()

        async with Client(CONFIG) as client:
            tools = await client.list_tools()
            wrapped = [{"type": "function", "function": t} for t in tools]

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": GOAL_PROMPT}
            ]

            tool_results = {}

            while True:
                # === Each LLM orchestration step ===
                metrics["llm_calls"] += 1  

                response = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=wrapped,
                    tool_choice="auto"
                )

                msg = response.choices[0].message

                if getattr(msg, "tool_calls", None):
                    # LLM requested tools → count each tool call
                    messages.append(msg)
                    for call in msg.tool_calls:
                        metrics["tool_calls"] += 1
                        res = await client.call_tool(
                            name=call.function.name,
                            arguments=json.loads(call.function.arguments)
                        )
                        try:
                            content = json.dumps(res)
                        except TypeError:
                            content = str(res)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": content
                        })

                        tool_results.setdefault(call.function.name, []).append(make_json_safe(res))

                    # Loop back → LLM will be called again after tool outputs
                    continue
                
                # === After LLM has generated final plan ===
                final_content = msg.content
                plan_data = extract_json_from_response(final_content)

                if plan_data is None:
                    print(" WARNING: No structured plan found in LLM output.")
                    plan_data = {}

                # Remove any metrics inside LLM output
                plan_data.pop("metrics", None)

                # Build final output JSON
                final_output = {**plan_data, "metrics": {
                    "llm_calls": metrics["llm_calls"],
                    "tool_calls": metrics["tool_calls"],
                    "execution_time_sec": round(time.time() - start, 2)
                }}

                metrics["final_output"] = final_output
                return metrics["final_output"]

    return asyncio.run(main())

# === Run planning process ===
if __name__ == "__main__":
    result = run_mcp()
    print(json.dumps(result, indent=2))
    with open("transport_plan.json", "w") as f:
        json.dump(result, f, indent=2)
