"""Read-only SEC EDGAR Item 2.02 event provider for the initial IAA universe."""
import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .events import SYMBOL_MAP, ingest, write_jsonl_atomic

CORE_CIKS = {'AAPL': '0000320193', 'NVDA': '0001045810', 'TSLA': '0001318605'}
EXPANDED_CIKS = {
    'MSFT':'0000789019', 'META':'0001326801', 'AMZN':'0001018724',
    'GOOGL':'0001652044', 'AMD':'0000002488', 'AVGO':'0001730168',
    'NFLX':'0001065280', 'COIN':'0001679788', 'PLTR':'0001321655',
    'HOOD':'0001783879', 'ORCL':'0001341439', 'ADBE':'0000796343',
    'CRM':'0001108524', 'INTC':'0000050863',
}
EXTENSION_CIKS = {
    'QCOM':'0000804328', 'IBM':'0000051143', 'CSCO':'0000858877',
    'WMT':'0000104169', 'JPM':'0000019617', 'V':'0001403161',
    'MA':'0001141391', 'XOM':'0000034088', 'JNJ':'0000200406',
    'LLY':'0000059478', 'MCD':'0000063908', 'DIS':'0001744489',
    'UBER':'0001543151', 'PYPL':'0001633917', 'BA':'0000012927',
    'GE':'0000040545', 'HD':'0000354950',
}
CIKS = CORE_CIKS
BASE = 'https://data.sec.gov/submissions/CIK{}.json'


def parse_acceptance(value):
    text = str(value).strip()
    if text.endswith('Z') or '+' in text[10:]:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    else:
        # EDGAR submissions JSON acceptanceDateTime is an Eastern local timestamp.
        parsed = datetime.strptime(text, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        raise ValueError('Ambiguous SEC acceptanceDateTime without a UTC offset')
    return parsed.astimezone(timezone.utc)


def filing_rows(payload):
    recent = payload.get('filings', {}).get('recent', {})
    if not isinstance(recent, dict):
        raise ValueError('Missing filings.recent object')
    lengths = {len(value) for value in recent.values() if isinstance(value, list)}
    if not lengths:
        return []
    if len(lengths) != 1:
        raise ValueError('SEC filing columns have inconsistent lengths')
    keys = [key for key, value in recent.items() if isinstance(value, list)]
    return [{key: recent[key][index] for key in keys} for index in range(next(iter(lengths)))]


def is_item_202(row):
    form = str(row.get('form', '')).upper()
    items = {item.strip() for item in str(row.get('items', '')).split(',')}
    return form in ('8-K', '8-K/A') and '2.02' in items


def archive_url(cik, accession, document):
    return (f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/'
            f'{accession.replace("-", "")}/{document}')


def exhibit_documents(submission_bytes):
    text = submission_bytes.decode('latin-1', errors='replace')
    exhibits = []
    for block in re.findall(r'<DOCUMENT>(.*?)</DOCUMENT>', text, flags=re.I | re.S):
        def field(name):
            match = re.search(rf'<{name}>\s*([^\r\n<]+)', block, flags=re.I)
            return match.group(1).strip() if match else ''
        document_type, filename = field('TYPE').upper(), field('FILENAME')
        # SEC sometimes labels the earnings release as TYPE 99 or EX-99 rather than EX-99.1.
        if (document_type in ('99', 'EX-99', 'EX-99.1') or document_type.startswith('EX-99.')) and filename:
            normalized_type = 'EX-99.1' if document_type in ('99', 'EX-99') else document_type
            exhibits.append({'type': normalized_type, 'filename': filename,
                             'description': field('DESCRIPTION')})
    exhibits.sort(key=lambda item: (item['type'] != 'EX-99.1', item['type'], item['filename']))
    return exhibits


def make_event(ticker, cik, row, document_bytes, retrieved_at,
               receipt_latency_seconds=180, processing_seconds=15):
    accepted = parse_acceptance(row['acceptanceDateTime'])
    received = accepted + timedelta(seconds=receipt_latency_seconds)
    structured = received + timedelta(seconds=processing_seconds)
    accession = str(row['accessionNumber'])
    form = str(row['form']).upper()
    return {
        'event_id': f'sec-{accession}', 'source_url': archive_url(cik, accession, row['primaryDocument']),
        'raw_text_hash': hashlib.sha256(document_bytes).hexdigest(),
        'published_at': accepted.isoformat(), 'first_received_at': received.isoformat(),
        'structured_at': structured.isoformat(), 'model_ready_at': structured.isoformat(),
        'event_type': 'earnings_filing', 'underlying_ticker': ticker,
        'token_symbol': SYMBOL_MAP[ticker], 'source_timezone': 'SEC acceptance timestamp',
        'model_version': 'no-impact-model', 'extraction_version': 'sec-item-2.02-v1',
        'accession_number': accession, 'cik': cik, 'filing_form': form,
        'filing_items': row.get('items', ''), 'timestamp_semantics': 'edgar_acceptance',
        'issuer_release_time_validated': False,
        'availability_assumption': {
            'historical_receipt_latency_seconds': receipt_latency_seconds,
            'processing_seconds': processing_seconds,
            'actual_retrieved_at': retrieved_at,
        },
    }


class SECProvider:
    name = 'sec_edgar'
    synthetic = False

    def __init__(self, user_agent, opener=None, timeout=20, pause_seconds=0.12):
        if not user_agent or '@' not in user_agent:
            raise ValueError('SEC user agent must identify the project and a contact email')
        self.user_agent = user_agent
        self.opener = opener or urlopen
        self.timeout = timeout
        self.pause_seconds = pause_seconds

    def get(self, url):
        request = Request(url, headers={'User-Agent': self.user_agent,
                                        'Accept-Encoding': 'identity', 'Accept': 'application/json,text/html'})
        with self.opener(request, timeout=self.timeout) as response:
            return response.read(), getattr(response, 'status', 200)

    def collect(self, start, end, receipt_latency_seconds=180, processing_seconds=15, ciks=None):
        events, requests = [], []
        for ticker, cik in (ciks or CIKS).items():
            url = BASE.format(cik)
            try:
                body, status = self.get(url)
                payload = json.loads(body)
                returned_cik = str(payload.get('cik', '')).zfill(10)
                if returned_cik != cik:
                    raise ValueError(f'SEC payload CIK mismatch: expected {cik}, received {returned_cik}')
                requests.append({'url': url, 'http_status': status, 'response_received': True, 'ok': True})
                rows = [row for row in filing_rows(payload) if is_item_202(row)]
                for row in rows:
                    accepted = parse_acceptance(row['acceptanceDateTime'])
                    if not start <= accepted < end:
                        continue
                    doc_url = archive_url(cik, row['accessionNumber'], row['primaryDocument'])
                    document, doc_status = self.get(doc_url)
                    retrieved = datetime.now(timezone.utc).isoformat()
                    requests.append({'url': doc_url, 'http_status': doc_status,
                                     'response_received': True, 'ok': True})
                    accession = row['accessionNumber']
                    submission_url = archive_url(cik, accession, f'{accession}.txt')
                    submission, submission_status = self.get(submission_url)
                    requests.append({'url': submission_url, 'http_status': submission_status,
                                     'response_received': True, 'ok': True})
                    exhibits = []
                    for candidate in exhibit_documents(submission):
                        exhibit_url = archive_url(cik, accession, candidate['filename'])
                        exhibit_body, exhibit_status = self.get(exhibit_url)
                        requests.append({'url': exhibit_url, 'http_status': exhibit_status,
                                         'response_received': True, 'ok': True})
                        exhibits.append({**candidate, 'source_url': exhibit_url,
                                         'sha256': hashlib.sha256(exhibit_body).hexdigest(),
                                         'size_bytes': len(exhibit_body),
                                         'release_timestamp_evidence': None})
                        time.sleep(self.pause_seconds)
                    event = make_event(ticker, cik, row, document, retrieved,
                                       receipt_latency_seconds, processing_seconds)
                    event['earnings_exhibits'] = exhibits
                    events.append(event)
                    time.sleep(self.pause_seconds)
            except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
                requests.append({'url': url, 'response_received': isinstance(exc, HTTPError),
                                 'http_status': getattr(exc, 'code', None), 'ok': False,
                                 'error': f'{type(exc).__name__}: {exc}'})
                raise RuntimeError(f'SEC request failed for {ticker}: {exc}') from exc
            time.sleep(self.pause_seconds)
        return ingest(events, synthetic=False), requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', required=True, help='Inclusive UTC ISO-8601 timestamp')
    parser.add_argument('--end', required=True, help='Exclusive UTC ISO-8601 timestamp')
    parser.add_argument('--user-agent', default=os.environ.get('IAA_SEC_USER_AGENT'),
                        help='SEC-compliant identity, e.g. Project Name contact@example.com')
    parser.add_argument('--receipt-latency-seconds', type=int, default=180)
    parser.add_argument('--processing-seconds', type=int, default=15)
    parser.add_argument('--universe', choices=['core', 'expanded', 'extension'], default='core')
    args = parser.parse_args()
    if min(args.receipt_latency_seconds, args.processing_seconds) < 0:
        parser.error('latencies must be non-negative')
    start = datetime.fromisoformat(args.start.replace('Z', '+00:00')).astimezone(timezone.utc)
    end = datetime.fromisoformat(args.end.replace('Z', '+00:00')).astimezone(timezone.utc)
    if start >= end:
        parser.error('start must be before end')
    provider = SECProvider(args.user_agent)
    ciks = {'core':CORE_CIKS, 'expanded':EXPANDED_CIKS,
            'extension':EXTENSION_CIKS}[args.universe]
    events, requests = provider.collect(start, end, args.receipt_latency_seconds,
                                        args.processing_seconds, ciks=ciks)
    root = Path(__file__).resolve().parents[1]
    output = root / 'data' / {'core':'events_sec.jsonl',
                              'expanded':'events_sec_expanded.jsonl',
                              'extension':'events_sec_extension.jsonl'}[args.universe]
    write_jsonl_atomic(output, events)
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'provider': provider.name,
        'synthetic': False, 'real_sec_response_received': any(r['response_received'] for r in requests),
        'universe': args.universe, 'issuer_count': len(ciks),
        'issuer_release_time_validated': False, 'timestamp_semantics': 'edgar_acceptance',
        'event_count': len(events), 'output': str(output), 'requests': requests,
    }
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    report_path = reports / ('event-ingestion-sec-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(report_path), 'provider': provider.name,
                      'synthetic': False, 'real_sec_response_received': report['real_sec_response_received'],
                      'issuer_release_time_validated': False, 'event_count': len(events)}, indent=2))


if __name__ == '__main__':
    main()
