---
name: gisoo
description: Use Gisoo (gisoo.pro) to reach many AI models through one prepaid API key. Use when the user wants a second opinion from another model (GPT, Claude, Gemini, DeepSeek, Qwen, Kimi, GLM), wants an image, speech (text-to-speech), music or video generated, wants audio transcribed to text, needs embeddings, or asks about Gisoo credit, model prices or how to connect Gisoo as an OpenAI-compatible API or MCP server. Do not use it for work the current model can do itself.
---

# Gisoo

Gisoo (https://gisoo.pro) is a multi-model AI API. One key gives access to chat models from several vendors, image, speech, transcription, music, video and embedding models. It is OpenAI-compatible, prepaid (no free tier) and billed per request from the account balance.

Docs: https://gisoo.pro/docs · OpenAPI: https://gisoo.pro/api/v1/openapi.json

## 1. Setup

1. Create a key at https://gisoo.pro/app/api/keys (format `sk-gisoo-v1-...`).
2. Export it. Never print it, paste it into a file that is committed, or echo it in logs.

```bash
export GISOO_API_KEY="sk-gisoo-v1-..."
```

- Base URL: `https://gisoo.pro/api/v1`. Servers and users inside Iran can use `https://ir.gisoo.pro/api/v1` instead; the path and key are the same.
- Auth: `Authorization: Bearer $GISOO_API_KEY` (an `X-API-Key` header is also accepted).

## 2. Check the balance (before any paid job)

```bash
curl -s https://gisoo.pro/api/v1/me -H "Authorization: Bearer $GISOO_API_KEY"
# {"object":"account","balance":{"usd":"12.408114","usd_display":"$12.4081"},"status":"active",...}
```

Use `GET /usage` for project spend and `GET /requests/{id}` for the cost of one request.

## 3. Choose a model (free to call)

`GET /models` needs no key. Filter by type: `chat`, `embedding`, `image`, `audio_stt` (transcription), `audio_tts` (speech), `video`, `music`, `moderation`.

```bash
curl -s "https://gisoo.pro/api/v1/models?type=chat" | python3 -c "import sys,json;[print(m['id'],m['pricing']) for m in json.load(sys.stdin)['data'][:40]]"
curl -s https://gisoo.pro/api/v1/models/deepseek-v4-flash      # one model: capabilities, context, price
```

Prices are USD per million tokens unless the pricing key says otherwise (`per_image`, `per_minute`, `per_second`, `per_million_characters`, `per_request`).

Examples that exist at the time of writing. Check `/models` before relying on any of them, because the catalogue changes:

| Need | Cheap / fast | Stronger |
|---|---|---|
| Chat | `qwen-flash`, `gpt-5.6-luna`, `deepseek-v4-flash` | `claude-sonnet-5`, `gpt-5.5`, `gemini-3.6-flash` |
| Image | `gpt-image-2` (low quality) | `gemini-3-pro-image` |
| Speech | `tts-1` | `gpt-4o-mini-tts`, `gemini-3.8-flash-tts` |
| Transcription | `whisper-1` (verbose_json, translation), `gpt-transcribe` | `gemini-3.5-transcribe` (diarization) |
| Video | `veo-3.1-lite`, `sora-2` | `sora-2-pro`, `veo-3.1` |
| Music | `lyria-3-clip-preview` (30 s clip) | `lyria-3-pro-preview` (lyrics) |
| Embeddings | `text-embedding-3-small` | `gemini-embedding-2` (multimodal) |

## 4. Cost discipline

- Use the cheapest model that is adequate. Escalate only when the cheap answer is visibly wrong.
- Read the price in `/models` before a big job; multiply by the expected size and say the estimate to the owner.
- Set `max_tokens` on chat calls and keep `n=1`. Output tokens are the expensive part.
- Never loop paid calls (retries, polling loops, batch jobs) without a cap and a stop condition.
- Generate one candidate, not five, unless the owner asks for variants.

## 5. Recipes

### 5.1 Chat (second opinion from another model)

Pick a model from a different vendor than the one you are running, so the opinion is independent.

```bash
curl -s https://gisoo.pro/api/v1/chat/completions \
  -H "Authorization: Bearer $GISOO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-5","max_tokens":800,
       "messages":[{"role":"system","content":"You review code. Be brief."},
                   {"role":"user","content":"Is this retry loop safe? ..."}]}'
# answer: .choices[0].message.content   usage: .usage
```

Options that are accepted: `temperature`, `top_p`, `stop`, `seed`, `response_format` (`{"type":"json_object"}`), `tools` / `tool_choice`, `reasoning_effort` (`minimal|low|medium|high`), `stream` (SSE). Use `max_completion_tokens` for OpenAI reasoning models; `max_tokens` is accepted too.

```python
import os
from openai import OpenAI   # pip install openai  (or: pip install gisoo, then `from gisoo import Gisoo; client = Gisoo()`)

client = OpenAI(base_url="https://gisoo.pro/api/v1", api_key=os.environ["GISOO_API_KEY"])
r = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Explain idempotency keys in two sentences."}],
    max_tokens=300,
)
print(r.choices[0].message.content)
```

### 5.2 Image generation (save the file)

```bash
curl -sf https://gisoo.pro/api/v1/images/generations \
  -H "Authorization: Bearer $GISOO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2","prompt":"flat logo of a fox in a circle, no text","size":"1024x1024","quality":"low","n":1}' \
  | python3 -c "import sys,json,base64;d=json.load(sys.stdin);open('out.png','wb').write(base64.b64decode(d['data'][0]['b64_json']))"
```

The result is always base64 in `data[].b64_json`. Allowed sizes and qualities per model are in `capabilities` in `/models`. `output_format` (`png|jpeg|webp`) and `background` (`transparent|opaque|auto`) are accepted.

```python
import base64, os
from openai import OpenAI
client = OpenAI(base_url="https://gisoo.pro/api/v1", api_key=os.environ["GISOO_API_KEY"])
r = client.images.generate(model="gpt-image-2", prompt="flat logo of a fox", size="1024x1024", quality="low")
open("out.png", "wb").write(base64.b64decode(r.data[0].b64_json))
```

### 5.3 Text to speech (save the audio)

```bash
curl -sf https://gisoo.pro/api/v1/audio/speech \
  -H "Authorization: Bearer $GISOO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"alloy","input":"Hello from Gisoo.","response_format":"mp3"}' \
  -o out.mp3
```

Input is at most 4096 characters per request. Voices for `tts-1`: `alloy echo fable onyx nova shimmer`; other models list theirs in `capabilities.voices`. `gpt-4o-mini-tts` accepts `instructions` (tone). Formats: `mp3 opus aac flac wav pcm`.

```python
from openai import OpenAI
import os
client = OpenAI(base_url="https://gisoo.pro/api/v1", api_key=os.environ["GISOO_API_KEY"])
with client.audio.speech.with_streaming_response.create(model="tts-1", voice="alloy", input="Hello.") as r:
    r.stream_to_file("out.mp3")
```

### 5.4 Transcription (audio to text)

Upload as multipart, field `file`, at most 25 MB (mp3, mp4, m4a, wav, webm, ogg). `language=fa` helps Persian. Use `response_format=srt` or `vtt` for subtitles.

```bash
curl -sf https://gisoo.pro/api/v1/audio/transcriptions \
  -H "Authorization: Bearer $GISOO_API_KEY" \
  -F model=whisper-1 -F language=fa -F file=@meeting.mp3
# {"text":"..."}
```

```python
from openai import OpenAI
import os
client = OpenAI(base_url="https://gisoo.pro/api/v1", api_key=os.environ["GISOO_API_KEY"])
with open("meeting.mp3", "rb") as f:
    t = client.audio.transcriptions.create(model="whisper-1", file=f, language="fa")
print(t.text)
```

`POST /audio/translations` returns English text from any-language audio.

### 5.5 Music (one clip, saved)

The request returns the whole clip in one response (MP3 as base64). Price is per clip (`per_request`), not per token. Do not send music models to `/chat/completions`.

```bash
curl -sf https://gisoo.pro/api/v1/audio/music \
  -H "Authorization: Bearer $GISOO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"lyria-3-clip-preview","prompt":"calm lo-fi piano, 80 bpm, no vocals"}' \
  | python3 -c "import sys,json,base64;d=json.load(sys.stdin);open('clip.mp3','wb').write(base64.b64decode(d['data'][0]['b64_json']))"
```

For a song with lyrics use `lyria-3-pro-preview` or `lyria-3.5` and put the lyrics in the prompt.

### 5.6 Video (async job, poll, download)

Video takes one to two minutes, so the create call returns a job, not a file. The job cost is charged at acceptance and refunded if no video is produced (`refunded: true`).

```bash
H="Authorization: Bearer $GISOO_API_KEY"
VID=$(curl -sf https://gisoo.pro/api/v1/videos -H "$H" -H "Content-Type: application/json" \
  -d '{"model":"veo-3.1-lite","prompt":"a paper boat on a calm lake at dawn","seconds":"4","size":"1280x720"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
# poll until status is completed or failed (queued, in_progress, completed, failed)
for i in $(seq 1 40); do
  S=$(curl -sf https://gisoo.pro/api/v1/videos/$VID -H "$H" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  echo "$S"; [ "$S" = completed ] || [ "$S" = failed ] && break; sleep 10
done
curl -sf "https://gisoo.pro/api/v1/videos/$VID/content?variant=video" -H "$H" -o out.mp4
```

Cap the poll loop (above: about 7 minutes). If the status is `failed`, read `error` in the job and stop; do not resubmit in a loop. `seconds` is `4`, `8` or `12` for `sora-2`; `4`, `6` or `8` for `veo-3.1` models. Sizes per model are in `capabilities.sizes`. `DELETE /videos/{id}` cancels or removes a job.

### 5.7 Embeddings

```bash
curl -sf https://gisoo.pro/api/v1/embeddings -H "Authorization: Bearer $GISOO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-3-small","input":["first text","second text"]}'
# .data[i].embedding
```

`dimensions` shortens the vector for `text-embedding-3-*` and Gemini models.

## 6. Use the MCP server instead of raw calls

Gisoo runs a remote MCP server (tools only, Bearer key, no OAuth) at `https://gisoo.pro/api/mcp`. Use it when the coding agent should call Gisoo as tools rather than write code.

- Claude Code (all projects):
  ```bash
  claude mcp add --transport http --scope user gisoo https://gisoo.pro/api/mcp \
    --header "Authorization: Bearer $GISOO_API_KEY"
  ```
  Check with `/mcp` inside Claude Code.
- Cursor (`~/.cursor/mcp.json` or `.cursor/mcp.json`):
  ```json
  { "mcpServers": { "gisoo": { "url": "https://gisoo.pro/api/mcp",
      "headers": { "Authorization": "Bearer sk-gisoo-v1-..." } } } }
  ```
- Claude Code or any other client that talks to Gisoo as an Anthropic API: `ANTHROPIC_BASE_URL=https://gisoo.pro/api` and `ANTHROPIC_AUTH_TOKEN=$GISOO_API_KEY`.
- Other clients (VS Code, Cline, Claude Desktop, Codex CLI): see https://gisoo.pro/docs/mcp and https://gisoo.pro/docs/claude-code.

Keep the key out of committed config files; prefer the environment variable or the client's own secret store.

## 7. Helper script (stdlib only)

`scripts/gisoo.py` wraps the common calls with no dependencies beyond Python 3.8+. It needs `GISOO_API_KEY` except for `models`.

```bash
python3 scripts/gisoo.py models --type chat
python3 scripts/gisoo.py balance
python3 scripts/gisoo.py chat deepseek-v4-flash "Summarise RFC 9110 in 3 bullets" --max-tokens 300
python3 scripts/gisoo.py image gpt-image-2 "a fox logo" -o fox.png --quality low
python3 scripts/gisoo.py speak tts-1 "Hello" -o hello.mp3 --voice nova
python3 scripts/gisoo.py transcribe whisper-1 meeting.mp3 --language fa
```

## 8. Errors and safety

- Errors come back as `{"error":{"message":"...","code":"..."}}`. Read `message` and report it. `code` is stable for decisions.
- A balance or key problem (`suspended`, expired, IP not allowed) stops the job. Tell the owner; do not work around it.
- Generated content is paid output. Save results to files and show the owner the path and the cost, not a long dump.
- Do not send credentials, client data or personal data to a model the owner has not approved for that data.
