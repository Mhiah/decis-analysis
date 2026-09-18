"""Anti-look-ahead alignment of point-in-time events to one-minute candles."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

MINUTE_MS = 60_000


def timestamp_ms(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).timestamp() * 1000)


def load_candles(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return [{**row, 'timestamp_ms': int(row['timestamp_ms'])} for row in csv.DictReader(handle)]


def load_events(path):
    with Path(path).open(encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def align_event(event, candles, max_baseline_age_minutes=5):
    if event.get('synthetic') not in (True, False):
        raise ValueError('Event provenance is required')
    published = timestamp_ms(event['published_at'])
    available = timestamp_ms(event['available_at'])
    if available < published:
        raise ValueError('Event cannot be available before publication')
    ordered = sorted(candles, key=lambda row: row['timestamp_ms'])
    # A candle stamped T is available only at T+1 minute.
    baseline_candidates = [row for row in ordered if row['timestamp_ms'] + MINUTE_MS <= published]
    baseline = baseline_candidates[-1] if baseline_candidates else None
    if baseline and published - (baseline['timestamp_ms'] + MINUTE_MS) > max_baseline_age_minutes * MINUTE_MS:
        baseline = None
    observations = [row for row in ordered if row['timestamp_ms'] + MINUTE_MS >= available]
    first_observation = observations[0] if observations else None
    return {
        'event_id': event['event_id'], 'token_symbol': event['token_symbol'],
        'synthetic_event': event['synthetic'], 'published_at': event['published_at'],
        'available_at': event['available_at'], 'baseline': baseline,
        'first_observation': first_observation,
        'baseline_valid': baseline is not None,
        'decision_delay_seconds': (available - published) / 1000,
        'candle_availability_rule': 'timestamp_ms + 60000',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--market-manifest', type=Path, required=True)
    parser.add_argument('--max-baseline-age-minutes', type=int, default=5)
    args = parser.parse_args()
    if args.max_baseline_age_minutes < 0:
        parser.error('--max-baseline-age-minutes must be non-negative')
    manifest = json.loads(args.market_manifest.read_text(encoding='utf-8'))
    if manifest.get('synthetic') is not False or manifest.get('provider') != 'bitget':
        raise ValueError('Alignment requires a real Bitget collection manifest')
    root = Path(__file__).resolve().parents[1]
    events = load_events(args.events)
    results = []
    for event in events:
        candles = load_candles(root / 'data' / f'{event["token_symbol"]}_1m.csv')
        results.append(align_event(event, candles, args.max_baseline_age_minutes))
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'market_provider': 'bitget', 'market_data_synthetic': False,
        'market_manifest': str(args.market_manifest),
        'event_source_synthetic': any(event.get('synthetic') for event in events),
        'real_event_validation_successful': bool(events) and not any(event.get('synthetic') for event in events),
        'aligned_events': len(results),
        'baseline_valid_events': sum(result['baseline_valid'] for result in results),
        'results': results,
    }
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    output = reports / ('event-alignment-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), 'market_data_synthetic': False,
                      'event_source_synthetic': report['event_source_synthetic'],
                      'real_event_validation_successful': report['real_event_validation_successful'],
                      'aligned_events': report['aligned_events'],
                      'baseline_valid_events': report['baseline_valid_events']}, indent=2))


if __name__ == '__main__':
    main()
