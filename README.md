# AI-AGENT

An asynchronous assistant for tool use, local memory, document creation, and Google Workspace integration. The chat model is accessed through an OpenAI-compatible OmniRoute endpoint; memory and generated files are stored locally.

This is a personal-assistant prototype. The implementation is useful for studying orchestration and execution boundaries, but it has no published task-success benchmark or production reliability evaluation.

![Architecture](docs/assets/architecture-diagram.png)

## What is implemented

- LangChain tool-calling orchestration with asynchronous calls, retries, and background Streamlit jobs.
- Conversation summaries, durable notes/tasks, and a local JSON knowledge graph.
- Gmail, Calendar, and Drive tools using Google OAuth.
- Research briefs, document generation, and optional media-provider routes.
- Workspace path checks and an opt-in Docker runner for generated Python.

Provider availability, pricing, and tool-calling support depend on the configured endpoint. A local gateway does not imply that model inference or submitted content stays on your machine.

## Try the offline checks first

Use Python 3.11+:

```bash
git clone https://github.com/Kartik-A-1820/AI-AGENT.git
cd AI-AGENT
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in Windows PowerShell. From the repository root:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q tests
```

These tests need no provider credentials or model downloads. They check execution opt-in, no host fallback, container command restrictions, path traversal, bounded output, timeout handling, and cleanup. They do not run a real Docker job or validate external integrations.

## Run the assistant

1. Install application dependencies with `python -m pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set the OmniRoute endpoint, model, and endpoint key if required. The default URL is `http://localhost:20128/v1`; a gateway must already be running.
3. Leave optional provider keys empty until using those integrations. Leave `AI_AGENT_ENABLE_CODE=false` for the initial run.
4. Start either interface:

```bash
python main.py
python -m streamlit run gui.py
```

Run those commands separately. The CLI is interactive; the Streamlit interface opens in a browser. A first local-memory exercise is to add a task, list it, and recall a saved note. It still requires a working chat-model endpoint.

`python setup_check.py` prints path, credential, and endpoint diagnostics. It makes a live endpoint request and creates assistant directories. Its exit code is not a comprehensive readiness check.

Requirements use bounded version ranges. Record exact installed versions when reproducing behavior. Existing PowerShell launch/startup helpers contain development-machine D-drive defaults; use the explicit commands above on a fresh machine.

## Configuration

| Setting | Purpose |
| --- | --- |
| `OMNIROUTE_BASE_URL`, `OMNIROUTE_MODEL`, `OMNIROUTE_API_KEY` | Chat-model route and authentication |
| `AI_AGENT_HOME` | Durable local memory and task data |
| `AI_AGENT_WORKSPACE` | Generated-file workspace |
| `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_TOKEN_PATH` | OAuth client and saved token |
| `TAVILY_API_KEY`, `GEMINI_API_KEY` | Optional search and image integrations |
| `AI_AGENT_ENABLE_CODE`, `AI_AGENT_DOCKER_IMAGE` | Generated-Python opt-in and prebuilt local image |

The example uses relative paths under `.local/` and `agent_working/`; run from the repository root. Local storage contains personal data. External model calls, graph extraction, research, and connected-service tools can transmit content to their providers.

## Google Workspace integration

Google access is optional for local-memory exploration. To use Gmail, Calendar, or Drive:

1. Configure a Google Cloud Desktop OAuth client and enable the relevant service APIs.
2. Save its JSON at `GOOGLE_CREDENTIALS_PATH`.
3. Run `python get_google_service.py` and inspect the requested scopes before authorizing.
4. Keep the saved token private at `GOOGLE_TOKEN_PATH`.

The current OAuth flow requests Calendar, Gmail send/read, and Drive scopes together. Action confirmation is requested through the agent prompt; it is not an independent authorization gate around each tool. Review tools and scopes before connecting an account. Offline tests do not establish end-to-end OAuth behavior.

## Generated-code execution

Generated Python execution is **disabled by default**. A working directory and
regex denylist never provided process isolation; the old host-Python runner has
been removed. Both CLI entrypoints register the code tool only when the owner
sets `AI_AGENT_ENABLE_CODE=true`. The runner checks that setting again at call
time and requires `AI_AGENT_DOCKER_IMAGE` to name an owner-prepared local image.
There is no automatic image pull and no host-Python fallback.

To enable it, install Docker with Linux-container support, prepare a trusted image
containing Python and any required libraries, and set those two variables before
launching the assistant. Prefer an image pinned by digest. Docker Desktop users
must allow sharing the configured workspace drive. The image must support an
unprivileged UID. Do not put credentials, the Docker socket, or host directories
inside that image.

Each call creates `agent_working/_jobs/<unique-id>/`. Only that job directory is
mounted; input files are copied from resolved workspace paths and passed as
`input_files`. Code runs under `/workspace`, with no host environment variables
forwarded, no network, a read-only container root, dropped capabilities,
no-new-privileges, and memory/CPU/process/file-size/time/output limits. Generated
artifacts remain in the reported job directory. This changes where old scripts
find inputs and write outputs: supply inputs explicitly and use relative names.

Runtime pip installation is disabled. Prepare dependencies in the trusted image
outside the agent. The host file tools resolve symlinks before checking paths.
These path checks are convenience guards, not a hostile multi-user filesystem
boundary; avoid concurrent untrusted host processes changing workspace symlinks.

The container runner protects the code-execution path, not the entire assistant.
Google Workspace and other network-capable tools run in the host service, and
prompt-based action confirmation remains separate from this execution boundary.
Containers share the host kernel and the job mount remains writable; this is not
a hardened public multi-tenant execution service or a guarantee against kernel
vulnerabilities or total workspace disk exhaustion.

Verification: `python -m pip install -r requirements-test.txt` followed by
`python -m pytest -q tests`. These offline tests check default denial, no-host
fallback, command restrictions, traversal/symlink checks, output/time limits,
and cleanup after failure. A Docker daemon/image smoke test is additionally
required before enabling execution on a deployment machine. See
[Docker run options](https://docs.docker.com/reference/cli/docker/container/run/).

## Source map

| File | Responsibility |
| --- | --- |
| `main.py`, `app.py`, `gui.py` | Agent entrypoints and interfaces |
| `llm_config.py`, `async_utils.py` | Model settings, asynchronous execution, retry helpers |
| `assistant_state.py`, `graph_memory.py`, `personal_tools.py` | Durable memory and local task operations |
| `*_tools.py` | Service, document, research, media, and file integrations |
| `isolated_runner.py`, `workspace_paths.py` | Container runner and resolved-path checks |

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the test and review workflow and [SECURITY.md](SECURITY.md) for execution boundaries. Useful contributions include mocked tool tests, explicit action-approval controls, portable launchers, and task-success evaluation with reproducible fixtures.

No standalone LICENSE file is currently included. Check repository and third-party reuse terms before redistribution.
