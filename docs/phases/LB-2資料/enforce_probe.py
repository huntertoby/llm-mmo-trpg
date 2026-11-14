import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
model = sys.argv[1]
url = "http://localhost:8001/v1/chat/completions"
msgs = [{"role": "user", "content": '請輸出 JSON：{"color": "red", "kind": "c", "x": "zz", "a": 1, "b": 2}，不要別的。'}]
A = {"type": "object", "properties": {"kind": {"const": "a"}, "x": {"enum": ["aa"]}}, "required": ["kind", "x"], "additionalProperties": False}
B = {"type": "object", "properties": {"kind": {"const": "b"}, "x": {"enum": ["bb"]}}, "required": ["kind", "x"], "additionalProperties": False}
ENUM = {"type": "object", "properties": {"color": {"enum": ["zzz_only"]}}, "required": ["color"], "additionalProperties": False}
cases = {
    "rf_enum": ("response_format", ENUM),
    "rf_oneOf": ("response_format", {"oneOf": [A, B]}),
    "rf_anyOf": ("response_format", {"anyOf": [A, B]}),
    "rf_maxProps": ("response_format", {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}, "c": {"type": "integer"}}, "maxProperties": 1, "additionalProperties": False}),
    "guided_enum": ("guided_json", ENUM),
}
for name, (mode, schema) in cases.items():
    body = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": 60, "reasoning_effort": "none"}
    if mode == "response_format":
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "r", "schema": schema, "strict": True}}
    else:
        body["guided_json"] = schema
    r = httpx.post(url, json=body, timeout=300)
    try:
        c = r.json()["choices"][0]["message"]["content"]
    except Exception:
        c = r.text[:400]
    print(name, r.status_code, repr(c)[:300], flush=True)
