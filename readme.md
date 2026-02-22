# ai-review

CLI for local AI code review by git diff (TypeScript/React + Node.js focus).

## Installation
1. `pipx install -e .`
2. (alternative) venv + pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

`pipx` is convenient for CLI tools because it installs them in isolated environments while still exposing the command globally (by default in `~/.local/bin`).

## Usage
1. `ai-review --staged --provider local`
2. `ai-review --range HEAD~1..HEAD --provider openai --mode deep`

`--staged` reviews what is currently staged in git. `--range` reviews a specific commit range (for example `HEAD~1..HEAD` for the last commit).

## OpenAI provider
1. `OPENAI_API_KEY` (required)
2. `OPENAI_MODEL` (default `gpt-4.1`)

## Local provider (Ollama in Docker)
docker compose up -d
docker exec -it ollama ollama pull qwen2.5-coder:7b

Environment for `ai-review`:
1. `LOCAL_LLM_BASE_URL=http://localhost:11434/v1`
2. `LOCAL_LLM_MODEL=qwen2.5-coder:7b`

## Troubleshooting
1. VSCode terminal does not see `ai-review`: add `~/.local/bin` to your `PATH` (macOS/zsh).
2. Connection refused: the container is not running. Run `docker compose up -d`.
3. Model not found: run `docker exec -it ollama ollama pull <model>`.
4. Invalid JSON: use `--mode deep`, reduce `--max-chars`, or try another model.
