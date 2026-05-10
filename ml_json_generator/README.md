# ML JSON Generator

This folder contains experiments for the path:

```text
user request -> local LLM -> JSON CAD plan -> validator -> KOMPAS .m3m macro
```

## Main notebook

Use:

```text
colab_json_repair_loop.ipynb
```

It is designed for Google Colab with a T4 GPU.

## Modes

### Full request mode

The model receives one complete request and returns one complete JSON plan.

```text
request -> full JSON
```

Test file:

```text
test_requests.jsonl
```

### Incremental mode

The model receives the current JSON plan plus one small instruction and returns the full updated JSON plan.

```text
current JSON + instruction -> updated JSON
```

Test file:

```text
test_sets/incremental_tasks.jsonl
```

This is the preferred direction because complex CAD tasks become a sequence of smaller edits.

### Planner mode

The model first splits one large request into small steps, then the incremental builder executes those steps.

```text
user request -> planned steps -> current JSON + step -> updated JSON
```

Use:

```python
run_planned_incremental_request(...)
```

This mode decides how many model calls are needed:

```text
1 planner call + up to N builder attempts per planned step
```

Builder attempts stop as soon as a valid JSON is produced.

## Logging

The older full-request mode appends logs to:

```text
logs/candidate_table.csv
logs/accepted_candidates.csv
logs/rejected_candidates.csv
logs/test_summary.csv
```

The incremental mode creates a new folder per run:

```text
logs/incremental_run_YYYYMMDD_HHMMSS/
```

Inside it:

```text
all_candidates.csv
accepted_candidates.csv
rejected_candidates.csv
step_summary.csv
task_summary.jsonl
tasks/<task_id>.csv
```

The planner mode also creates a new folder per run:

```text
logs/planned_incremental_run_YYYYMMDD_HHMMSS/
```

It additionally stores:

```text
planned_task.json
planned_tasks.jsonl
```

Each task file is the most useful table for review:

```text
request/instruction -> model answer -> accepted or error
```

## Human-readable flow

See:

```text
PROGRAM_FLOW_RU.md
```

It explains the whole program step by step in Russian.
