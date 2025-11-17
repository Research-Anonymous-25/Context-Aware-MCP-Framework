from datasets import load_dataset
from mcp_client import run_mcp
import json
import time
import evaluate

rouge = evaluate.load("rouge")
bertscore = evaluate.load("bertscore")

dataset = load_dataset("osunlp/TravelPlanner", "test")["test"]
subset = dataset.select(range(500))
results = []

for i, example in enumerate(subset):
    print(f"\n=== Example {i+1} ===")
    user_query = example["query"]
    gold_reference = example["reference_information"]

    print("User Query:", user_query)
    print("Gold Reference:", gold_reference)

    t0 = time.time()
    metrics = run_mcp(user_query)
    exec_time = time.time() - t0

    if metrics is None:
        print("System Output: [ERROR: LLM did not return valid JSON]")
        print("Execution Time (sec):", exec_time)
        print("Skipping similarity and metrics for this example.\n")
        results.append({
            "query": user_query,
            "gold_reference": gold_reference,
            "system_output": "",
            "rougeL": None,
            "bertscore_f1": None,
            "execution_time_sec": exec_time,
            "goal_hits": None,
            "completeness_score": None,
            "error": "LLM did not return valid JSON"
        })
        continue

    system_output = metrics["final_output"]
    goal_hits = metrics.get("goal_hits", {})
    completeness_score = metrics.get("completeness_score", None)

    # Similarity metrics
    rouge_score = rouge.compute(predictions=[system_output], references=[gold_reference])
    bert_score = bertscore.compute(predictions=[system_output], references=[gold_reference], lang="en")

    print("System Output:", system_output)
    print("Execution Time (sec):", exec_time)
    print("Goal Hits:", goal_hits)
    print("Completeness Score:", completeness_score)
    print("ROUGE-L:", rouge_score["rougeL"])
    print("BERTScore F1:", bert_score["f1"][0])

    results.append({
        "query": user_query,
        "gold_reference": gold_reference,
        "system_output": system_output,
        "rougeL": rouge_score["rougeL"],
        "bertscore_f1": bert_score["f1"][0],
        "execution_time_sec": exec_time,
        "goal_hits": goal_hits,
        "completeness_score": completeness_score,
        "error": None
    })

    # Save results for later analysis
    with open("traditional_mcp_eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    time.sleep(2)  # To reduce API rate limit issues