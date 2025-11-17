import json
from datetime import datetime

class WeddingEvaluator:
    def __init__(self, task_def):
        self.task_def = task_def
        self.deadline = task_def.constraints[0].parameters["deadline"]
        self.vehicle_caps = task_def.constraints[1].parameters["capacities"]
        self.dependencies = task_def.constraints[2].parameters["dependencies"]

    def evaluate(self, plan_output: dict):
        metrics = {}

        # --- Goal Satisfaction ---
        metrics["goal_satisfaction_rate"] = self._evaluate_goals(plan_output)

        # --- Constraint Satisfaction ---
        deadline_ok = self._check_deadline(plan_output)
        vehicle_ok = self._check_vehicle_capacity(plan_output)
        dep_ok = self._check_dependencies(plan_output)
        metrics["constraint_satisfaction_rate"] = (deadline_ok + vehicle_ok + dep_ok) / 3

        # --- Optimality ---
        metrics["makespan"] = self._calculate_makespan(plan_output)
        metrics["coordination_score"] = self._evaluate_coordination(plan_output)

        # --- Resource Usage ---
        usage = plan_output.get("metrics", {})
        metrics["llm_calls"] = usage.get("llm_calls", 0)
        metrics["tool_calls"] = usage.get("tool_calls", 0)
        metrics["execution_time_sec"] = usage.get("execution_time_sec", 0)

        return metrics

    # ---------------------
    def _evaluate_goals(self, plan_output):
        guests = [g["id"] for g in self.task_def.resources["guests"]]
        errands = self.task_def.resources["errands"]
        plan_items = [s["item"] for s in plan_output.get("transport_plan", [])]

        guests_done = all(g in plan_items for g in guests)
        errands_done = all(e in plan_items for e in errands)

        return (guests_done + errands_done) / 2  # 0, 0.5, or 1

    def _check_deadline(self, plan_output):
        for step in plan_output.get("transport_plan", []):
            if step["end_time"] > self.deadline:
                return 0
        return 1

    def _check_vehicle_capacity(self, plan_output):
        for step in plan_output.get("transport_plan", []):
            if step["action"] == "pickup_guest":
                if self.vehicle_caps[step["vehicle"]] < 1:
                    return 0
        return 1

    def _check_dependencies(self, plan_output):
        completed = [s["item"] for s in plan_output.get("transport_plan", [])]
        for pre, post in self.dependencies:
            if pre in completed and post in completed:
                if completed.index(pre) > completed.index(post):
                    return 0
        return 1

    def _calculate_makespan(self, plan_output):
        fmt = "%H:%M"
        times = []
        for s in plan_output.get("transport_plan", []):
            times.append(datetime.strptime(s["start_time"], fmt))
            times.append(datetime.strptime(s["end_time"], fmt))
        if not times:
            return 0
        return (max(times) - min(times)).seconds / 60  # in minutes

    def _evaluate_coordination(self, plan_output):
        # simplistic: errands with identical start_time are "batched"
        errands = [s for s in plan_output.get("transport_plan", []) if s["action"] == "pickup_errand"]
        times = [s["start_time"] for s in errands]
        if len(times) != len(set(times)):
            return 1  # batched
        return 0
