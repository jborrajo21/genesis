# Using Genesis

The full command reference. For what Genesis is and why, see the
[README](https://github.com/jborrajo21/genesis/blob/main/README.md).

## Install

```bash
pip install "genesis-agent[anthropic]"     # hosted backend
pip install genesis-agent                  # local models via Ollama need no extra
```

**Installs as `genesis-agent`, runs as `genesis`.** The name `genesis` was already taken on PyPI by
an unrelated project, so only the distribution name changed — the import name, the package directory
and the command are all still `genesis`. **`pip install genesis` gets you someone else's library**,
and because it also ships a package called `genesis`, it collides with this one in the same
environment.

**`[anthropic]` is the only extra, and only for the hosted backend.** It pulls in the Anthropic SDK,
deliberately not a default dependency (D-017) so the offline suite and CI run without it. **Ollama
needs no extra and no Python dependency at all** — that adapter talks HTTP through the standard
library. What it needs is the Ollama server running locally.

**From a clone:**

```bash
git clone https://github.com/jborrajo21/genesis && cd genesis
python -m venv .venv && source .venv/bin/activate
pip install -e ".[anthropic]"          # add dev for the tests: ".[dev,anthropic]"
```

Cloning alone is not enough: `genesis` is a console script, so it exists only once the package is
installed. `pip install -e .` is what puts it on your PATH, and `-e` means edits take effect without
reinstalling.

## Two backends, same commands

| | Hosted (Anthropic) | Local (Ollama) |
|---|---|---|
| Setup | `export ANTHROPIC_API_KEY=...` | `ollama serve` |
| Invoke | `genesis create "idea" ./out` | `genesis create "idea" ./out --adapter ollama --model <your-model>` |
| Cost | tokens | free |
| Needs network | yes | no |
| Plan quality | deeper plans (≈30 steps) | thinner (≈14 steps) — but **higher end-to-end success**, see [the eval numbers](https://github.com/jborrajo21/genesis/blob/main/README.md#eval-numbers) |

## Credentials

**Genesis never stores, caches or transmits your API key anywhere except to the provider you chose.**
It holds no config file and reads no `.env` — the Anthropic SDK resolves credentials itself, from
`ANTHROPIC_API_KEY` or an `ant auth login` profile, and Genesis passes nothing of its own.

The local path needs no credential at all: `--adapter ollama` talks to a server on your own machine,
and `genesis scaffold` needs no model whatsoever, so plans you already have cost nothing to build.

## Commands

Three commands. `plan` and `scaffold` are each independently useful; `create` chains them (D-033).

```
genesis plan      idea            → Plan JSON        (needs a model)
genesis scaffold  plan JSON file  → working repo     (no model, no network beyond pip)
genesis create    idea            → plan + repo      (both of the above)
```

**Every positional argument is optional.** Omit one and Genesis prompts for it, so `genesis create`
with no arguments walks you through the whole thing. Pass them all and it never asks, which is what
makes it scriptable.

| Flag | Commands | Default | Notes |
|---|---|---|---|
| `--adapter` | `plan`, `create` | prompts | `anthropic` or `ollama` |
| `--model` | `plan`, `create` | prompts | Menu of known models, or type any name — the list is a menu, not a whitelist (D-047) |
| `--output` | `plan`, `create` | — | Save the plan JSON to a path |
| `--force` | `scaffold`, `create` | off | Overwrite an existing output directory |
| `--max-rounds` | `plan`, `create` | 6 | Cap on clarifying rounds — a ceiling, not a target |
| `--max-tokens` | `plan`, `create` | 10000 | Per model call. Raise it if a plan is truncated |

### Interactive — no arguments at all

The friendliest way in. Every prompt corresponds to an argument you could have passed.

```
$ genesis create

What's your project idea?
→ a cli that tracks time spent per project

Where should we scaffold it?
→ ~/timetrack

Choose adapter:
1) Anthropic
2) Ollama
→ 1

Choose anthropic model:
1) claude-opus-5
2) claude-sonnet-5
3) claude-haiku-4-5
4) Enter custom model name
→ 3

→ Planning...
[Q1/2] Where should the time entries be stored?
→ a json file in the project directory

[Q2/2] Should it track a single active timer, or allow several at once?
→ one at a time

✓ Plan created
→ Scaffolding... ✓ Scaffolded to ~/timetrack
✓ Build and tests passed
```

`genesis plan` and `genesis scaffold` behave the same way: omit any positional argument and you are
asked for it. `genesis scaffold` on its own asks for a plan file and an output directory, and needs
no model or key at all.

### End to end

```
$ genesis create "a cli todo app with local storage" ~/my-todo \
    --adapter anthropic --model claude-haiku-4-5

→ Planning...
[Q1/3] What programming language and/or platform do you prefer (e.g., Python, Node.js, Go, Rust)?
→ Python 3.11
[Q2/3] Should todos support additional metadata like due dates, priority levels, or just a simple
       text description?
→ title and completion status only
[Q3/3] What CLI interface style do you want: interactive menu-driven, command-based, or both?
→ command-based
✓ Plan created

→ Scaffolding... ✓ Scaffolded to ~/my-todo
✓ Build and tests passed

Run:
  cd ~/my-todo
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
```

`Build and tests passed` is the point: Genesis created a throwaway virtualenv, installed the
generated repo into it, ran its command and its test suite — then **deleted the virtualenv**, so
what you get is 36 KB of project rather than 47 MB of someone else's environment.

### Planning on its own

```bash
$ genesis plan "a log file parser that summarises errors" --output plan.json
```

Without `--output` the plan goes to stdout as JSON, so it pipes:

```bash
$ genesis plan "a git commit message linter" --adapter ollama --model gemma4:latest | jq .stack
```

A plan is a typed object — `project_name`, `summary`, `stack`, `phases[]`, `manual_checklist[]`,
and `supported`. **`supported` is computed by Genesis from the recommended stack, never by the
model** (D-028). When it is `false`, scaffolding writes `PLAN.md` and a `README.md` explaining that
no code was generated, rather than forcing a Python CLI template onto a stack that does not fit.

### Scaffolding a plan you already have

```bash
$ genesis scaffold plan.json ~/my-todo --force
```

`scaffold` takes **any** valid plan JSON — one Genesis produced, or one you wrote by hand. It runs
no model and needs no API key, so it is the fast, free, deterministic half of the pipeline.

### Running locally with Ollama

```bash
$ ollama serve
$ genesis create "a csv to json converter" ./out --adapter ollama --model llama3.1
```

No API key, no token cost. Plan quality tracks the local model — see [`EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md), where
the local model turns out to win end-to-end for a reason worth reading. Point Genesis at a remote
Ollama with `GENESIS_OLLAMA_BASE_URL`. If the server is not running, Genesis says so and tells you
how to start it rather than failing with a stack trace.

### Running it in a container

```bash
docker build -t genesis .
docker run --rm -v "$PWD:/work" genesis scaffold plan.json out
```

The image is `python:3.11-slim`, runs as a non-root user, and carries the template inside the
installed package — so a container can scaffold and then **verify the result builds**, creating a
virtualenv and running the generated repo's tests inside itself. CI builds the image on every push
and fails if a repo scaffolded *inside the container* doesn't install and pass its own tests.

**For local use, `pip install` is better.** A CLI that writes files to your disk fits a container
badly: you need a volume mount, and the output is owned by the container's user. The image exists
so Genesis can be deployed, not so it can be installed.

### Exit codes

`0` success · `1` failure · `2` usage error from argument parsing · `130` interrupted with Ctrl-C.
Failures print one actionable line to stderr — a missing plan key names the key; an unreachable
Ollama server names the command to start it; a prompt with no input left tells you to pass the
value as an argument instead.

