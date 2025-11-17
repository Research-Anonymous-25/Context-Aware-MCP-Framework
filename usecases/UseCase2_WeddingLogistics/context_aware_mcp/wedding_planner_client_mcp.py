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

client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"]) 

CONFIG = {
    "mcpServers": {
        "arrival": {"command": "python", "args": ["arrival_tracker_mcp.py"]},
        "transport": {"command": "python", "args": ["transport_mcp.py"]},
        "errand": {"command": "python", "args": ["errand_mcp.py"]}
    }
}

SYSTEM_PROMPT = """
You are a wedding logistics planning assistant. You coordinate the following tools (functions), each provided by a separate agent/server:

1. track_guest_arrivals():
   - Purpose: Get a list of all guests and their expected arrival times at the wedding venue.
   - Arguments: None.
   - Returns: List of guest dicts, each with at least 'name' and 'arrival_time' keys.

2. plan_transport(from_location, to_location, departure_time):
   - Purpose: Plan transport for guests or items between locations at a specific time.
   - Arguments:
       - from_location (str): Start location (e.g., 'B', 'G', 'T', 'W')
       - to_location (str): Destination location
       - departure_time (str): Time in 'HH:MM' 24-hour format
   - Returns: Dict with estimated travel time, arrival time, and transport details.

3. pickup_gift(current_time):
   - Purpose: Schedule the pickup of the wedding gift from location G.
   - Arguments:
       - current_time (str): Time in 'HH:MM' 24-hour format when pickup is attempted.
   - Returns: Confirmation and any constraints or issues.

4. pickup_clothes(current_time):
   - Purpose: Schedule the pickup of wedding clothes from location T.
   - Arguments:
       - current_time (str): Time in 'HH:MM' 24-hour format when pickup is attempted.
   - Returns: Confirmation and any constraints or issues.

**Your job is to:**
- Plan all activities so that all guests arrive at the wedding venue (W) by 3:00 PM.
- Ensure the gift is picked up from G after 12:00 PM and clothes from T before 2:00 PM.
- Only two cars are available: Pat's (at W after 12:00), and Chris's (at W after 1:30).
- Guests: Alex (arrives 11:00 at B, needs ride), Jamie (12:30 at B, needs ride), Pat (12:00 at W, has car).
- Travel times: B-W:40, B-G:45, B-T:30, G-W:25, G-T:20, T-W:15 (all in minutes).
- Make sure that the pickups are done by either Pat or Chris, and that they are coordinated with guest arrivals.
- Use the tools step-by-step, reasoning about the order and timing of errands, pickups, and transport.
- After gathering all tool results, **validate the feasibility of the plan yourself**
- In your final output, provide:
    - 'guest_arrivals': list of guest dicts with 'arrival_time' keys
    - 'errand_plan': list of errands with 'pickup_time' keys
    - 'transport_time_minutes': dict with keys like 'B->W', etc.
    - A clear, concise final plan with all tasks, timings, people, and transport arrangements, including shop opening/closing timings, everything listed sequentially line after line numbered.
- After the tables, output a JSON code block with a key "plan" containing a list of actions, where each action is a dict with fields like step, action, who, from, to, departure, arrival, etc.
**Think step-by-step.**  
**You are responsible for validating the plan and presenting the final result.**
"""

GOAL_PROMPT = "Plan and validate all activities to complete before 3 PM wedding photo, using the available tools."

def extract_plan_from_response(response_content):
    # Find the last JSON code block in the LLM output
    matches = list(re.finditer(r"```json(.*?)```", response_content, re.DOTALL))
    if not matches:
        return None
    json_block = matches[-1].group(1)
    try:
        plan_dict = json.loads(json_block)
        if "plan" in plan_dict and isinstance(plan_dict["plan"], list):
            return plan_dict["plan"]
    except Exception:
        pass
    return None

def run_mcp():
    metrics = {
        "llm_calls": 0,
        "tool_calls": 0,
        "planning_time_sec": None,
        "final_plan": None,
        "plan": None,
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
                metrics["llm_calls"] += 1
                response = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=wrapped,
                    tool_choice="auto"
                )

                msg = response.choices[0].message

                if getattr(msg, "tool_calls", None):
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
                    continue

                # Final LLM message with plan
                summary = json.dumps({"tool_results": make_json_safe(tool_results)}, indent=2)
                metrics["llm_calls"] += 1
                summary_resp = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": summary}
                    ]
                )
                final_content = summary_resp.choices[0].message.content
                metrics["final_plan"] = final_content
                metrics["tool_results"] = tool_results

                # Extract structured plan from JSON code block
                plan = extract_plan_from_response(final_content)
                if plan:
                    metrics["plan"] = plan
                else:
                    print("WARNING: No structured plan found in LLM output.")

                break

        metrics["planning_time_sec"] = round(time.time() - start, 2)
        return metrics

    return asyncio.run(main())

# === Run planning process ===
if __name__ == "__main__":
    result = run_mcp()
    print(json.dumps(result, indent=2))
    with open("wedding_planner_metrics.json", "w") as f:
        json.dump(result, f, indent=2)
