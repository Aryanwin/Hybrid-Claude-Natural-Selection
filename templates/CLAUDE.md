# Local models first

Free local models (Ollama on this computer) are available through the `local-evolve` MCP tools and
`{REPO}/evolve.py`. Use them to save Claude usage:

- Before writing any NEW file over ~50 lines, draft it with `local_draft` (or `local_evolve` with a concrete
  rubric when quality matters), then review, fix and finish the result yourself.
- Also draft tests, docs, README sections and long prose answers locally first.
- For self-contained coding tasks with a clear spec, run `evolve.py` first (from inside the target git repo,
  work committed): `python3 "{REPO}/evolve.py" "<task>" --files <file>`. Take over directly if it fails.
- Do debugging, running commands, small edits to existing files and short answers directly.
- If `local_models` reports Ollama offline, work normally and mention that `start_ollama.py` isn't running.
- If you skip the local models for any part of a task, say which part and why.
