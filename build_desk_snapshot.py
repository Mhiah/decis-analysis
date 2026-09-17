"""Build Decis Analysis desk snapshot from IAA research artifacts.

Outputs:
  desk/data/desk_snapshot.json              — Decis UI contract (camelCase)
  desk/decis-ui/public/desk_snapshot.json   — served by Vite for the UI

Run from iaa project root:
  python desk/build_desk_snapshot.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK = Path(__file__).resolve().parent
SCHEMA_VERSION = "1.0.0"


def latest(pattern: str) -> Path:
    matches = sorted(ROOT.joinpath("reports").glob(pattern))
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[-1]


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def downsample_path(observations: list[dict], max_points: int = 64) -> list[dict]:
    if not observations:
        return []
    step = max(1, len(observations) // max_points)
    points = []
    for index, item in enumerate(observations):
        if index % step == 0 or index == len(observations) - 1:
            points.append(
                {
                    "t": round(float(item["elapsed_minutes"]), 2),
                    "ret": float(item["observed_return"]),
                }
            )
    return points


def main() -> None:
    events = load_jsonl(ROOT / "data" / "events_sec_combined30.jsonl")
    scores = load_jsonl(ROOT / "data" / "event_scores_combined30.jsonl")
    replay = json.loads((ROOT / "reports" / "replay-combined30.json").read_text(encoding="utf-8"))
    cal = json.loads(latest("calibration-*.json").read_text(encoding="utf-8"))
    benches = sorted(ROOT.joinpath("reports").glob("benchmark-*.json"))
    bench = json.loads(benches[-1].read_text(encoding="utf-8"))
    papers = sorted(ROOT.joinpath("reports").glob("paper-execution-*.json"))
    paper = json.loads(papers[-1].read_text(encoding="utf-8")) if papers else {}

    score_by = {item["event_id"]: item for item in scores}
    replay_by = {item["event_id"]: item for item in replay.get("replays", [])}

    instruments = []
    for event in events:
        score = score_by.get(event["event_id"], {})
        replay_row = replay_by.get(event["event_id"], {})
        observations = replay_row.get("observations") or []
        instruments.append(
            {
                "eventId": event["event_id"],
                "ticker": event.get("underlying_ticker"),
                "token": event.get("token_symbol"),
                "publishedAt": event.get("published_at"),
                "timestampSemantics": event.get("timestamp_semantics") or "unknown",
                "issuerClockValidated": bool(event.get("issuer_release_time_validated")),
                "direction": score.get("direction") or "neutral",
                "surprise": score.get("source_surprise_fraction"),
                "importance": score.get("importance") or "unknown",
                "horizonReturn": replay_row.get("horizon_observed_return"),
                "firstReturn": observations[0]["observed_return"] if observations else None,
                "tradeBlockers": score.get("trade_blockers") or [],
                "path": downsample_path(observations),
            }
        )

    instruments.sort(key=lambda item: item["publishedAt"] or "")

    holdout = cal.get("holdout_metrics") or {}
    snapshot = {
        "schemaVersion": SCHEMA_VERSION,
        "product": "Decis Analysis",
        "track": "AI Trading Desk",
        "tagline": "AI processes the research. You make the call.",
        "updatedAt": bench.get("created_at") or cal.get("created_at"),
        "posture": {
            "strategyEdgeValidated": bool(bench.get("strategy_edge_validated")),
            "calibrationSuccessful": bool(cal.get("calibration_successful")),
            "paperExecutionValidated": bool(paper.get("paper_execution_validated")),
            "refusalReasons": bench.get("refusal_reasons") or [],
            "paperRefusalReasons": paper.get("refusal_reasons") or [],
            "holdoutDirectionAccuracy": holdout.get("direction_accuracy"),
            "holdoutMae": holdout.get("mae"),
        },
        "gates": {
            "events": len(instruments),
            "issuerClocksValidated": sum(
                1 for event in events if event.get("issuer_release_time_validated")
            ),
            "immutableConsensus": sum(
                1 for score in scores if score.get("immutable_consensus_snapshot")
            ),
            "calibration": (
                "accepted_fit_edge_refused"
                if cal.get("calibration_successful")
                else "refused"
            ),
            "paper": "blocked" if not paper.get("paper_execution_validated") else "validated",
            "live": "blocked",
        },
        "instruments": instruments,
    }

    out_data = DESK / "data" / "desk_snapshot.json"
    out_public = DESK / "decis-ui" / "public" / "desk_snapshot.json"
    out_data.parent.mkdir(parents=True, exist_ok=True)
    out_public.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, indent=2)
    out_data.write_text(payload, encoding="utf-8")
    out_public.write_text(payload, encoding="utf-8")

    # Keep legacy snake_case builder entrypoint compatible via thin wrapper note
    print(
        json.dumps(
            {
                "schemaVersion": SCHEMA_VERSION,
                "output": str(out_data),
                "uiCopy": str(out_public),
                "instruments": len(instruments),
                "strategyEdgeValidated": snapshot["posture"]["strategyEdgeValidated"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
