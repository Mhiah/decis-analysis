"""Deterministic, source-backed event scoring without a return forecast."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def score_surprise(surprise):
    value = float(surprise['surprise_fraction'])
    if value > 0:
        direction = 'positive'
    elif value < 0:
        direction = 'negative'
    else:
        direction = 'neutral'
    magnitude = abs(value)
    importance = 'high' if magnitude >= .03 else ('medium' if magnitude >= .01 else 'low')
    immutable = bool(surprise.get('immutable_snapshot_validated'))
    return {
        'event_id': surprise['event_id'], 'direction': direction,
        'magnitude_fraction': magnitude, 'importance': importance,
        'primary_metric': surprise['metric'], 'source_surprise_fraction': value,
        'evidence_quality': 1.0 if immutable else 0.7,
        'immutable_consensus_snapshot': immutable,
        'return_forecast_available': False, 'trade_eligible': False,
        'trade_blockers': ['IMPACT_MODEL_NOT_CALIBRATED', 'RESIDUAL_DISTRIBUTION_NOT_CALIBRATED',
                           'HISTORICAL_QUOTES_UNAVAILABLE'],
        'scoring_version': 'deterministic-surprise-v1',
    }


def score_events(surprises):
    """Emit one deterministic score per event, preferring revenue as primary."""
    grouped = {}
    for surprise in surprises:
        grouped.setdefault(surprise['event_id'], []).append(surprise)
    scores = []
    for event_id in sorted(grouped):
        items = grouped[event_id]
        primary = next((item for item in items if item['metric'] == 'revenue'), items[0])
        score = score_surprise(primary)
        score['component_surprises'] = [
            {'metric': item['metric'], 'surprise_fraction': float(item['surprise_fraction'])}
            for item in sorted(items, key=lambda item: item['metric'])]
        scores.append(score)
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actuals-report', type=Path, required=True)
    parser.add_argument('--output', type=Path,
                        help='JSONL destination; defaults to data/event_scores.jsonl')
    args = parser.parse_args()
    actuals = json.loads(args.actuals_report.read_text(encoding='utf-8'))
    scores = score_events(actuals.get('surprises', []))
    root = Path(__file__).resolve().parents[1]
    output = args.output or (root / 'data' / 'event_scores.jsonl')
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(''.join(json.dumps(score, sort_keys=True) + '\n' for score in scores), encoding='utf-8')
    report = {'created_at':datetime.now(timezone.utc).isoformat(), 'synthetic':False,
              'score_count':len(scores), 'trade_eligible_count':sum(s['trade_eligible'] for s in scores),
              'scores':scores, 'output':str(output)}
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    report_path = reports / ('event-scoring-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report':str(report_path), 'scores':scores}, indent=2))


if __name__ == '__main__': main()
