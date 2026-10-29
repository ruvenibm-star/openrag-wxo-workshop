#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6"]
# ///
"""Command-line helper for the OpenRAG workshop: ingest the sample documents, manage knowledge filters
and settings, ask questions, and check answers against answer-key.yaml.

Every call goes to the OpenRAG backend through the frontend route (<OPENRAG_URL>/api/...), signed in
with HTTP Basic as a Software Hub user. Settings come from the environment, then from
secrets/secrets.env one level above the workshop folder, if it exists:

    OPENRAG_URL                         frontend route, e.g. https://openrag-fe-cpd.apps.<cluster>
    OPENRAG_USERNAME, OPENRAG_PASSWORD  Software Hub user; default CPD_USERNAME and CPD_PASSWORD

Commands:
    whoami                              signed-in user, role and permission count
    files                               documents the user can see
    ingest PATH... [--no-wait]          upload files or folders (recursively) and wait for the task
    delete FILENAME...                  delete documents by file name
    search QUERY [--filter NAME]        hybrid search; prints score, file, page and a text excerpt. Uses the
           [--limit N] [--threshold S]  filter's response limit and score threshold unless given
    chat QUESTION [--filter NAME]       ask the agent; prints the answer and the cited files
    filters                             list knowledge filters
    filter-id NAME                      print the id of a knowledge filter
    filter-apply FILE.json...           create or update knowledge filters from filters/
    filter-delete NAME...               delete knowledge filters by name
    settings [KEY=VALUE...]             show ingestion settings, or change them (ocr, picture_descriptions,
                                        table_structure, chunk_size, chunk_overlap)
    check [--id ID...] [--group G...]   ask the answer-key questions and check each answer
    reset                               delete the workshop documents and filters, restore the instance's
                                        ingestion settings (OCR on, picture descriptions off)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
import yaml

WORKSHOP = Path(__file__).resolve().parent.parent
REPO = WORKSHOP.parent
SAMPLE_DOCS = WORKSHOP / "sample-docs"
FILTERS = WORKSHOP / "filters"
ANSWER_KEY = WORKSHOP / "answer-key.yaml"
DEFAULT_SETTINGS = {"ocr": True, "picture_descriptions": False, "table_structure": True,
                    "chunk_size": 1000, "chunk_overlap": 200}


def load_env():
    env = {}
    secrets = REPO / "secrets" / "secrets.env"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.strip())
            if m:
                env[m[1]] = m[2].strip().strip('"').strip("'")
    get = lambda *keys: next((v for k in keys for v in (os.environ.get(k), env.get(k)) if v), None)
    url, user, password = get("OPENRAG_URL"), get("OPENRAG_USERNAME", "CPD_USERNAME"), get("OPENRAG_PASSWORD", "CPD_PASSWORD")
    if not (url and user and password):
        sys.exit("Set OPENRAG_URL, OPENRAG_USERNAME and OPENRAG_PASSWORD")
    return url.rstrip("/"), user, password


class OpenRAG:
    def __init__(self):
        url, user, password = load_env()
        self.user = user
        self.http = httpx.Client(base_url=f"{url}/api", auth=(user, password), timeout=180.0)
        r = self.http.post("/auth/ibm/login")
        if r.status_code != 200:
            sys.exit(f"Sign-in to {url} as {user} failed: HTTP {r.status_code} {r.text[:200]}")

    def call(self, method, path, **kw):
        r = self.http.request(method, path, **kw)
        if r.status_code >= 400:
            sys.exit(f"{method} {path}: HTTP {r.status_code} {r.text[:500]}")
        return r.json() if r.content else {}

    def files(self):
        out, page = [], 1
        while True:
            data = self.call("GET", "/files", params={"page": page, "page_size": 100})
            out += data["files"]
            if len(out) >= data["total"] or not data["files"]:
                return out
            page += 1

    def filters(self):
        return self.call("POST", "/v1/knowledge-filters/search", json={"query": "", "limit": 100}).get("filters", [])

    def filter_id(self, name):
        if not name:
            return None
        for f in self.filters():
            if f["name"] == name:
                return f["id"]
        sys.exit(f"No knowledge filter named {name!r}")


def expand(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".") and f.name != "README.md")
        elif p.is_file():
            files.append(p)
        else:
            sys.exit(f"Not found: {p}")
    return files


def wait_task(o, task_id, quiet=False):
    last = None
    while True:
        t = o.call("GET", f"/v1/tasks/{task_id}")
        state = (t["status"], t.get("processed_files"), t.get("successful_files"), t.get("failed_files"))
        if state != last and not quiet:
            print(f"  task {task_id[:8]}: {t['status']}, {t.get('processed_files', 0)}/{t.get('total_files', 0)} processed, "
                  f"{t.get('failed_files', 0)} failed")
            last = state
        if t["status"] in ("completed", "failed", "cancelled"):
            return t
        time.sleep(5)


def cmd_whoami(o, a):
    me = o.call("GET", "/users/me")
    print(f"{me['name']} ({me['user_id']}), roles {', '.join(me['roles'])}, {len(me['permissions'])} permissions")


def cmd_files(o, a):
    for f in sorted(o.files(), key=lambda f: f["filename"].lower()):
        print(f"{f['chunk_count']:>4} chunks  {f['owner_name'] or '-':<16} {f['connector_type']:<13} {f['filename']}")


def cmd_ingest(o, a):
    files = expand(a.paths)
    print(f"Uploading {len(files)} file(s) as {o.user}")
    handles = [("file", (f.name, f.open("rb"))) for f in files]
    try:
        r = o.call("POST", "/v1/documents/ingest", files=handles, data={"replace_duplicates": "true"})
    finally:
        for _, (_, fh) in handles:
            fh.close()
    print(f"  {r.get('message')}")
    if a.no_wait:
        print(f"  task_id {r['task_id']}")
        return
    t = wait_task(o, r["task_id"])
    failed = []
    for info in t.get("files", {}).values():
        ok = info.get("status") == "completed"
        if not ok:
            failed.append(info.get("filename"))
        print(f"  {'ok    ' if ok else 'FAILED'} {info.get('filename')}  {info.get('duration_seconds', 0):.0f}s"
              + ("" if ok else f"  {info.get('error')}"))
    if failed:
        sys.exit(1)


def cmd_delete(o, a):
    for name in a.filenames:
        r = o.call("DELETE", "/v1/documents", json={"filename": name})
        print(f"{name}: {r.get('deleted_chunks', r)}")


def cmd_search(o, a):
    body = {"query": a.query, "filter_id": o.filter_id(a.filter)}
    if a.limit is not None:
        body["limit"] = a.limit
    if a.threshold is not None:
        body["score_threshold"] = a.threshold
    for hit in o.call("POST", "/v1/search", json=body)["results"]:
        text = " ".join(hit["text"].split())
        print(f"{hit['score']:6.2f}  {hit['filename']}  page {hit.get('page')}\n        {text[:220]}")


def ask(o, question, filter_name=None):
    body = {"message": question, "filter_id": o.filter_id(filter_name)}
    started = time.time()
    r = o.call("POST", "/v1/chat", json=body)
    names = {f["document_id"]: f["filename"] for f in o.files()}
    cited = []
    for s in r.get("sources", []):
        name = next((n for doc, n in names.items() if doc in s["filename"]), s["filename"])
        if name not in cited:
            cited.append(name)
    if r.get("chat_id"):
        o.http.delete(f"/v1/chat/{r['chat_id']}")
    return r["response"], cited, time.time() - started


def cmd_chat(o, a):
    answer, cited, secs = ask(o, a.question, a.filter)
    print(re.sub(r"\(Source: [^)]+\)", "", answer).strip())
    print(f"\nCited: {', '.join(cited) or 'none'}  ({secs:.0f}s)")


def cmd_filters(o, a):
    for f in o.filters():
        q = json.loads(f["query_data"]) if isinstance(f.get("query_data"), str) else f.get("query_data") or {}
        print(f"{f['name']:<26} {f['id']}  owner {f.get('owner')}\n    query {q.get('query')!r}  filters {json.dumps(q.get('filters'))}")


def cmd_filter_id(o, a):
    print(o.filter_id(a.name))


def cmd_filter_apply(o, a):
    existing = {f["name"]: f["id"] for f in o.filters()}
    for path in map(Path, a.files):
        spec = json.loads(path.read_text())
        body = {"name": spec["name"], "description": spec.get("description", ""), "queryData": json.dumps(spec["queryData"])}
        if spec["name"] in existing:
            o.call("PUT", f"/v1/knowledge-filters/{existing[spec['name']]}", json=body)
            print(f"updated {spec['name']}")
        else:
            o.call("POST", "/v1/knowledge-filters", json=body)
            print(f"created {spec['name']}")


def cmd_filter_delete(o, a):
    existing = {f["name"]: f["id"] for f in o.filters()}
    for name in a.names:
        if name in existing:
            o.call("DELETE", f"/v1/knowledge-filters/{existing[name]}")
            print(f"deleted {name}")


def parse_value(v):
    return {"true": True, "false": False}.get(v.lower(), int(v) if v.isdigit() else v)


def cmd_settings(o, a):
    if a.pairs:
        body = dict(p.split("=", 1) for p in a.pairs)
        o.call("POST", "/settings", json={k: parse_value(v) for k, v in body.items()})
    current = o.call("GET", "/settings")
    k, agent = current["knowledge"], current["agent"]
    print(f"embedding            {k['embedding_provider']}/{k['embedding_model']}")
    print(f"llm                  {agent['llm_provider']}/{agent['llm_model']}")
    for key in DEFAULT_SETTINGS:
        print(f"{key:<21}{k[key]}")


def matches(answer, alternatives):
    norm = lambda s: re.sub(r"[\s·.,]+", " ", s.lower().replace("n·m", "nm").replace("n m", "nm"))
    return any(norm(alt) in norm(answer) for alt in alternatives)


def cmd_check(o, a):
    key = yaml.safe_load(ANSWER_KEY.read_text())
    questions = [q for q in key["questions"]
                 if (not a.id or q["id"] in a.id) and (not a.group or q["group"] in a.group)]
    passed = scored = 0
    for q in questions:
        answer, cited, secs = ask(o, q["question"], q.get("filter"))
        missing = [alts[0] for alts in q.get("expect", []) if not matches(answer, alts)]
        present = [alt for alt in q.get("reject", []) if matches(answer, [alt])]
        ok = not missing and not present
        if q.get("observe"):
            verdict = "SEE "
        else:
            verdict, scored, passed = ("PASS" if ok else "FAIL"), scored + 1, passed + ok
        source = "source cited" if q.get("source") in cited else f"source not cited ({', '.join(cited) or 'none'})"
        print(f"{verdict}  {q['id']:<28} {secs:4.0f}s  {source}")
        if not ok or q.get("observe") or a.verbose:
            print("      " + " ".join(re.sub(r"\(Source: [^)]+\)", "", answer).split())[:600])
            if missing and not q.get("observe"):
                print(f"      missing: {missing}")
            if present:
                print(f"      should not contain: {present}")
    print(f"\n{passed}/{scored} passed")
    sys.exit(0 if passed == scored else 1)


def cmd_reset(o, a):
    names = {f.name for f in expand([SAMPLE_DOCS])}
    for f in o.files():
        if f["filename"] in names:
            o.call("DELETE", "/v1/documents", json={"filename": f["filename"]})
            print(f"deleted document {f['filename']}")
    workshop_filters = {json.loads(p.read_text())["name"] for p in FILTERS.glob("*.json")}
    for f in o.filters():
        if f["name"] in workshop_filters:
            o.call("DELETE", f"/v1/knowledge-filters/{f['id']}")
            print(f"deleted filter {f['name']}")
    o.call("POST", "/settings", json=DEFAULT_SETTINGS)
    print("restored ingestion settings: " + ", ".join(f"{k}={v}" for k, v in DEFAULT_SETTINGS.items()))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    sub.add_parser("files")
    s = sub.add_parser("ingest"); s.add_argument("paths", nargs="+"); s.add_argument("--no-wait", action="store_true")
    s = sub.add_parser("delete"); s.add_argument("filenames", nargs="+")
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--filter"); s.add_argument("--limit", type=int); s.add_argument("--threshold", type=float)
    s = sub.add_parser("chat"); s.add_argument("question"); s.add_argument("--filter")
    sub.add_parser("filters")
    s = sub.add_parser("filter-id"); s.add_argument("name")
    s = sub.add_parser("filter-apply"); s.add_argument("files", nargs="+")
    s = sub.add_parser("filter-delete"); s.add_argument("names", nargs="+")
    s = sub.add_parser("settings"); s.add_argument("pairs", nargs="*")
    s = sub.add_parser("check"); s.add_argument("--id", nargs="*"); s.add_argument("--group", nargs="*"); s.add_argument("-v", "--verbose", action="store_true")
    sub.add_parser("reset")
    a = p.parse_args()
    globals()[f"cmd_{a.cmd.replace('-', '_')}"](OpenRAG(), a)


if __name__ == "__main__":
    main()
