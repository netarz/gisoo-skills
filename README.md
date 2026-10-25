# gisoo-skills

An agent skill for [Gisoo](https://gisoo.pro): one prepaid API key for many AI models, usable from Claude Code, Codex and other coding agents.

The skill tells the agent when to use Gisoo (a second opinion from another model, images, speech, music, video, transcription, embeddings) and how to call it with curl, the OpenAI SDK, or the bundled stdlib helper. It also covers the Gisoo MCP server.

- API docs: https://gisoo.pro/docs
- OpenAPI spec: https://gisoo.pro/api/v1/openapi.json
- Get a key: https://gisoo.pro/app/api/keys (prepaid, no free tier)

## Install

Set the key first:

```bash
export GISOO_API_KEY="sk-gisoo-v1-..."
```

### Claude Code: plugin marketplace

```text
/plugin marketplace add netarz/gisoo-skills
/plugin install gisoo@gisoo-skills
```

### Claude Code: copy the skill

```bash
git clone https://github.com/netarz/gisoo-skills.git
mkdir -p ~/.claude/skills && cp -r gisoo-skills/skills/gisoo ~/.claude/skills/gisoo
```

### Codex (and other agents that read SKILL.md)

```bash
git clone https://github.com/netarz/gisoo-skills.git
mkdir -p ~/.codex/skills && cp -r gisoo-skills/skills/gisoo ~/.codex/skills/gisoo
```

### Any agent: skills CLI

```bash
npx skills add netarz/gisoo-skills
```

### MCP instead of the skill

Gisoo also runs a remote MCP server at `https://gisoo.pro/api/mcp`:

```bash
claude mcp add --transport http --scope user gisoo https://gisoo.pro/api/mcp \
  --header "Authorization: Bearer $GISOO_API_KEY"
```

Cursor, VS Code and other clients: https://gisoo.pro/docs/mcp

## Helper script

```bash
python3 skills/gisoo/scripts/gisoo.py models --type chat
python3 skills/gisoo/scripts/gisoo.py balance
python3 skills/gisoo/scripts/gisoo.py chat deepseek-v4-flash "Say hi in Persian" --max-tokens 60
python3 skills/gisoo/scripts/gisoo.py image gpt-image-2 "a fox logo" -o fox.png --quality low
python3 skills/gisoo/scripts/gisoo.py speak tts-1 "Hello" -o hello.mp3
python3 skills/gisoo/scripts/gisoo.py transcribe whisper-1 meeting.mp3 --language fa
```

The script uses only the Python standard library. `models` needs no key; everything else calls the paid API and needs `GISOO_API_KEY`. Set `GISOO_BASE_URL=https://ir.gisoo.pro/api/v1` for servers inside Iran.

## Repository layout

```text
.claude-plugin/marketplace.json   Claude Code marketplace entry
.claude-plugin/plugin.json        Claude Code plugin manifest
skills/gisoo/SKILL.md             the skill (Agent Skills format)
skills/gisoo/scripts/gisoo.py     stdlib-only helper
```

## Cost

Gisoo bills per request from the account balance. The skill tells the agent to check prices with `/models` and to keep paid loops capped. Check `/me` for the balance.

## License

MIT. See [LICENSE](LICENSE).
