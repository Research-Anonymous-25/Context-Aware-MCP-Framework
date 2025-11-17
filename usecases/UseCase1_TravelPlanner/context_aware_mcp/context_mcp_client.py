from context_store import ContextStore
from openai import OpenAI
import time
import json
import re
import os

client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

from datetime import datetime

TODAY = "June 26, 2025"

SYSTEM_PROMPT = f"""
Today is {TODAY}.
You are a context-aware travel planner. When given a user request and tool descriptions, your job is to:
- Parse the user's request and write ALL the initial parameters needed for the travel planning pipeline to the context store as a single JSON object.
- Include: base_city, lat, lon, radius_km, keyword, start_date, end_date, budget, guests, dietary_preference, and any other parameters needed for location, weather, hotel, and food planning.
- Do NOT write any *_result or *_done flags.
- The servers will process sequentially, each reading from and writing to the context store as needed.
- At the end, you will be called again to summarize the final context for the user.

Example context:
{{
  "base_city": "Chicago",
  "lat": 41.88,
  "lon": -87.63,
  "radius_km": 200,
  "keyword": "leisure=park",
  "start_date": "2025-06-21",
  "end_date": "2025-06-22",
  "budget": 200,
  "guests": 2,
  "dietary_preference": "vegan"
}}
"""

def extract_json_from_markdown(text):
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1)
    return text.strip()

def run_context_mcp(user_prompt, print_metrics=True):
    context = ContextStore()
    metrics = {
        "llm_calls": 0,
        "server_wait_time_sec": 0,
        "total_response_time_sec": 0,
        "final_output": "",
        "context": {},
        "goal_hits": {
            "location_done": False,
            "weather_done": False,
            "hotel_done": False,
            "food_done": False
        },
        "completeness_score": 0.0
    }

    start_time = time.time()

    print("[MCP] Calling LLM for initial context...")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    metrics["llm_calls"] += 1
    response = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    plan = response.choices[0].message.content

    plan_json_str = extract_json_from_markdown(plan)
    try:
        plan_dict = json.loads(plan_json_str)
        print("[DEBUG] Successfully parsed JSON.")
    except Exception as e:
        print("LLM did not return valid JSON. Plan was:")
        print(plan)
        print("Exception:", e)
        return None

    for k, v in plan_dict.items():
        print(f"[DEBUG] Writing {k}: {v} to context")
        context.set(k, v)

    print("[MCP] Initial context set by LLM:")
    print(json.dumps(context.get_all(), indent=2))

    print("[MCP] Waiting for all servers to finish (sequential pipeline)...")
    wait_start = time.time()
    dots = 0
    while not context.get("food_done"):
        time.sleep(2)
        dots = (dots + 1) % 10
        # Update goal_hits for metrics
        for goal in metrics["goal_hits"]:
            metrics["goal_hits"][goal] = bool(context.get(goal))
        status = {goal: metrics["goal_hits"][goal] for goal in metrics["goal_hits"]}
        print(f"[MCP] Waiting{'.'*dots} Status: {status}")
    wait_end = time.time()
    metrics["server_wait_time_sec"] = round(wait_end - wait_start, 2)

    # Final update for goal_hits
    for goal in metrics["goal_hits"]:
        metrics["goal_hits"][goal] = bool(context.get(goal))
    metrics["completeness_score"] = round(
        sum(metrics["goal_hits"].values()) / len(metrics["goal_hits"]), 2
    )

    print("[MCP] All servers done. Calling LLM for summary...")
    summary_prompt = f"You are a travel planner. Here is the context: {json.dumps(context.get_all(), indent=2)}\nSummarize the best options for the user."
    metrics["llm_calls"] += 1
    summary_response = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": summary_prompt}]
    )
    metrics["final_output"] = summary_response.choices[0].message.content
    metrics["context"] = context.get_all()
    metrics["total_response_time_sec"] = round(time.time() - start_time, 2)

    if print_metrics:
        print("\nMCP Metrics:")
        print(json.dumps(metrics, indent=2))
        print("\nFinal Output:\n")
        print(metrics["final_output"])

    return metrics

if __name__ == "__main__":
    user_input = input("User: ")
    run_context_mcp(user_input)
