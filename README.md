# letapis-core

The engine's public home: how to install it, how to license it, what it expects of the machine,
and the **MCP proxy**, which is how an assistant talks to it.

The engine itself is licensed, and it is not in this repository. You receive it from us with your
licence key; there is no public download. What is here is everything you need around it.

**Installing for the first time? → [ONBOARDING.md](ONBOARDING.md).** The whole path on one page,
in order, with a box to tick at every step. The pages below are the long versions of its steps.

## Start here

| If you want to | Go to |
|---|---|
| Put the engine on a Mac that already has the panel | [ONBOARDING.md#6-the-engine](ONBOARDING.md#6-the-engine) |
| Log this machine in, or understand a refusal | [docs/licence.md](docs/licence.md) |
| Point Claude Code, opencode or another client at it | [letapis-mcp/README.md](letapis-mcp/README.md) |
| Know which models it is built against | [docs/models.md](docs/models.md) |
| Run the embedder under vllm-mlx instead of llama.cpp | [docs/vllm/README.md](docs/vllm/README.md) |
| Go back to a previous engine version | [docs/updating.md](docs/updating.md) |
| See what changed in this version | [docs/release-notes.md](docs/release-notes.md) |

**Installing from nothing?** Start with the panel instead: it brings up Docker, Qdrant and the
two model servers, and this repository picks up from there:
[letapis-ai/letapis-panel](https://github.com/letapis-ai/letapis-panel).

## The MCP proxy

`letapis-mcp` is a thin proxy: it asks the engine what tools it has (`GET /api/v1/tools`) and
passes them through as they are. It holds no tool definitions of its own, which is why a new
capability in the engine needs no new version of this.

It is a normal Python package: install it, point it at your engine with `LETAPIS_SERVER_URL`,
and register it with your client. [letapis-mcp/README.md](letapis-mcp/README.md) has the config
blocks for the common clients.

The tests come with it on purpose. They are the clearest description of the protocol we have, and
they let you check the proxy works against your own engine rather than taking our word for it.

## Something wrong, something missing?

**Open an issue.** That is what this repository is for as much as the files in it. It is the one
place you can reach us about the engine.

## What is not here, and why

The engine's own code and builds. It is the licensed part: the binary comes from the licence
service in exchange for a valid key, and putting it in a public repository would be giving away
the thing the licence is for. Everything *around* it — how to install it, how to configure it,
how to talk to it — is here, and is meant to be.
