"""Validate point-in-time consensus records and calculate bounded surprises."""
import argparse
import json
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit


REQUIRED = ('consensus_id', 'event_id', 'source_url', 'source_name', 'metric',
            'estimate', 'unit', 'fiscal_period', 'available_at', 'event_published_at',
            'retrieved_at', 'retrieval_surface', 'immutable_snapshot_validated')
METRICS = {'revenue', 'adjusted_eps'}


def utc(value, field):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError(f'{field} must include a timezone')
    return parsed.astimezone(timezone.utc)


def normalize(record):
    missing = [field for field in REQUIRED if record.get(field) in (None, '')]
    if missing:
        raise ValueError('Missing consensus fields: ' + ', '.join(missing))
    item = dict(record)
    if item['metric'] not in METRICS:
        raise ValueError('Unsupported consensus metric')
    estimate = float(item['estimate'])
    if not isfinite(estimate) or estimate <= 0:
        raise ValueError('Consensus estimate must be positive and finite')
    parts = urlsplit(item['source_url'])
    if parts.scheme != 'https' or not parts.hostname:
        raise ValueError('Consensus source must be an absolute HTTPS URL')
    available = utc(item['available_at'], 'available_at')
    published = utc(item['event_published_at'], 'event_published_at')
    retrieved = utc(item['retrieved_at'], 'retrieved_at')
    if available >= published:
        raise ValueError('Consensus must be available before the event')
    item.update(estimate=estimate, available_at=available.isoformat(),
                event_published_at=published.isoformat(), retrieved_at=retrieved.isoformat(),
                immutable_snapshot_validated=bool(item['immutable_snapshot_validated']))
    item['point_in_time_usable'] = True
    item['evidence_limit'] = (None if item['immutable_snapshot_validated'] else
                              'Dated pre-release publication; immutable vendor snapshot unavailable')
    return item


def validate(records):
    output, ids, keys = [], set(), set()
    for record in records:
        item = normalize(record)
        key = (item['event_id'], item['metric'])
        if item['consensus_id'] in ids or key in keys:
            raise ValueError('Duplicate consensus identity or event metric')
        ids.add(item['consensus_id']); keys.add(key); output.append(item)
    return sorted(output, key=lambda item: (item['event_published_at'], item['metric']))


def calculate_surprise(estimate, actual):
    estimate, actual = float(estimate), float(actual)
    if not all(isfinite(value) for value in (estimate, actual)) or estimate <= 0:
        raise ValueError('Invalid surprise inputs')
    return (actual - estimate) / abs(estimate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path,
                        help='JSONL destination; defaults to data/consensus.jsonl')
    args = parser.parse_args()
    raw = json.loads(args.input.read_text(encoding='utf-8'))
    records = validate(raw if isinstance(raw, list) else [raw])
    root = Path(__file__).resolve().parents[1]
    output = args.output or (root / 'data' / 'consensus.jsonl')
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(''.join(json.dumps(record, sort_keys=True) + '\n' for record in records),
                      encoding='utf-8')
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'records': len(records),
        'point_in_time_usable_records': sum(record['point_in_time_usable'] for record in records),
        'immutable_snapshot_validated_records': sum(record['immutable_snapshot_validated'] for record in records),
        'source_response_received_records': sum(bool(record.get('source_response_received')) for record in records),
        'local_source_response_received': False,
        'retrieval_surfaces': sorted({record['retrieval_surface'] for record in records}),
        'output': str(output),
    }
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    report_path = reports / ('consensus-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(report_path), **report}, indent=2))


if __name__ == '__main__': main()
