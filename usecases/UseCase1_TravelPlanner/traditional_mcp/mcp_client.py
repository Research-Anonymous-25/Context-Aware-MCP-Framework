import os
import json
import asyncio
import time
from fastmcp import Client
from openai import OpenAI

client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
CONFIG = {
    "mcpServers": {
        "location": {"command": "python", "args": ["location_server.py"]},
        "weather": {"command": "python", "args": ["weather_server.py"]},
        "hotel": {"command": "python", "args": ["hotel_server.py"]},
        "food": {"command": "python", "args": ["food_server.py"]}
    }
}

SYSTEM_PROMPT = """
You are a smart travel planner that can use external tools to fulfill user travel requests. The tools themselves do not understand user intent — only you do. You must do all reasoning and translation between user preferences and tool inputs.

You have access to four tools:

1. location_search_locations(base_city, radius_km, keyword): 
   - Finds interesting places near a city.
   - You must provide a keyword in the format of OpenStreetMap (OSM) tags, e.g. "tourism=beach", "leisure=park".
   - Do not pass vague terms like "sunny", "scenic", "relaxing" directly.
   - Instead, interpret them into relevant OSM tag(s) before calling this tool.

2. weather_get_weather_forecast(lat, lon, start_date=None, end_date=None):
   - Returns weather forecasts for a location.
   - Optionally accepts start_date and end_date in 'YYYY-MM-DD' format to get forecasts for a specific date range.
   - If the user request mentions vague or relative dates (like "this weekend", "last week of June", "next Friday"), you must interpret and convert them into exact start_date and end_date values before calling this tool.
   - Use this to evaluate user weather preferences like "sunny", "not windy", "warm" for the relevant dates.

3. hotel_find_hotels_nearby(lat, lon, radius):
   - Finds hotels in a city matching the location. 
   - You must take these hotels and check their availability for the user’s dates and guests and make sure it fits the budget, and then return the best options.
   - Remember that although the tool provides hotel names, rating, review, and price, the price is not correct, and you must check their availability and details online.
   - Only works with cities, not natural spots.

4. food_find_food_places(lat, lon, radius_km=None):
   - Finds food places (restaurants, cafes) near the given coordinates.
   - Always provide lat and lon (not city name).
   - Optionally, you can specify radius_km (default is 5).
   - The tool will return basic information (name, lat, lon, cuisine, tags) from OSM.
   - You must look up additional details from the web such as:
     - Dietary options (veg, vegan, gluten-free)
     - Cuisine (Indian, Italian, etc.) if not specified in tool result
     - Ratings or menus if needed for user prompt
   - Match the user’s dietary or cuisine preferences by researching the food place name online or taking details from tool results.
   - You may assume reasonable defaults if information is missing.

Your job is to:
- Parse the user’s request for cities, radius, dates, guests, budget, food preferences, and activities.
- Use your own reasoning to translate vague preferences into tool-ready values.
  - For dates, always convert vague or relative expressions (like "this weekend", "last week of June", "next Friday") into exact start_date and end_date in 'YYYY-MM-DD' format when calling tools that require dates.
  - e.g. “sunny vacation near Chicago over the weekend” → call `get_weather_forecast(lat, lon, start_date="2025-06-21", end_date="2025-06-22")`
- Plan steps in a logical order:
  - Find destinations → check weather → find hotels → find food.
- You may call tools multiple times and compare alternatives.
- Your final response should be a concise summary of the best options for the user, including:
  - Destinations, Weather forecast, Hotels (with availability and budget), Food places (with dietary options).
- Always explain your reasoning and tool choices clearly.
- If any information is missing, assume reasonable defaults (e.g., radius = 200 km, budget = $200/night, guests = 2).
- Never pass ambiguous or uninterpretable values to tools.

Think step-by-step.
Always format your tool calls exactly as defined.
Be helpful, organized, and rational in all steps.
"""

def run_mcp(user_prompt: str, expected_goals=None):
    if expected_goals is None:
        expected_goals = [
            "location_search_locations",
            "weather_get_weather_forecast",
            "hotel_find_hotels_nearby",
            "food_find_food_places"
        ]
    metrics = {
        "llm_calls": 0,
        "tool_calls": 0,
        "goal_hits": {goal: False for goal in expected_goals},
        "final_output": ""
    }

    async def main():
        nonlocal metrics
        async with Client(CONFIG) as client:
            tools = await client.list_tools()
            wrapped_tools = [{"type": "function", "function": t} for t in tools]

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            tool_results = {}

            while True:
                metrics["llm_calls"] += 1

                response = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=wrapped_tools,
                    tool_choice="auto"
                )
                message = response.choices[0].message

                if getattr(message, "tool_calls", None):
                    messages.append(message)
                    for call in message.tool_calls:
                        metrics["tool_calls"] += 1
                        tool_result = await client.call_tool(
                            name=call.function.name,
                            arguments=json.loads(call.function.arguments)
                        )
                        # Robustly unwrap TextContent, even if in a list
                        tool_result_content = tool_result
                        if isinstance(tool_result, list) and tool_result and hasattr(tool_result[0], "text"):
                            try:
                                tool_result_content = json.loads(tool_result[0].text)
                            except Exception:
                                tool_result_content = tool_result[0].text
                        elif hasattr(tool_result, "text"):
                            try:
                                tool_result_content = json.loads(tool_result.text)
                            except Exception:
                                tool_result_content = tool_result.text

                        # Save tool results for summary
                        tool_name = call.function.name
                        if tool_name not in tool_results:
                            tool_results[tool_name] = []
                        tool_results[tool_name].append(tool_result_content)

                        # Goal hit logic (by substring match in tool name)
                        for goal in metrics["goal_hits"]:
                            if goal in call.function.name.lower():
                                metrics["goal_hits"][goal] = True

                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(tool_result_content)
                        })
                else:
                    # Final summary step: ask LLM to summarize for the user
                    summary_prompt = (
                        "You are a travel planner. Here is your plan and all tool results:\n"
                        + json.dumps({"plan": message.content, "tool_results": tool_results}, indent=2)
                        + "\nSummarize the best travel plan for the user in a concise, user-friendly way."
                    )
                    metrics["llm_calls"] += 1
                    summary_response = client_openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": summary_prompt}]
                    )
                    metrics["final_output"] = summary_response.choices[0].message.content
                    return metrics["final_output"]

    # Measure total response time
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()

    # Final metrics
    metrics["total_response_time_sec"] = round(end_time - start_time, 2)
    metrics["completeness_score"] = round(
        sum(metrics["goal_hits"].values()) / len(metrics["goal_hits"]), 2
    )

    return metrics

if __name__ == "__main__":
    user_input = input("User: ")
    metrics = run_mcp(user_input)
    print("\nMCP Metrics:")
    print(json.dumps(metrics, indent=2))
    print("\nFinal Output:")
    print(metrics["final_output"])