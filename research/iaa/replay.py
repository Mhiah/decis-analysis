"""Chronological candle replay for a verified event; no execution claims."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .alignment import MINUTE_MS, align_event, load_candles, load_events, timestamp_ms


def replay_event(event, candles, score, horizon_minutes=120, max_baseline_age_minutes=5):
    if horizon_minutes <= 0:
        raise ValueError('Replay horizon must be positive')
    aligned = align_event(event, candles, max_baseline_age_minutes)
    if not aligned['baseline_valid']:
        raise ValueError('A fresh pre-event baseline is required')
    published = timestamp_ms(event['published_at'])
    available = timestamp_ms(event['available_at'])
    horizon = published + horizon_minutes * MINUTE_MS
    baseline = float(aligned['baseline']['close'])
    observations = []
    for candle in sorted(candles, key=lambda row: row['timestamp_ms']):
        candle_available = candle['timestamp_ms'] + MINUTE_MS
        if candle_available < available or candle_available > horizon:
            continue
        close = float(candle['close'])
        observations.append({
            'candle_timestamp_ms': candle['timestamp_ms'],
            'available_at_ms': candle_available,
            'elapsed_minutes': (candle_available - published) / MINUTE_MS,
            'close': close, 'observed_return': close / baseline - 1,
            'base_volume': candle.get('base_volume', ''),
        })
    if not observations:
        raise ValueError('No observations are available inside the event horizon')
    first, last = observations[0], observations[-1]
    expected_slots = int((horizon - max(available, first['available_at_ms'])) // MINUTE_MS) + 1
    return {
        'event_id':event['event_id'], 'token_symbol':event['token_symbol'],
        'event_direction':score['direction'], 'event_magnitude_fraction':score['magnitude_fraction'],
        'published_at':event['published_at'], 'decision_available_at':event['available_at'],
        'horizon_minutes':horizon_minutes, 'baseline':aligned['baseline'],
        'baseline_price_kind':'candle_close_proxy', 'observations':observations,
        'observation_count':len(observations), 'expected_slots_from_first':expected_slots,
        'missing_slots_from_first':max(0, expected_slots-len(observations)),
        'first_observed_return':first['observed_return'], 'horizon_observed_return':last['observed_return'],
        'fixed_hold_close_to_close_return':last['close']/first['close']-1,
        'trade_generated':False, 'execution_validated':False,
        'trade_blockers':score['trade_blockers'],
        'limitations':['CANDLE_CLOSE_PROXY_NOT_MIDPOINT', 'NO_HISTORICAL_BID_ASK',
                       'NO_CALIBRATED_IMPACT_CURVE', 'SMALL_EVENT_SAMPLE'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--scores', type=Path, required=True)
    parser.add_argument('--horizon-minutes', type=int, default=120)
    args = parser.parse_args()
    events = load_events(args.events)
    scores = [json.loads(line) for line in args.scores.read_text(encoding='utf-8').splitlines() if line]
    score_by_id = {score['event_id']:score for score in scores}
    root = Path(__file__).resolve().parents[1]
    replays = []
    for event in events:
        if event['event_id'] not in score_by_id:
            continue
        candles = load_candles(root / 'data' / f'{event["token_symbol"]}_1m.csv')
        replays.append(replay_event(event, candles, score_by_id[event['event_id']], args.horizon_minutes))
    report = {'created_at':datetime.now(timezone.utc).isoformat(), 'synthetic':False,
              'replay_count':len(replays), 'trade_count':sum(r['trade_generated'] for r in replays),
              'execution_validated':False, 'replays':replays}
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    output = reports / ('replay-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report':str(output), 'replay_count':len(replays), 'trade_count':0,
                      'execution_validated':False,
                      'summaries':[{key:r[key] for key in ('event_id','observation_count','missing_slots_from_first',
                                                          'first_observed_return','horizon_observed_return',
                                                          'fixed_hold_close_to_close_return')} for r in replays]}, indent=2))


if __name__ == '__main__': main()
