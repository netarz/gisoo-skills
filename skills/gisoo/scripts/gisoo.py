#!/usr/bin/env python3
"""Gisoo helper: models, balance, chat, image, speak, transcribe.

Standard library only (Python 3.8+). Needs GISOO_API_KEY except for `models`.
Environment:
  GISOO_API_KEY    key from https://gisoo.pro/app/api/keys
  GISOO_BASE_URL   default https://gisoo.pro/api/v1 (use https://ir.gisoo.pro/api/v1 inside Iran)
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("GISOO_BASE_URL", "https://gisoo.pro/api/v1").rstrip("/")
UA = "gisoo-skill/1.0 (+https://github.com/netarz/gisoo-skills)"
MAX_UPLOAD = 25 * 1024 * 1024


def die(msg, code=1):
    print(f"gisoo: {msg}", file=sys.stderr)
    sys.exit(code)


def api_key():
    key = os.environ.get("GISOO_API_KEY", "").strip()
    if not key:
        die("set GISOO_API_KEY (sk-gisoo-v1-...) from https://gisoo.pro/app/api/keys")
    return key


def call(method, path, payload=None, raw=None, ctype=None, auth=True, timeout=300):
    """Return (body_bytes, content_type). Exits with the API's error message on HTTP errors."""
    headers = {"User-Agent": UA, "Accept": "application/json, audio/*, video/*"}
    if auth:
        headers["Authorization"] = "Bearer " + api_key()
    data = raw
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            err = json.loads(body)["error"]
            msg = f"{err.get('message')} (code: {err.get('code')})"
        except (ValueError, KeyError, TypeError):
            msg = body[:300].decode("utf-8", "replace")
        die(f"HTTP {e.code}: {msg}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")


def get_json(path, auth=True):
    body, _ = call("GET", path, auth=auth)
    return json.loads(body)


def post_json(path, payload):
    body, _ = call("POST", path, payload=payload)
    return json.loads(body)


def price_text(pricing):
    parts = [f"{k}={v}" for k, v in (pricing or {}).items() if k != "long_context_threshold"]
    return ", ".join(parts)[:90]


def cmd_models(a):
    q = "?" + urllib.parse.urlencode({"type": a.type}) if a.type else ""
    models = get_json("/models" + q, auth=False)["data"]
    for m in models[: a.limit]:
        print(f"{m['id']}\t{m.get('type')}\t{price_text(m.get('pricing'))}")


def cmd_balance(_a):
    acct = get_json("/me")
    bal = acct.get("balance", {})
    print(f"balance: {bal.get('usd_display', bal.get('usd'))}  status: {acct.get('status')}")


def read_prompt(text):
    return sys.stdin.read().strip() if text == "-" else text


def cmd_chat(a):
    messages = []
    if a.system:
        messages.append({"role": "system", "content": a.system})
    messages.append({"role": "user", "content": read_prompt(a.prompt)})
    payload = {"model": a.model, "messages": messages, "max_tokens": a.max_tokens}
    if a.temperature is not None:
        payload["temperature"] = a.temperature
    res = post_json("/chat/completions", payload)
    print(res["choices"][0]["message"]["content"])
    usage = res.get("usage") or {}
    print(f"[tokens in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}]", file=sys.stderr)


def cmd_image(a):
    payload = {"model": a.model, "prompt": a.prompt, "size": a.size, "n": 1}
    if a.quality:
        payload["quality"] = a.quality
    res = post_json("/images/generations", payload)
    with open(a.out, "wb") as f:
        f.write(base64.b64decode(res["data"][0]["b64_json"]))
    print(f"saved {a.out}")


def cmd_speak(a):
    payload = {"model": a.model, "input": read_prompt(a.text), "voice": a.voice, "response_format": a.format}
    body, _ = call("POST", "/audio/speech", payload=payload)
    with open(a.out, "wb") as f:
        f.write(body)
    print(f"saved {a.out} ({len(body)} bytes)")


def multipart(fields, filename, filedata, mime):
    boundary = uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )
    chunks.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        + filedata
        + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def cmd_transcribe(a):
    size = os.path.getsize(a.file)
    if size > MAX_UPLOAD:
        die(f"file is {size} bytes; the limit is 25 MB")
    with open(a.file, "rb") as f:
        data = f.read()
    mime = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".mp4": "video/mp4",
            ".webm": "audio/webm", ".ogg": "audio/ogg"}.get(os.path.splitext(a.file)[1].lower(), "application/octet-stream")
    fields = {"model": a.model, "response_format": a.response_format}
    if a.language:
        fields["language"] = a.language
    body, ctype = multipart(fields, os.path.basename(a.file), data, mime)
    raw, _ = call("POST", "/audio/transcriptions", raw=body, ctype=ctype)
    try:
        out = json.loads(raw)
        print(out.get("text", raw.decode("utf-8", "replace")))
    except ValueError:
        print(raw.decode("utf-8", "replace"))


def build_parser():
    p = argparse.ArgumentParser(prog="gisoo.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("models", help="list models (no key needed)")
    m.add_argument("--type", choices=["chat", "embedding", "image", "audio_stt", "audio_tts", "video", "music", "moderation"])
    m.add_argument("--limit", type=int, default=200)
    m.set_defaults(fn=cmd_models)

    sub.add_parser("balance", help="show account balance").set_defaults(fn=cmd_balance)

    c = sub.add_parser("chat", help="ask one model; prompt '-' reads stdin")
    c.add_argument("model")
    c.add_argument("prompt")
    c.add_argument("--system")
    c.add_argument("--max-tokens", type=int, default=800)
    c.add_argument("--temperature", type=float)
    c.set_defaults(fn=cmd_chat)

    i = sub.add_parser("image", help="generate an image and save it")
    i.add_argument("model")
    i.add_argument("prompt")
    i.add_argument("-o", "--out", default="image.png")
    i.add_argument("--size", default="1024x1024")
    i.add_argument("--quality")
    i.set_defaults(fn=cmd_image)

    s = sub.add_parser("speak", help="text to speech; saves audio")
    s.add_argument("model")
    s.add_argument("text", help="text, or '-' for stdin (max 4096 characters)")
    s.add_argument("-o", "--out", default="speech.mp3")
    s.add_argument("--voice", default="alloy")
    s.add_argument("--format", default="mp3", choices=["mp3", "opus", "aac", "flac", "wav", "pcm"])
    s.set_defaults(fn=cmd_speak)

    t = sub.add_parser("transcribe", help="audio to text (max 25 MB)")
    t.add_argument("model")
    t.add_argument("file")
    t.add_argument("--language", help="e.g. fa, en")
    t.add_argument("--response-format", dest="response_format", default="json",
                   choices=["json", "text", "srt", "vtt", "verbose_json"])
    t.set_defaults(fn=cmd_transcribe)
    return p


def main():
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
