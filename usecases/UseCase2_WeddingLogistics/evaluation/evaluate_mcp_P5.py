import json
import sys
import os

# Add REALM-bench evaluation path (adjust if needed)
sys.path.append(os.path.join(os.path.dirname(__file__), "REALM-Bench-main"))

from evaluation.evaluator import EvaluationConfig, TaskEvaluator

# Load your MCP result
with open("wedding_planner_metrics.json") as f:
    my_result = json.load(f)

# Choose the correct task id for P5
task_id = "P5"

# Prepare config (not strictly needed for TaskEvaluator, but included for completeness)
config = EvaluationConfig(
    frameworks=["my_mcp"],
    tasks=[task_id],
    num_runs=1,
    timeout_seconds=300,
    output_dir="my_eval_results",
    enable_visualization=False,
    save_detailed_results=True
)

# Create a TaskEvaluator for your task
task_evaluator = TaskEvaluator(task_id, config)

# Compute metrics using your result as the execution_result
metrics = task_evaluator._calculate_metrics(my_result)

print(json.dumps(metrics, indent=2))

