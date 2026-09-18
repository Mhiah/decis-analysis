"""Resumable one-minute rToken candle collector with coverage diagnostics."""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .providers import BitgetProvider, MockProvider

INTERVAL_MS = 60_000
RETRYABLE_ERRORS = {'DNS', 'CONNECTION', 'TIMEOUT', 'TLS', 'NETWORK', 'HTTP'}
DEFAULT_SYMBOLS = ('RAAPLUSDT', 'RNVDAUSDT', 'RTSLAUSDT')
FIELDS = ('timestamp_ms', 'timestamp_utc', 'session', 'open', 'high', 'low',
          'close', 'base_volume', 'quote_turnover')


def parse_utc(value):
    if value is None:
        return datetime.now(timezone.utc)
    text = value.strip().replace('Z', '+00:00')
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError('Timestamps must include a timezone, for example 2026-09-01T00:00:00Z')
    return parsed.astimezone(timezone.utc)


def floor_minute_ms(value):
    return int(value.timestamp() * 1000) // INTERVAL_MS * INTERVAL_MS


def _nth_sunday(year, month, occurrence):
    first = datetime(year, month, 1, tzinfo=timezone.utc)
    day = 1 + (6 - first.weekday()) % 7 + 7 * (occurrence - 1)
    return day


def eastern_time(timestamp_ms):
    """US Eastern time using post-2007 DST rules, valid for this research era."""
    utc = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
    # DST begins 02:00 EST (07:00 UTC), second Sunday in March, and ends
    # 02:00 EDT (06:00 UTC), first Sunday in November.
    start = datetime(utc.year, 3, _nth_sunday(utc.year, 3, 2), 7, tzinfo=timezone.utc)
    end = datetime(utc.year, 11, _nth_sunday(utc.year, 11, 1), 6, tzinfo=timezone.utc)
    offset = timedelta(hours=-4 if start <= utc < end else -5)
    return utc + offset


def session_label(timestamp_ms):
    local = eastern_time(timestamp_ms)
    minutes = local.hour * 60 + local.minute
    if local.weekday() == 5 or (local.weekday() == 6 and minutes < 1200) or (local.weekday() == 4 and minutes >= 1200):
        return 'weekend'
    if 240 <= minutes < 570:
        return 'pre_market'
    if 570 <= minutes < 960:
        return 'cash'
    if 960 <= minutes < 1200:
        return 'after_hours'
    return 'overnight'


def normalize_candle(raw):
    if not isinstance(raw, list) or len(raw) < 5:
        raise ValueError('Malformed candle record')
    timestamp = int(raw[0])
    if timestamp % INTERVAL_MS:
        raise ValueError(f'Candle timestamp is not minute-aligned: {timestamp}')
    numeric = []
    for index in range(1, 7):
        value = raw[index] if index < len(raw) else ''
        if value not in ('', None):
            float(value)
        numeric.append('' if value is None else str(value))
    return {
        'timestamp_ms': timestamp,
        'timestamp_utc': datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat(),
        'session': session_label(timestamp),
        'open': numeric[0], 'high': numeric[1], 'low': numeric[2], 'close': numeric[3],
        'base_volume': numeric[4], 'quote_turnover': numeric[5],
    }


def load_existing(path):
    if not path.exists():
        return {}
    rows = {}
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            normalized = {key: row.get(key, '') for key in FIELDS}
            normalized['timestamp_ms'] = int(normalized['timestamp_ms'])
            rows[normalized['timestamp_ms']] = normalized
    return rows


def write_csv_atomic(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows[key] for key in sorted(rows))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def detect_gaps(rows):
    stamps = sorted(rows)
    gaps = []
    for left, right in zip(stamps, stamps[1:]):
        if right - left <= INTERVAL_MS:
            continue
        missing = (right - left) // INTERVAL_MS - 1
        cursor = left + INTERVAL_MS
        contains_weekend = False
        # At most seven daily probes are sufficient to detect a weekend in any span.
        for _ in range(min(7, missing)):
            if session_label(cursor) == 'weekend':
                contains_weekend = True
                break
            cursor += max(INTERVAL_MS, (right - left) // 7)
        gaps.append({'after_timestamp_ms': left, 'before_timestamp_ms': right,
                     'after_utc': rows[left]['timestamp_utc'], 'before_utc': rows[right]['timestamp_utc'],
                     'missing_intervals': missing, 'after_session': rows[left]['session'],
                     'before_session': rows[right]['session'],
                     'classification': 'spans_weekend' if contains_weekend else 'unclassified'})
    return gaps


def collect_symbol(provider, symbol, start_ms, end_ms, path, pause_seconds=0.06,
                   max_attempts=4, retry_base_seconds=0.5, preserve_outside_window=False):
    rows = load_existing(path)
    existing_before = len(rows)
    cursor = end_ms
    requests = []
    duplicate_records_seen = 0
    seen_boundaries = set()
    while cursor > start_ms:
        if cursor in seen_boundaries:
            raise RuntimeError(f'Pagination stalled at {cursor}')
        seen_boundaries.add(cursor)
        for attempt in range(1, max_attempts + 1):
            probe = provider.candles(symbol, cursor, 100)
            request_record = {key: probe.get(key) for key in
                              ('ok', 'provider', 'synthetic', 'url', 'retrieved_at', 'http_status',
                               'api_response_received', 'error_kind', 'error', 'transport') if key in probe}
            request_record['attempt'] = attempt
            requests.append(request_record)
            if probe.get('ok') or probe.get('error_kind') not in RETRYABLE_ERRORS or attempt == max_attempts:
                break
            time.sleep(retry_base_seconds * (2 ** (attempt - 1)))
        if not probe.get('ok'):
            raise RuntimeError(f'{symbol} request failed: {probe.get("error_kind")}: {probe.get("error")}')
        batch = probe.get('body', {}).get('data', [])
        if not batch:
            break
        normalized = [normalize_candle(item) for item in batch]
        duplicate_records_seen += len(normalized) - len({row['timestamp_ms'] for row in normalized})
        earliest = min(row['timestamp_ms'] for row in normalized)
        for row in normalized:
            if start_ms <= row['timestamp_ms'] < end_ms:
                rows[row['timestamp_ms']] = row
        if earliest >= cursor:
            raise RuntimeError(f'Pagination did not move backward: {earliest} >= {cursor}')
        cursor = earliest
        if earliest <= start_ms:
            break
        if not provider.synthetic:
            time.sleep(pause_seconds)
    window_rows = {stamp: row for stamp, row in rows.items() if start_ms <= stamp < end_ms}
    if not preserve_outside_window:
        rows = window_rows
    for stamp, row in rows.items():
        row['session'] = session_label(stamp)
    write_csv_atomic(path, rows)
    gaps = detect_gaps(window_rows)
    stamps = sorted(window_rows)
    return {
        'symbol': symbol, 'provider': provider.name, 'synthetic': provider.synthetic,
        'requested_start_ms': start_ms, 'requested_end_ms': end_ms,
        'requested_start_utc': datetime.fromtimestamp(start_ms/1000, timezone.utc).isoformat(),
        'requested_end_utc': datetime.fromtimestamp(end_ms/1000, timezone.utc).isoformat(),
        'rows': len(window_rows), 'stored_rows_total': len(rows),
        'preserved_outside_window': preserve_outside_window,
        'existing_rows_before': existing_before,
        'first_timestamp_ms': stamps[0] if stamps else None,
        'last_timestamp_ms': stamps[-1] if stamps else None,
        'duplicate_records_seen': duplicate_records_seen, 'duplicate_timestamps_in_output': 0,
        'leading_uncovered_intervals': max(0, ((stamps[0] - start_ms) // INTERVAL_MS) if stamps else ((end_ms-start_ms)//INTERVAL_MS)),
        'trailing_uncovered_intervals': max(0, ((end_ms - INTERVAL_MS - stamps[-1]) // INTERVAL_MS) if stamps else 0),
        'request_count': len(requests),
        'missing_volume_rows': sum(row['base_volume'] == '' or row['quote_turnover'] == '' for row in window_rows.values()),
        'session_counts': {label: sum(row['session'] == label for row in window_rows.values())
                           for label in ('pre_market', 'cash', 'after_hours', 'overnight', 'weekend')},
        'gap_count': len(gaps), 'missing_intervals_total': sum(g['missing_intervals'] for g in gaps),
        'gaps': gaps, 'requests': requests, 'csv': str(path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['bitget', 'mock'], default='bitget')
    parser.add_argument('--dns-fallback', action='store_true')
    parser.add_argument('--symbols', nargs='+', default=list(DEFAULT_SYMBOLS))
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--start', help='ISO-8601 UTC start; overrides --days')
    parser.add_argument('--end', help='ISO-8601 UTC end; defaults to current completed minute')
    parser.add_argument('--merge-windows', action='store_true',
                        help='preserve rows outside the requested window in existing CSV files')
    args = parser.parse_args()
    if args.days <= 0:
        parser.error('--days must be positive')
    end_dt = parse_utc(args.end)
    start_dt = parse_utc(args.start) if args.start else end_dt - timedelta(days=args.days)
    start_ms, end_ms = floor_minute_ms(start_dt), floor_minute_ms(end_dt)
    if start_ms >= end_ms:
        parser.error('start must be before end')
    provider = MockProvider() if args.provider == 'mock' else BitgetProvider(dns_fallback=args.dns_fallback)
    root = Path(__file__).resolve().parents[1]
    results = []
    for symbol in args.symbols:
        clean = symbol.upper()
        if clean not in DEFAULT_SYMBOLS:
            parser.error(f'Unsupported initial-universe symbol: {symbol}')
        results.append(collect_symbol(provider, clean, start_ms, end_ms,
                                      root / 'data' / f'{clean}_1m.csv',
                                      preserve_outside_window=args.merge_windows))
    manifest = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'provider': provider.name,
        'synthetic': provider.synthetic, 'historical_coverage_validated': False,
        'session_labels': 'America/New_York weekday clock only; holidays and exchange pauses are not classified.',
        'merge_windows': args.merge_windows,
        'symbols': results,
    }
    folder = root / 'reports'
    folder.mkdir(exist_ok=True)
    output = folder / ('collection-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    output.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), 'provider': provider.name,
                      'synthetic': provider.synthetic,
                      'symbols': [{key: result[key] for key in ('symbol','rows','request_count','gap_count','missing_intervals_total','missing_volume_rows')} for result in results]}, indent=2))


if __name__ == '__main__':
    main()
