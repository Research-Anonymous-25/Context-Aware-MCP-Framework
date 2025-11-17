# Context-Aware-MCP-Framework
Enhancing Model Context Protocol (MCP) with Context-Aware Server Collaboration

An Implementation of Shared-Context Multi-Agent Coordination for the Model Context Protocol (MCP)
This repository contains the reference implementation used in the experiments of the paper:
Enhancing Model Context Protocol (MCP) with Context-Aware Server Collaboration (2025)
It provides traditional (stateless) MCP baselines and the proposed Context-Aware MCP architecture, along with evaluation scripts, figures, and benchmark outputs for two representative multi-agent workflows:
TravelPlanner (real-world itinerary planning)
Wedding Logistics (REALM-Bench P5) (multi-agent scheduling and coordination)
The goal of this repository is to demonstrate how introducing a Shared Context Store enables MCP servers to coordinate autonomously, reducing LLM workload, improving latency, and increasing task completeness and coordination accuracy.

## Repository Layout
- `usecases/UseCase1_TravelPlanner/`
  - `traditional_mcp/`: Stateless MCP orchestrator (`mcp_client.py`) plus location, weather, hotel, and food servers.
  - `context_aware_mcp/`: Context-aware orchestrator (`context_mcp_client.py`) and context-enabled servers (location, weather, hotel, food), using `context_store.py` to pass state.
  - `evaluation/`: Traditional travel planner evaluator (`traditional_evaluate_travelplanner.py`) and comparison plotter (`compare_eval_results2.py`).
  - `outputs/`: Benchmark plots for Execution Time, Completeness, BERTScore, and RougeL.
- `usecases/UseCase2_WeddingLogistics/`
  - `traditional_mcp/`: Stateless wedding planner (`wedding_planner_traditional.py`) plus arrival/errand/transport servers.
  - `context_aware_mcp/`: Context-oriented wedding planner (`wedding_planner_client_mcp.py`) plus arrival/errand/transport servers, shared context sample (`shared_context_P5.py`, `context_store/shared_context_wedding.json`).
  - `evaluation/`: P5 evaluation scripts (`evaluation_trad_p5.py`, `evaluate_mcp_P5.py`) and task metadata (`task_definitions_copy.py`, `wedding_evaluator.py`).
  - `validation/`: Schedule validators (`schedule_validator.py`, `schedule_validator_mcp.py`).
  - `outputs/`: Sample transport plan JSON.

## Prerequisites
- Python 3.10+ recommended.
- `fastmcp`, `openai`, and plotting/eval deps used by the evaluation scripts (`datasets`, `evaluate`, `matplotlib`, etc.).
- Set your key: `export OPENAI_API_KEY=...`

## Running the Travel Planner (UseCase1)
1) Traditional MCP:
```bash
cd usecases/UseCase1_TravelPlanner/traditional_mcp
python mcp_client.py
```
2) Context-Aware MCP:
```bash
cd usecases/UseCase1_TravelPlanner/context_aware_mcp
python context_mcp_client.py
```

## Running the Wedding Logistics Planner (UseCase2)
1) Traditional MCP:
```bash
cd usecases/UseCase2_WeddingLogistics/traditional_mcp
python wedding_planner_traditional.py
```
2) Context-Aware MCP:
```bash
cd usecases/UseCase2_WeddingLogistics/context_aware_mcp
python wedding_planner_client_mcp.py
```

## Evaluating
- Travel planner traditional eval: `usecases/UseCase1_TravelPlanner/evaluation/traditional_evaluate_travelplanner.py`
- Wedding P5 eval: `usecases/UseCase2_WeddingLogistics/evaluation/evaluation_trad_p5.py` or `evaluate_mcp_P5.py`

- Outputs are provided for the four benchmark evaluation metrics. The plots are also shown in the Research paper figures (ExecutionTime, Completeness, BERTScore, RougeL).
```

