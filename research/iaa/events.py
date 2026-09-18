"""Point-in-time earnings-event ingestion with explicit synthetic provenance."""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SYMBOL_MAP = {
    'AAPL':'RAAPLUSDT', 'NVDA':'RNVDAUSDT', 'TSLA':'RTSLAUSDT',
    'MSFT':'RMSFTUSDT', 'META':'RMETAUSDT', 'AMZN':'RAMZNUSDT',
    'GOOGL':'RGOOGLUSDT', 'AMD':'RAMDUSDT', 'AVGO':'RAVGOUSDT',
    'NFLX':'RNFLXUSDT', 'COIN':'RCOINUSDT', 'PLTR':'RPLTRUSDT',
    'HOOD':'RHOODUSDT', 'ORCL':'RORCLUSDT', 'ADBE':'RADBEUSDT',
    'CRM':'RCRMUSDT', 'INTC':'RINTCUSDT',
    'QCOM':'RQCOMUSDT', 'IBM':'RIBMUSDT', 'CSCO':'RCSCOUSDT',
    'WMT':'RWMTUSDT', 'JPM':'RJPMUSDT', 'V':'RVUSDT', 'MA':'RMAUSDT',
    'XOM':'RXOMUSDT', 'JNJ':'RJNJUSDT', 'LLY':'RLLYUSDT',
    'MCD':'RMCDUSDT', 'DIS':'RDISUSDT', 'UBER':'RUBERUSDT',
    'PYPL':'RPYPLUSDT', 'BA':'RBAUSDT', 'GE':'RGEUSDT', 'HD':'RHDUSDT',
}
REQUIRED = ('event_id', 'source_url', 'raw_text_hash', 'published_at', 'first_received_at',
            'structured_at', 'model_ready_at', 'event_type', 'underlying_ticker',
            'token_symbol', 'source_timezone', 'model_version', 'extraction_version')
HASH_RE = re.compile(r'^[0-9a-f]{64}$')


def utc_timestamp(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} is required')
    parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError(f'{field} must include a timezone')
    return parsed.astimezone(timezone.utc)


def normalize_event(raw, synthetic=False):
    if not isinstance(raw, dict):
        raise ValueError('Event must be an object')
    missing = [field for field in REQUIRED if raw.get(field) in (None, '')]
    if missing:
        raise ValueError('Missing required fields: ' + ', '.join(missing))
    event = {field: str(raw[field]).strip() for field in REQUIRED}
    ticker = event['underlying_ticker'].upper()
    token = event['token_symbol'].upper()
    if ticker not in SYMBOL_MAP or token != SYMBOL_MAP[ticker]:
        raise ValueError('Ambiguous or unsupported ticker mapping')
    if event['event_type'] not in ('earnings_release', 'earnings_filing'):
        raise ValueError('Initial event family must be earnings_release or earnings_filing')
    parts = urlsplit(event['source_url'])
    if parts.scheme != 'https' or not parts.hostname:
        raise ValueError('source_url must be an absolute HTTPS URL')
    event['raw_text_hash'] = event['raw_text_hash'].lower()
    if not HASH_RE.fullmatch(event['raw_text_hash']):
        raise ValueError('raw_text_hash must be a SHA-256 hex digest')
    times = {field: utc_timestamp(event[field], field) for field in
             ('published_at', 'first_received_at', 'structured_at', 'model_ready_at')}
    if not (times['published_at'] <= times['first_received_at'] <=
            times['structured_at'] <= times['model_ready_at']):
        raise ValueError('Event availability timestamps are out of order')
    for field, value in times.items():
        event[field] = value.isoformat()
    event['underlying_ticker'], event['token_symbol'] = ticker, token
    event['synthetic'] = bool(synthetic)
    event['available_at'] = event['model_ready_at']
    for optional in ('correction_of', 'fiscal_period', 'currency', 'actual_eps',
                     'consensus_eps', 'surprise_fraction', 'accession_number', 'cik',
                     'filing_form', 'filing_items', 'timestamp_semantics',
                     'issuer_release_time_validated', 'availability_assumption',
                     'earnings_exhibits', 'publication_evidence', 'sec_filing_evidence'):
        if raw.get(optional) not in (None, ''):
            event[optional] = raw[optional]
    if 'surprise_fraction' in event:
        event['surprise_fraction'] = float(event['surprise_fraction'])
    return event


def ingest(records, synthetic=False):
    events, seen = [], set()
    for index, raw in enumerate(records, 1):
        event = normalize_event(raw, synthetic=synthetic)
        if event['event_id'] in seen:
            raise ValueError(f'Duplicate event_id at record {index}: {event["event_id"]}')
        if event.get('correction_of') == event['event_id']:
            raise ValueError('A correction cannot reference itself')
        seen.add(event['event_id'])
        events.append(event)
    events.sort(key=lambda event: (event['published_at'], event['event_id']))
    return events


def fixture_records():
    records = []
    for ticker, published in [('AAPL', '2026-08-20T20:05:00Z'),
                              ('NVDA', '2026-08-27T20:05:00Z'),
                              ('TSLA', '2026-09-03T20:05:00Z')]:
        body = f'SYNTHETIC {ticker} earnings fixture v1'
        base = published[:-1]
        published_dt = utc_timestamp(published, 'published_at')
        def later(seconds):
            return datetime.fromtimestamp(published_dt.timestamp() + seconds, timezone.utc).isoformat()
        records.append({
            'event_id': f'fixture-{ticker.lower()}-2026q3-v1',
            'source_url': f'https://example.invalid/{ticker.lower()}/synthetic-earnings',
            'raw_text_hash': hashlib.sha256(body.encode()).hexdigest(),
            'published_at': base + '+00:00', 'first_received_at': later(2),
            'structured_at': later(8), 'model_ready_at': later(15),
            'event_type': 'earnings_release', 'underlying_ticker': ticker,
            'token_symbol': SYMBOL_MAP[ticker], 'source_timezone': 'America/New_York',
            'model_version': 'fixture-model-v1', 'extraction_version': 'fixture-extractor-v1',
        })
    return records


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def write_jsonl_atomic(path, events):
    temporary = path.with_suffix(path.suffix + '.tmp')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(''.join(json.dumps(event, sort_keys=True) + '\n' for event in events),
                         encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['fixture', 'csv'], default='fixture')
    parser.add_argument('--input', type=Path, help='CSV input for --provider csv')
    args = parser.parse_args()
    if args.provider == 'csv' and not args.input:
        parser.error('--input is required for --provider csv')
    records = fixture_records() if args.provider == 'fixture' else read_csv(args.input)
    synthetic = args.provider == 'fixture'
    events = ingest(records, synthetic=synthetic)
    root = Path(__file__).resolve().parents[1]
    output = root / 'data' / ('events_fixture.jsonl' if synthetic else 'events.jsonl')
    write_jsonl_atomic(output, events)
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'provider': args.provider,
              'synthetic': synthetic, 'real_event_response_received': False,
              'event_count': len(events), 'output': str(output),
              'earliest_published_at': events[0]['published_at'] if events else None,
              'latest_published_at': events[-1]['published_at'] if events else None}
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    report_path = reports / ('event-ingestion-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(report_path), **report}, indent=2))


if __name__ == '__main__':
    main()
