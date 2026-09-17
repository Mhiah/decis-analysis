"""Tiny Bitget market sidecar for Decis UI.

Public market data only — no keys, no orders.
Uses IAA BitgetProvider with DNS-over-HTTPS fallback.

Endpoints:
  GET  /quote?symbol=RAMDUSDT
  GET  /instruments          — Reality (rToken) universe
  POST /research-request     — queue rToken research → iaacontact2026@gmail.com

Run from iaa root:
  python desk/live_quotes.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from iaa.providers import BitgetProvider  # noqa: E402

HOST = "127.0.0.1"
PORT = 8788
CACHE_TTL_SEC = 300
RESEARCH_INBOX = "iaacontact2026@gmail.com"
REQUEST_LOG = Path(__file__).resolve().parent / "data" / "research_requests.jsonl"


class Handler(BaseHTTPRequestHandler):
    provider = BitgetProvider(dns_fallback=True, timeout=25)
    _instruments_cache: dict | None = None
    _instruments_cached_at = 0.0

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/quote", "/api/live/quote"):
            self._quote(parsed)
            return
        if path in ("/instruments", "/api/live/instruments"):
            self._instruments()
            return
        self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/research-request", "/api/live/research-request"):
            self._research_request()
            return
        self._send(404, {"ok": False, "error": "not found"})

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 16_384:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _research_request(self) -> None:
        body = self._read_json_body()
        symbol = str(body.get("symbol") or "").strip().upper().replace(" ", "")
        if not symbol:
            self._send(400, {"ok": False, "error": "symbol required"})
            return

        at = datetime.now(timezone.utc).isoformat()
        record = {
            "at": at,
            "symbol": symbol,
            "etaDays": 3,
            "inbox": RESEARCH_INBOX,
            "source": "decis-ui",
            "note": str(body.get("note") or "").strip() or None,
        }

        mailed = False
        mail_error = None
        try:
            mailed = _email_research_request(record)
        except Exception as exc:  # noqa: BLE001 — soft-fail; UI may mailto
            mail_error = str(exc)

        _append_request_log({**record, "mailed": mailed, "mailError": mail_error})

        self._send(
            200,
            {
                "ok": True,
                "symbol": symbol,
                "etaDays": 3,
                "inbox": RESEARCH_INBOX,
                "mailed": mailed,
                "mailError": mail_error,
                "at": at,
            },
        )

    def _quote(self, parsed) -> None:
        symbol = (parse_qs(parsed.query).get("symbol") or [""])[0].strip().upper()
        if not symbol or not symbol.endswith("USDT"):
            self._send(400, {"ok": False, "error": "symbol required, e.g. RAMDUSDT"})
            return

        result = self.provider.ticker(symbol)
        if not result.get("ok"):
            self._send(
                502,
                {
                    "ok": False,
                    "symbol": symbol,
                    "error": result.get("error") or "bitget ticker failed",
                    "errorKind": result.get("error_kind"),
                    "url": result.get("url"),
                    "retrievedAt": result.get("retrieved_at"),
                },
            )
            return

        rows = (result.get("body") or {}).get("data") or []
        row = rows[0] if rows else {}
        self._send(
            200,
            {
                "ok": True,
                "symbol": symbol,
                "source": "bitget",
                "live": True,
                "retrievedAt": result.get("retrieved_at"),
                "lastPrice": _num(row.get("lastPrice")),
                "bid": _num(row.get("bid1Price")),
                "ask": _num(row.get("ask1Price")),
                "change24h": _num(row.get("price24hPcnt")),
                "high24h": _num(row.get("highPrice24h")),
                "low24h": _num(row.get("lowPrice24h")),
                "volume24h": _num(row.get("volume24h")),
                "ts": row.get("ts"),
            },
        )

    def _instruments(self) -> None:
        now = time.time()
        if (
            Handler._instruments_cache is not None
            and now - Handler._instruments_cached_at < CACHE_TTL_SEC
        ):
            self._send(200, Handler._instruments_cache)
            return

        result = self.provider.instruments()
        if not result.get("ok"):
            self._send(
                502,
                {
                    "ok": False,
                    "error": result.get("error") or "bitget instruments failed",
                    "errorKind": result.get("error_kind"),
                },
            )
            return

        rows = (result.get("body") or {}).get("data") or []
        universe = []
        for row in rows:
            if str(row.get("isReality", "")).lower() != "yes":
                continue
            if str(row.get("status", "")).lower() not in ("online", ""):
                continue
            symbol = str(row.get("symbol") or "").upper()
            if not symbol.endswith("USDT"):
                continue
            base = str(row.get("baseCoin") or "")
            ticker = _ticker_from_base(base, symbol)
            universe.append(
                {
                    "token": symbol,
                    "ticker": ticker,
                    "baseCoin": base,
                    "status": row.get("status") or "online",
                }
            )

        universe.sort(key=lambda item: item["ticker"])
        payload = {
            "ok": True,
            "source": "bitget",
            "retrievedAt": result.get("retrieved_at"),
            "count": len(universe),
            "instruments": universe,
        }
        Handler._instruments_cache = payload
        Handler._instruments_cached_at = now
        self._send(200, payload)


def _append_request_log(record: dict) -> None:
    REQUEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with REQUEST_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def _email_research_request(record: dict) -> bool:
    """Deliver to RESEARCH_INBOX via FormSubmit (no SMTP secrets in repo)."""
    payload = {
        "_subject": f"Decis research request: {record['symbol']}",
        "_template": "table",
        "_captcha": "false",
        "symbol": record["symbol"],
        "etaDays": record["etaDays"],
        "at": record["at"],
        "source": record["source"],
        "note": record.get("note") or "(none)",
        "message": (
            f"New Decis research package request for {record['symbol']}. "
            f"Expected turnaround: up to {record['etaDays']} days."
        ),
    }
    req = Request(
        f"https://formsubmit.co/ajax/{RESEARCH_INBOX}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DecisAnalysis/1.0",
        },
        method="POST",
    )
    with urlopen(req, timeout=20) as resp:
        status = getattr(resp, "status", 200)
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        body = {}
    if isinstance(body, dict) and body.get("success") in (True, "true"):
        return True
    if 200 <= int(status) < 300:
        return True
    raise RuntimeError(
        (body.get("message") if isinstance(body, dict) else None)
        or raw
        or "mail relay failed"
    )


def _ticker_from_base(base: str, symbol: str) -> str:
    cleaned = base.strip()
    if cleaned.lower().startswith("r") and len(cleaned) > 1:
        cleaned = cleaned[1:]
    if cleaned:
        return cleaned.upper()
    if symbol.startswith("R") and symbol.endswith("USDT"):
        return symbol[1:-4]
    return symbol


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    """Serve forever; restart the listener if it exits unexpectedly."""
    while True:
        try:
            server = ThreadingHTTPServer((HOST, PORT), Handler)
            print(
                json.dumps(
                    {
                        "quote": f"http://{HOST}:{PORT}/quote?symbol=RAMDUSDT",
                        "instruments": f"http://{HOST}:{PORT}/instruments",
                        "researchRequest": f"http://{HOST}:{PORT}/research-request",
                        "inbox": RESEARCH_INBOX,
                    },
                    indent=2,
                )
            )
            server.serve_forever()
        except OSError as exc:
            # Port busy or bind failure — wait and retry so demo stays recoverable
            sys.stderr.write(f"live_quotes bind/serve error: {exc}; retry in 3s\n")
            time.sleep(3)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 — keep sidecar alive for demo
            sys.stderr.write(f"live_quotes crashed: {exc}; restarting in 2s\n")
            time.sleep(2)


if __name__ == "__main__":
    main()
