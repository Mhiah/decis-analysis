"""Collect bounded real Bitget candle windows around supplied events."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .collector import INTERVAL_MS, collect_symbol
from .events import ingest
from .providers import BitgetProvider


def event_window(event, before_minutes=15, after_minutes=180):
    if before_minutes < 1 or after_minutes < 1:
        raise ValueError('Event window bounds must be positive')
    published = datetime.fromisoformat(event['published_at'].replace('Z', '+00:00')).astimezone(timezone.utc)
    start = int((published - timedelta(minutes=before_minutes)).timestamp() * 1000)
    end = int((published + timedelta(minutes=after_minutes)).timestamp() * 1000)
    return start // INTERVAL_MS * INTERVAL_MS, (end // INTERVAL_MS + 1) * INTERVAL_MS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--dns-fallback', action='store_true')
    parser.add_argument('--before-minutes', type=int, default=15)
    parser.add_argument('--after-minutes', type=int, default=180)
    args = parser.parse_args()
    events = ingest([json.loads(line) for line in args.events.read_text(encoding='utf-8').splitlines()
                     if line], synthetic=False)
    provider = BitgetProvider(dns_fallback=args.dns_fallback)
    root = Path(__file__).resolve().parents[1]
    results = []
    for event in events:
        start_ms, end_ms = event_window(event, args.before_minutes, args.after_minutes)
        collection = collect_symbol(provider, event['token_symbol'], start_ms, end_ms,
                                    root / 'data' / f'{event["token_symbol"]}_1m.csv',
                                    preserve_outside_window=True)
        results.append({'event_id':event['event_id'], 'ticker':event['underlying_ticker'],
                        'token_symbol':event['token_symbol'], **collection})
    report = {
        'created_at':datetime.now(timezone.utc).isoformat(), 'provider':provider.name,
        'synthetic':provider.synthetic, 'event_count':len(events),
        'real_bitget_response_received':any(
            any(request.get('api_response_received') for request in item['requests']) for item in results),
        'events_with_candles':sum(item['rows'] > 0 for item in results),
        'events_without_candles':sum(item['rows'] == 0 for item in results),
        'before_minutes':args.before_minutes, 'after_minutes':args.after_minutes,
        'results':results,
    }
    folder = root / 'reports'; folder.mkdir(exist_ok=True)
    output = folder / ('event-market-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report':str(output), 'provider':report['provider'],
                      'synthetic':report['synthetic'],
                      'real_bitget_response_received':report['real_bitget_response_received'],
                      'event_count':report['event_count'],
                      'events_with_candles':report['events_with_candles'],
                      'events_without_candles':report['events_without_candles'],
                      'results':[{'ticker':item['ticker'], 'symbol':item['token_symbol'],
                                  'rows':item['rows'], 'requests':item['request_count']}
                                 for item in results]}, indent=2))


if __name__ == '__main__': main()
