"""Tiny JSON-over-HTTP helpers on top of the standard library (no web framework needed)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse


class JSONHandler(BaseHTTPRequestHandler):
    """Base handler: subclasses implement route(method, path, query, body, headers)."""

    server_version = "inferentienet-mock/0.1"
    quiet = True

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - signature from the stdlib
        if not self.quiet:
            super().log_message(format, *args)

    def _read_body(self) -> Any:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"request body is not valid JSON: {exc}") from exc

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        try:
            body = self._read_body() if method == "POST" else {}
            status, payload, headers = self.route(method, parsed.path, query, body, self.headers)
        except ValueError as exc:
            status, payload, headers = 400, {"error": str(exc)}, {}
        self.send_json(status, payload, headers)

    def send_json(self, status: int, payload: Any, headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - name required by BaseHTTPRequestHandler
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802 - name required by BaseHTTPRequestHandler
        self._dispatch("POST")

    def route(self, method, path, query, body, headers):  # pragma: no cover - implemented by subclasses
        raise NotImplementedError


def request_json(
    url: str, payload: Any | None = None, headers: dict[str, str] | None = None, timeout: float = 5.0
) -> tuple[int, Any, dict[str, str]]:
    """POST (when payload is given) or GET a JSON endpoint. Returns (status, body, headers)."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "null"), dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = {"error": raw}
        return err.code, body, dict(err.headers)
