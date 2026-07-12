# TokenMeter

Track and estimate your LLM API token usage and costs with zero external dependencies.

## Features

- **Auto-record** — Wraps OpenAI/DeepSeek API calls and logs every request automatically
- **Cost estimation** — Exact match for repeated prompts (hash-based), rough estimate for new ones
- **Privacy-first** — Never stores prompt content, only SHA256 hash + token counts + cost
- **Multi-model** — Built-in pricing for GPT-5.5, GPT-5.4, DeepSeek (add your own in 2 lines)
- **SQLite storage** — Single file, portable, no database setup
- **Zero dependencies** — Uses only Python standard library (urllib, sqlite3, hashlib)

## Quick Start

```bash
# Record an API call
python token_meter.py rec --t "Hello" --pt 5 --ct 10 --m deepseek-chat

# Estimate cost for a new prompt
python token_meter.py est --t "Hello" --m deepseek-chat

# View total stats
python token_meter.py sts
```

## Programmatic Usage

```python
from token_meter import call_chat, call_responses, sts

# Auto-record Chat Completions API calls
text, info = call_chat("Explain RAG in one sentence", model="deepseek-chat", api_key="sk-xxx")
print(f"Cost: ${info['cost']}")

# View accumulated stats
print(sts())  # {calls, cost, pt, ct}
```

## Supported Models (with built-in pricing)

| Model | Input ($/M tokens) | Output ($/M tokens) |
|---|---|---|
| gpt-5.5 | $15.00 | $60.00 |
| gpt-5.5-pro | $30.00 | $120.00 |
| gpt-5.4 | $10.00 | $40.00 |
| deepseek-chat | $0.14 | $0.28 |
| deepseek-reasoner | $0.55 | $2.19 |

## How It Works

1. Every call generates a SHA256 hash of the prompt text (not the text itself)
2. Records: hash | prompt_tokens | completion_tokens | model | cost | timestamp
3. When estimating, checks for exact hash match first, falls back to character-count estimation
4. All data stored in a local SQLite file (`token_meter.db`)

## Privacy

- **No prompt text is ever stored** — only a SHA256 hash
- The database is local — no data is sent anywhere
- Share your `token_meter.db` with friends to compare costs without exposing your prompts

## License

MIT