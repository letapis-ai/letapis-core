# letapis-mcp

MCP server for letapis - semantic code search and knowledge graph.

Proxies MCP tool calls to letapis-core via HTTP API.

## Requirements

- Python 3.11+
- Running letapis-core server
- uv (recommended) or pip

## Installation

```bash
# Clone and install locally
cd letapis-mcp
uv sync

# Or install as tool
uv tool install .
```

## Quick Start

```bash
# Set environment and run
export LETAPIS_SERVER_URL=http://localhost:3131
export LETAPIS_API_KEY=your-api-key
uv run letapis-mcp

# Or with config file
uv run letapis-mcp --config ~/.config/letapis-mcp/config.yaml
```

## Usage with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "letapis": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/path/to/letapis-mcp",
        "letapis-mcp",
        "--config", "/path/to/config.yaml"
      ],
      "env": {
        "LETAPIS_API_KEY": "your-api-key"
      }
    }
  }
}
```

Or without explicit config (uses env vars):

```json
{
  "mcpServers": {
    "letapis": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/letapis-mcp", "letapis-mcp"],
      "env": {
        "LETAPIS_SERVER_URL": "http://localhost:3131",
        "LETAPIS_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Usage with OpenCode

Add to `opencode.json` in your project root (or `~/.config/opencode/opencode.json` for global):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "letapis": {
      "type": "local",
      "command": [
        "uv",
        "run",
        "--project",
        "/path/to/letapis-mcp",
        "letapis-mcp"
      ],
      "environment": {
        "LETAPIS_SERVER_URL": "http://localhost:3131",
        "LETAPIS_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Usage with Cursor

Add to Cursor settings (`Preferences` > `MCP Servers`):

```json
{
  "letapis": {
    "command": "uv",
    "args": [
      "run",
      "--project", "/path/to/letapis-mcp",
      "letapis-mcp"
    ],
    "env": {
      "LETAPIS_SERVER_URL": "http://localhost:3131",
      "LETAPIS_API_KEY": "your-api-key"
    }
  }
}
```

## Usage with Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "letapis": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/letapis-mcp", "letapis-mcp"],
      "env": {
        "LETAPIS_SERVER_URL": "http://localhost:3131",
        "LETAPIS_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Deployment Scenarios

### Scenario 1: Local (Same Machine)

letapis-core and Claude/OpenCode on the same machine. Files are reachable directly.

```
┌─────────────────────────────────────────────────────────────┐
│                      Same Machine                           │
│                                                             │
│  Claude Desktop → letapis-mcp → localhost:3131 → letapis-core  │
│       ↓                                             ↓       │
│  Read files directly                             Neo4j      │
│  (no fetch needed)                              Embeddings  │
└─────────────────────────────────────────────────────────────┘
```

**Config:**
```yaml
server:
  url: http://localhost:3131
  api_key: ${LETAPIS_API_KEY}

paths:
  # No mapping needed - paths are already local
  mapping: []
  fetch:
    enabled: false  # Not needed
```

Claude can open files from a search result with the Read tool, no fetch involved.

### Scenario 2: Remote Server

letapis-core on a remote server. Either path mapping or fetch is required.

```
┌──────────────────────┐          ┌──────────────────────────┐
│      Local Mac       │   HTTP   │     Remote Server        │
│                      │          │                          │
│  Claude Desktop      │────────→ │  letapis-core              │
│       ↓              │          │    ↓                     │
│  letapis-mcp (stdio)   │          │  Neo4j + Embeddings      │
│       ↓              │          │    ↓                     │
│  ~/.letapis_cache/     │          │  /workspace/project/     │
│  (fetched files)     │          │                          │
└──────────────────────┘          └──────────────────────────┘
```

**Option A: Path Mapping (if you have local copies)**
```yaml
server:
  url: http://192.168.1.100:3000

paths:
  mapping:
    - remote: /workspace/project
      local: /Users/you/project  # Local git clone
    - remote: /workspace/libs
      local: /Users/you/libs
  fetch:
    enabled: false
```

**Option B: Fetch on Demand (no local copies)**
```yaml
server:
  url: http://192.168.1.100:3000

paths:
  mapping: []
  fetch:
    enabled: true
    cache_dir: ~/.letapis_cache
    clear_on_start: true  # Fresh cache each session
```

Claude uses the `fetch_file` tool to download files.

**Option C: Both (mapping + fetch fallback)**
```yaml
server:
  url: http://192.168.1.100:3000

paths:
  mapping:
    - remote: /workspace/main-project
      local: /Users/you/main-project
  fetch:
    enabled: true  # For files not in mapping
    cache_dir: ~/.letapis_cache
```

### Scenario 3: Docker (letapis-core in container)

letapis-core in Docker with a volume mount.

```
┌─────────────────────────────────────────────────────────────┐
│                        Host                                 │
│                                                             │
│  Claude Desktop → letapis-mcp → localhost:3131                │
│       ↓                            ↓                        │
│  /Users/you/project/       ┌───────────────┐                │
│        ↓ (volume)          │    Docker     │                │
│                            │  letapis-core   │                │
│                            │       ↓       │                │
│                            │  /workspace/  │                │
│                            └───────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

**Config:**
```yaml
server:
  url: http://localhost:3131

paths:
  mapping:
    - remote: /workspace
      local: /Users/you/project  # Host path mounted to container
```

## Configuration

### CLI Arguments

```
letapis-mcp [OPTIONS]

Options:
  -c, --config PATH    Path to config file (YAML)
  -h, --help           Show help message
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LETAPIS_SERVER_URL` | letapis-core server URL | `http://localhost:3131` |
| `LETAPIS_API_KEY` | API key for authentication | None |
| `LETAPIS_TIMEOUT` | Request timeout in seconds | `60` |
| `LETAPIS_CONFIG` | Path to config file | None |
| `LETAPIS_CACHE_DIR` | Cache directory for fetched files | `~/.letapis_cache` |
| `LETAPIS_FETCH_ENABLED` | Enable file fetching | `false` |

### Config File

Default locations (checked in order):
1. `--config` CLI argument
2. `LETAPIS_CONFIG` environment variable
3. `~/.config/letapis-mcp/config.yaml`
4. `~/.config/letapis-mcp/config.yml`
5. `.letapis-mcp.yaml` (current directory)
6. `.letapis-mcp.yml` (current directory)

Example config:

```yaml
server:
  url: http://localhost:3131
  api_key: ${LETAPIS_API_KEY}  # Expands env var
  timeout: 60

paths:
  # Map remote paths to local paths
  mapping:
    - remote: /workspace/project
      local: /Users/you/project
    - remote: /remote/libs
      local: /Users/you/libs

  # Fetch files not found locally
  fetch:
    enabled: true
    cache_dir: ~/.letapis_cache
    clear_on_start: true  # Clean cache on startup
```

### Path Handling

Two different things ask about a path, and they answer differently. Reading this as one
chain is what let a cached file stand in for permission once already, so the split is
spelled out.

**Naming a path in a search result.** letapis-core has already decided what the caller
may see, so this only puts a local name on what it returned:

1. **Path Mapping** - If path matches a mapping, adds the local path
2. **Cache Lookup** - If the file was fetched before, adds the cached path
3. **Otherwise** - the remote path is left as it is (use `fetch_file` to download)

Example: letapis-core returns `/workspace/project/src/main.py`
- With mapping `/workspace/project` -> `/Users/you/project`
- Returns `/Users/you/project/src/main.py`

**Asking for a file with `fetch_file`.** Here the cache is NOT consulted, and that is
deliberate:

1. **Path Mapping** - answered locally. A mapping is your own configuration about a tree
   already on your own disk, which you could open without this proxy at all.
2. **letapis-core** - everything else is asked of the engine, on every call, including a
   file you have already fetched. A cached file is one the engine handed to ONE earlier
   request; answering a later one out of it would make permission a property of this
   process's history instead of the request being answered — and a folder marked hidden
   in the engine would come back to a call that never named it. The price is a round
   trip per repeat fetch of the same path, paid on purpose.

A folder the engine marks hidden answers nobody who did not name it in `reveal`; pass it
to `fetch_file` to read from your own working copy. `list_folders` shows which folders are
hidden and what each supersedes.

## Available Tools

| Tool | Description |
|------|-------------|
| `search` | Semantic search across all indexed content |
| `vector_search_nodes` | Full-featured semantic search with filters |
| `memory_node` | CRUD operations for knowledge nodes |
| `memory_edge` | Manage relationships between nodes |
| `index_folder` | Index a folder and watch for changes |
| `list_folders` | List all watched folders |
| `get_indexing_progress` | Get indexing progress |
| `ena_get_context` | Get episodic memories and context |
| `fetch_file` | Download file from letapis-core to local cache. Takes `reveal` — hidden folders this call may read from |

## Architecture

```
┌─────────────┐     stdio      ┌─────────────┐     HTTP      ┌─────────────┐
│   Claude    │ ◄────────────► │  letapis-mcp  │ ◄───────────► │ letapis-core  │
│  Desktop    │      MCP       │  (this pkg) │   REST API    │   server    │
└─────────────┘                └─────────────┘               └─────────────┘
                                     │                             │
                                     │                             ▼
                                     │                       ┌───────────┐
                                     │                       │   Neo4j   │
                                     ▼                       │ Embeddings│
                               ┌───────────┐                 └───────────┘
                               │ Local FS  │
                               │ (cache)   │
                               └───────────┘
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Run single test
uv run pytest tests/test_config.py -v
```

## License

MIT
