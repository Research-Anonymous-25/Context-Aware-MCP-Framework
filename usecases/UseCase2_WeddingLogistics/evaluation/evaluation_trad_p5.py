from task_definitions_copy import TASK_DEFINITIONS
from wedding_evaluator import WeddingEvaluator
import json

# load task definition
task_def = TASK_DEFINITIONS["P5"]

# load plan output from JSON
with open("transport_plan.json") as f:
    plan_output = json.load(f)

# evaluate
evaluator = WeddingEvaluator(task_def)
metrics = evaluator.evaluate(plan_output)

print(metrics)
