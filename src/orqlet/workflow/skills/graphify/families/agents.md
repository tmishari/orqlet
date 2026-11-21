# Dispatching the extraction subagents

This is Step B2 of the graphify skill for this client.

> Uses the `Task` tool for parallel subagent dispatch.
> Call `Task` once per chunk — ALL in the same response so they run in parallel.

Pass the extraction prompt as the task description:

```
Task(description="Your task is to perform the following. Follow the instructions below exactly.\n\n<agent-instructions>\n[extraction prompt, with FILE_LIST, CHUNK_NUM, TOTAL_CHUNKS, DEEP_MODE substituted]\n</agent-instructions>\n\nExecute this now. Output ONLY the structured JSON response.")
```

Each subagent writes its result to its own `graphify-out/.graphify_chunk_NN.json`. Collect results as each `Task` completes and parse each as JSON.
