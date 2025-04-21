# Agent Runner

**Agent Runner** is a framework for orchestrating complex, multi-step LLM (Large Language Model) workflows using a declarative JSON format. It enables you to break down long, intricate LLM tasks into a series of manageable steps, each with its own conversation context, tool functions, and execution logic.

---

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
  - [Workspace](#workspace)
  - [Step](#step)
  - [Function](#function)
- [Execution Flow](#execution-flow)
- [Sample Workspace JSON](#sample-workspace-json)
- [Extensibility & Roadmap](#extensibility--roadmap)
- [Limitations](#limitations)
- [Development](#development)
- [License](#license)

---

## Overview

Agent Runner lets you define a workflow as a series of steps, each representing an LLM conversation turn, optionally augmented with tool/function calls. The workflow and all its components are described in a single JSON file, making it easy to author, review, and modify complex agent behaviors.

The framework supports:
- Multi-step, linear LLM workflows
- Tool/function calls (sequential or parallel)
- Passing conversation context between steps
- Flexible model selection per step
- Full definition of functions (parameters, code, description) alongside steps

---

## Key Concepts

### Workspace

A **Workspace** is the top-level entity representing a workflow. It contains:
- A list of steps (the workflow)
- A list of functions (tools available to the LLM)
- Metadata about the workflow

All definitions are contained in a single JSON file.

---

### Step

A **Step** represents a single LLM conversation turn and its associated logic.

**Attributes:**
- `id`: Unique identifier for the step
- `chat`: Array of messages (role/content) forming the conversation context
- `nextStep`: The ID of the next step (linear only)
- `model`: Which LLM model to use (e.g., `gpt-4o`)
- `passConversationToNextStep`: If `true`, passes the full chat array to the next step
- `runFunctionsInParallel`: If `true`, executes all tool calls in parallel
- `function`: Array of functions (by name) available as tools in this step

---

### Function

A **Function** describes a tool that the LLM can call during a step.

**Attributes:**
- `name`: Unique identifier for the function
- `description`: What the function does
- `parameters`: List of parameters (type, name, description)
- `code`: The implementation (for reference; actual execution expects the function to exist in runtime)

---

## Execution Flow

The workflow proceeds as follows (see also [docs/flow.md](docs/flow.md) for a Mermaid diagram):

1. **Start:** Instantiate a `WorkspaceManager` and load the workspace JSON.
2. **Parse:** Convert JSON into `WorkspaceData`, extracting steps and functions.
3. **Run:** Create a `Run` instance and start execution.
4. **Step Execution:**  
   - Prepare conversation context and tool array for the step.
   - Call the LLM (via [litellm](https://docs.litellm.ai/docs/)).
   - If tool calls are present in the LLM response:
     - Execute functions (in parallel or sequentially).
     - Append results to the conversation.
   - Move to the next step if specified.
5. **End:** Emit the final result when the workflow completes or aborts on error.

**Error Handling:**  
If any function/tool call fails, the current step and the entire run are aborted.

---

## Sample Workspace JSON

See [docs/sample-workspace-json.md](docs/sample-workspace-json.md) for a comprehensive example.

In a JSON there are multiple keys defining steps and functions. The nomenclature is as follows:

`<Agent name>@<version>>@<step/func>-<name>#details`, where:

 - Agent name: Name of the agent
 - Version: Version of the agent
 - step/func: Type of the key (step or function)
 - name: Name of the step or function
 - details: Details of the step or function

**Example Step:**
```json
"Agent - V1@develop@step-1. Architect#details": {
  "chat": [
    {"role": "system", "content": "You are a helpful AI agent..."},
    {"role": "user", "content": "I have a sheet ..."}
  ],
  "function": [
    {"name": "send_plan_to_pm"},
    {"name": "read_data_from_sheet"}
  ],
  "nextStep": "-",
  "model": "gpt-4o",
  "runFunctionsInParallel": false,
  "passConversationToNextStep": false
}
```

**Example Function:**
```json
"Agent - V1@develop@func-read_data_from_sheet#details": {
  "description": "reads data from given g-sheet",
  "parameters": [
    {"type": "string", "name": "sheet_url", "description": "Sheet url"},
    {"type": "string", "name": "tab_name", "description": "Tab name"}
  ],
  "code": "async function read_data_from_sheet(sheet_url, tab_name) { ... }"
}
```

**List of steps:**
```json
"Agent - V1@develop#details": {"steps":[{id: "1. Architect", name: "1. Architect"}]}
```

---

## Extensibility & Roadmap

Planned/future features:
- **Function/step reuse** across workspaces (via DB)
- **Persistence/recovery** for long-running runs
- **Conditional branching** (non-linear workflows)
- **Security/sandboxing** for user-defined functions

---

## Limitations

- **Linear workflows only:** No conditional branching yet.
- **All-in-memory:** No persistence or recovery on failure.
- **No sandboxing:** User-defined functions are not restricted.
- **No runtime dynamic generation:** All steps/functions must be pre-defined in the JSON.

---

## Development

### Project Structure

- `docs/`: Documentation and sample workspace JSONs
- `src/`: Core implementation (see class diagrams in [docs/workspace.md](docs/workspace.md))
- `tests/`: (If present) Unit and integration tests

### Core Dependencies

- **litellm:** [Universal LLM API wrapper](https://docs.litellm.ai/docs/)
- (Other dependencies as per your implementation)

### Running a Workflow

1. Define your workspace JSON (see sample).
2. Load and run it via the main entrypoint (see [flow.md](docs/flow.md) for flow).
3. Review results or debug via logs.

---

## License

[Your License Here]