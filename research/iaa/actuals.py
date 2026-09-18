"""Extract structured actuals from hash-verified SEC earnings exhibits."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from .consensus import calculate_surprise


class TextTokens(HTMLParser):
    def __init__(self):
        super().__init__(); self.tokens = []
    def handle_data(self, data):
        value = ' '.join(data.split())
        if value:
            self.tokens.append(value)


def visible_tokens(body):
    parser = TextTokens(); parser.feed(body.decode('utf-8', errors='replace'))
    return parser.tokens


def money(value):
    match = re.fullmatch(r'\$([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', value)
    if not match:
        raise ValueError(f'Expected a monetary value, received {value!r}')
    return float(match.group(1).replace(',', ''))


def section_metric(tokens, section, metric):
    start = tokens.index(section)
    index = tokens.index(metric, start + 1)
    return tokens[index + 1]


def extract_nvidia_metrics(body):
    tokens = visible_tokens(body)
    title = next((token for token in tokens if 'NVIDIA Announces Financial Results' in token), None)
    if not title:
        raise ValueError('Unexpected earnings exhibit identity')
    quarter = re.search(r'for (First|Second|Third|Fourth) Quarter Fiscal (\d{4})', title, flags=re.I)
    if not quarter:
        raise ValueError('NVIDIA fiscal-period identity was not found')
    quarter_number = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4}[quarter.group(1).lower()]
    fiscal_year = int(quarter.group(2))
    fiscal_period = f'Q{quarter_number} FY{fiscal_year}'
    revenue_millions = money(section_metric(tokens, 'GAAP', 'Revenue'))
    adjusted_eps = money(section_metric(tokens, 'Non-GAAP', 'Diluted earnings per share'))
    outlook = next((token for token in tokens[tokens.index('Outlook') + 1:]
                    if token.startswith('Revenue is expected to be $')), None)
    match = re.match(r'Revenue is expected to be \$([0-9.]+) billion, plus or minus ([0-9.]+)%', outlook or '')
    if not match:
        raise ValueError('Revenue guidance statement was not found')
    guidance_billions, range_percent = map(float, match.groups())
    return [
        {'metric':'revenue', 'basis':'GAAP', 'value':revenue_millions * 1_000_000,
         'unit':'USD', 'fiscal_period':fiscal_period, 'source_span':f'Revenue | ${revenue_millions:,.0f} million'},
        {'metric':'adjusted_eps', 'basis':'non-GAAP diluted', 'value':adjusted_eps,
         'unit':'USD/share', 'fiscal_period':fiscal_period,
         'source_span':f'Non-GAAP diluted EPS | ${adjusted_eps:.2f}'},
        {'metric':'revenue_guidance', 'basis':'company outlook midpoint',
         'value':guidance_billions * 1_000_000_000, 'unit':'USD',
         'fiscal_period':(f'Q{quarter_number + 1} FY{fiscal_year}' if quarter_number < 4
                          else f'Q1 FY{fiscal_year + 1}'),
         'range_fraction':range_percent / 100,
         'source_span':f'Revenue outlook | ${guidance_billions:.1f}B ±{range_percent:g}%'},
    ]


def extract_apple_metrics(body):
    text = ' '.join(visible_tokens(body))
    title_period = re.search(r'Apple reports (first|second|third|fourth) quarter results', text, re.I)
    fiscal_period_match = re.search(r'fiscal (\d{4}) (first|second|third|fourth) quarter', text, re.I)
    if (not title_period or not fiscal_period_match or
            title_period.group(1).lower() != fiscal_period_match.group(2).lower()):
        raise ValueError('Unexpected Apple earnings exhibit identity')
    quarter_number = {'first':1, 'second':2, 'third':3, 'fourth':4}[title_period.group(1).lower()]
    fiscal_period = f'Q{quarter_number} FY{fiscal_period_match.group(1)}'
    match = re.search(
        r'quarterly revenue of \$([0-9.]+) billion.*?Diluted earnings per share was \$([0-9.]+)',
        text, flags=re.I)
    if not match:
        raise ValueError('Apple revenue and diluted EPS statement was not found')
    revenue_billions, diluted_eps = map(float, match.groups())
    return [
        {'metric':'revenue', 'basis':'GAAP', 'value':revenue_billions * 1_000_000_000,
         'unit':'USD', 'fiscal_period':fiscal_period,
         'source_span':f'Quarterly revenue | ${revenue_billions:.1f} billion'},
        {'metric':'diluted_eps', 'basis':'GAAP diluted', 'value':diluted_eps,
         'unit':'USD/share', 'fiscal_period':fiscal_period,
         'source_span':f'Diluted earnings per share | ${diluted_eps:.2f}'},
    ]


def extract_tesla_metrics(body):
    text = ' '.join(visible_tokens(body))
    identity = re.search(r'Q([1-4]) 2026 Update', text)
    if not identity or 'F I N A N C I A L S U M M A R Y' not in text:
        raise ValueError('Unexpected Tesla earnings exhibit identity')
    fiscal_period = f'Q{identity.group(1)} FY2026'
    revenue = re.search(r'Total revenues(?:\s+[0-9,]+){4}\s+([0-9,]+)\s+[-0-9]+%', text)
    adjusted_eps = re.search(
        r'EPS attributable to common stockholders, diluted \(non-GAAP\)'
        r'(?:\s+[0-9.]+){4}\s+([0-9.]+)\s+[-0-9]+%', text)
    if not revenue or not adjusted_eps:
        raise ValueError('Tesla revenue and non-GAAP diluted EPS rows were not found')
    revenue_millions = float(revenue.group(1).replace(',', ''))
    eps = float(adjusted_eps.group(1))
    return [
        {'metric':'revenue', 'basis':'GAAP', 'value':revenue_millions * 1_000_000,
         'unit':'USD', 'fiscal_period':fiscal_period,
         'source_span':f'Total revenues | {revenue_millions:,.0f} million'},
        {'metric':'adjusted_eps', 'basis':'non-GAAP diluted', 'value':eps,
         'unit':'USD/share', 'fiscal_period':fiscal_period,
         'source_span':f'Non-GAAP diluted EPS | ${eps:.2f}'},
    ]


QUARTERS = {'first':1, 'second':2, 'third':3, 'fourth':4}


def _amount(raw, scale=1):
    """Parse an SEC display amount, including parenthesized losses."""
    value = raw.replace('$', '').replace(',', '').strip().rstrip('.,;')
    negative = value.startswith('(') and value.endswith(')')
    value = value.strip('()')
    parsed = (-1 if negative else 1) * float(value) * scale
    return int(round(parsed)) if scale != 1 else parsed


def _period(text, pattern, short_year=False):
    match = re.search(pattern, text, re.I)
    if not match:
        raise ValueError('Fiscal-period identity was not found')
    quarter = match.group('quarter')
    number = int(quarter) if quarter.isdigit() else QUARTERS[quarter.lower()]
    year = int(match.group('year'))
    if short_year:
        year += 2000
    return f'Q{number} FY{year}'


def _metric(metric, basis, value, unit, fiscal_period, source_span):
    return {'metric':metric, 'basis':basis, 'value':value, 'unit':unit,
            'fiscal_period':fiscal_period, 'source_span':source_span}


def extract_expanded_metrics(body, ticker):
    """Extract headline actuals using issuer-bound EX-99.1 layouts."""
    text = ' '.join(visible_tokens(body))
    specs = {
        'NFLX': (r'July \d+, (?P<year>\d{4}).*?Q(?P<quarter>[1-4]) revenue grew', False,
                 r'Q[1-4] revenue of \$([0-9.]+)B', 1_000_000_000,
                 [(r'Diluted EPS for the quarter amounted to \$([0-9.]+)', 'diluted_eps', 'GAAP diluted')]),
        'GOOGL': (r'Alphabet Announces (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4}) Results', False,
                  r'Consolidated Alphabet revenues.*?to \$([0-9.]+) billion', 1_000_000_000,
                  [(r'EPS increased .*? to \$([0-9.]+)', 'diluted_eps', 'GAAP diluted')]),
        'INTC': (r'Intel Reports (?P<quarter>First|Second|Third|Fourth)-Quarter (?P<year>\d{4}) Financial Results', False,
                 r'quarter revenue was \$([0-9.]+) billion', 1_000_000_000,
                 [(r'earnings \(loss\) per share .*? was \$?(\([0-9.]+\))', 'diluted_eps', 'GAAP diluted'),
                  (r'non-GAAP EPS attributable to Intel was \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'META': (r'Meta Reports (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4}) Results', False,
                 r'Revenue was \$([0-9.]+) billion', 1_000_000_000,
                 [(r'Diluted earnings per share \(EPS\) \$ ([0-9.]+)', 'diluted_eps', 'GAAP diluted')]),
        'MSFT': (r'(?P<quarter>First|Second|Third|Fourth) Quarter Results.*?quarter ended .*? (?P<year>\d{4})', False,
                 r'Revenue was \$([0-9.]+) billion', 1_000_000_000,
                 [(r'Diluted earnings per share was \$([0-9.]+).*?GAAP basis', 'diluted_eps', 'GAAP diluted'),
                  (r'Diluted earnings per share was .*?and was \$([0-9.]+).*?non-GAAP basis', 'adjusted_eps', 'non-GAAP diluted')]),
        'HOOD': (r'Robinhood Reports (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4})', False,
                 r'Revenues up .*? to a record \$([0-9.]+) billion', 1_000_000_000,
                 [(r'Diluted EPS up .*? to \$([0-9.]+)', 'diluted_eps', 'GAAP diluted')]),
        'COIN': (r'Q(?P<quarter>[1-4])[’\'](?P<year>\d{2}) EARNINGS', True,
                 r'Total revenue of \$([0-9.]+)B', 1_000_000_000,
                 [(r'Net income \(loss\) per share - Diluted(?:\s+\(?-?[0-9.]+\)?){4}\s+(\(?-?[0-9.]+\)?)', 'diluted_eps', 'GAAP diluted')]),
        'AMZN': (r'ANNOUNCES (?P<quarter>FIRST|SECOND|THIRD|FOURTH) QUARTER RESULTS.*?quarter ended .*? (?P<year>\d{4})', False,
                 r'Net sales increased .*? to \$([0-9.]+) billion in the (?:first|second|third|fourth) quarter', 1_000_000_000,
                 [(r'Net income increased to .*? or \$([0-9.]+) per diluted share', 'diluted_eps', 'GAAP diluted')]),
        'PLTR': (r'Palantir Reports Q(?P<quarter>[1-4]) (?P<year>\d{4})', False,
                 r'Q[1-4] \d{4} Highlights .*? • Revenue grew .*? to \$([0-9.]+) billion', 1_000_000_000,
                 [(r'GAAP earnings per share .*? of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                  (r'Adjusted EPS of \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'AMD': (r'AMD Reports (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4}) Financial Results', False,
                r'quarter revenue was \$([0-9.]+) billion', 1_000_000_000,
                [(r'diluted earnings per share was \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                 (r'On a non-GAAP.*?diluted earnings per share was \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'CRM': (r'Salesforce Delivers Record (?P<quarter>First|Second|Third|Fourth) Quarter Fiscal (?P<year>\d{4}) Results', False,
                r'(?<!support )Revenue of \$([0-9.]+) billion', 1_000_000_000,
                [(r'GAAP diluted net income per share of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                 (r'non-GAAP diluted net income per share of \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'AVGO': (r'Broadcom Inc\. Announces (?P<quarter>First|Second|Third|Fourth) Quarter Fiscal Year (?P<year>\d{4})', False,
                 r'Revenue of \$([0-9.]+) billion for the (?:first|second|third|fourth) quarter', 1_000_000_000,
                 [(r'GAAP diluted EPS of \$([0-9.]+) for the (?:first|second|third|fourth) quarter', 'diluted_eps', 'GAAP diluted'),
                  (r'Non-GAAP diluted EPS of \$([0-9.]+) for the (?:first|second|third|fourth) quarter', 'adjusted_eps', 'non-GAAP diluted')]),
        'ADBE': (r'Adobe Reports Record Q(?P<quarter>[1-4]) Results.*?quarter FY(?P<year>\d{4})', False,
                 r'Adobe achieved record revenue of \$([0-9.]+) billion', 1_000_000_000,
                 [(r'Diluted earnings per share was \$([0-9.]+) on a GAAP basis', 'diluted_eps', 'GAAP diluted'),
                  (r'and \$([0-9.]+) on a non-GAAP basis', 'adjusted_eps', 'non-GAAP diluted')]),
        'ORCL': (r'Oracle Announces Q(?P<quarter>[1-4]) Results.*?Q[1-4] FY(?P<year>\d{2}) results', True,
                 r'Total quarterly revenues increased .*? to \$([0-9.]+) billion', 1_000_000_000,
                 [(r'GAAP earnings per share increased to \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                  (r'non-GAAP earnings per share climbed to \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'JPM': (r'(?P<quarter>SECOND)-QUARTER (?P<year>\d{4}) NET INCOME', False,
                r'managed revenue 2 of \$([0-9.]+) billion', 1_000_000_000,
                [(r'NET INCOME OF \$[0-9.]+ BILLION \(\s*\$([0-9.]+) PER SHARE\)', 'diluted_eps', 'GAAP diluted'),
                 (r'NET INCOME EXCLUDING SIGNIFICANT ITEMS OF \$[0-9.]+ BILLION \(\$?([0-9.]+) PER SHARE\)',
                  'adjusted_eps', 'non-GAAP diluted')]),
        'IBM': (r'preliminary (?P<quarter>first|second|third|fourth)-quarter (?P<year>\d{4}) financial results', False,
                r'Revenue of \$([0-9.]+) billion', 1_000_000_000,
                [(r'Diluted Earnings Per Share:\s*GAAP:\s*\$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                 (r'Operating \(Non-GAAP\):\s*\$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'JNJ': (r'Johnson & Johnson reports Q(?P<quarter>[1-4]) (?P<year>\d{4}) results', False,
                r'Second-Quarter reported sales growth of [0-9.]+% to \$([0-9.]+) Billion', 1_000_000_000,
                [(r'Second-Quarter earnings per share \(EPS\) of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                 (r'adjusted EPS\* of \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'GE': (r'GE AEROSPACE ANNOUNCES (?P<quarter>FIRST|SECOND|THIRD|FOURTH) QUARTER (?P<year>\d{4}) RESULTS', False,
               r'Total revenue \(GAAP\) of \$([0-9.]+)B', 1_000_000_000,
               [(r'Continuing EPS \(GAAP\) of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                (r'adjusted EPS\* \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'PYPL': (r'PayPal Reports (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4}) Results', False,
                 r'Net revenues increased [0-9.]+% to \$([0-9.]+) billion', 1_000_000_000,
                 [(r'GAAP EPS decreased [0-9.]+% to \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                  (r'non-GAAP EPS decreased [0-9.]+% to \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'BA': (r'Boeing Reports (?P<quarter>First|Second|Third|Fourth) Quarter Results\s+(?:First|Second|Third|Fourth) Quarter (?P<year>\d{4})', False,
               r'Revenue increased to \$([0-9.]+) billion', 1_000_000_000,
               [(r'GAAP loss per share of (\(\$?[0-9.]+\))', 'diluted_eps', 'GAAP diluted')]),
        'V': (r'Visa Reports Fiscal (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4}) Results', False,
              r'Net revenue of \$([0-9.]+)B', 1_000_000_000,
              [(r'GAAP net income of \$[0-9.]+B or \$([0-9.]+) per share', 'diluted_eps', 'GAAP diluted'),
               (r'non-GAAP net income of \$[0-9.]+B or \$([0-9.]+) per share', 'adjusted_eps', 'non-GAAP diluted')]),
        'QCOM': (r'Qualcomm Announces (?P<quarter>First|Second|Third|Fourth) Quarter Fiscal (?P<year>\d{4}) Results', False,
                 r'Revenues:\s*\$([0-9.]+) billion', 1_000_000_000,
                 [(r'GAAP EPS:\s*\$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                  (r'Non-GAAP EPS:\s*\$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'MA': (r'Mastercard Incorporated Reports (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4}) Financial Results', False,
               r'Second quarter net reven\s*ue of \$([0-9.]+) billion', 1_000_000_000,
               [(r'diluted earnings per share \(EPS\) of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                (r'adjusted diluted EPS of \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'MCD': (r"McDONALD'S REPORTS (?P<quarter>FIRST|SECOND|THIRD|FOURTH) QUARTER (?P<year>\d{4}) RESULTS", False,
                r'Revenues \$ ([0-9,]+)', 1_000_000,
                [(r'Diluted earnings per share was \$([0-9.]+)', 'diluted_eps', 'GAAP diluted')]),
        'DIS': (r'fiscal Q(?P<quarter>[1-4]) results.*?June \d+, (?P<year>\d{4})', False,
                r'Revenues increased [0-9.]+% for the third quarter to \$([0-9.]+) billion', 1_000_000_000,
                [(r'Diluted earnings per share \(EPS\) decreased to \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                 (r'Adjusted EPS \(1\) increased to \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'UBER': (r'Uber Announces Results for (?P<quarter>First|Second|Third|Fourth) Quarter (?P<year>\d{4})', False,
                 r'Revenue grew [0-9.]+% YoY to \$([0-9.]+) billion', 1_000_000_000,
                 [(r'GAAP Diluted EPS of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                  (r'Non-GAAP EPS of \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'LLY': (r'Revenue in Q(?P<quarter>[1-4]) (?P<year>\d{4}) increased', False,
                r'Revenue in Q[1-4] [0-9]{4} increased [0-9.]+% to \$([0-9.]+) billion', 1_000_000_000,
                [(r'Q[1-4] [0-9]{4} EPS increased by [0-9.]+% to \$([0-9.]+) on a reported basis', 'diluted_eps', 'GAAP diluted'),
                 (r'increased by [0-9.]+% to \$([0-9.]+) on a non-GAAP basis', 'adjusted_eps', 'non-GAAP diluted')]),
        'CSCO': (r'CISCO REPORTS (?P<quarter>FIRST|SECOND|THIRD|FOURTH) QUARTER AND FISCAL YEAR (?P<year>\d{4}) EARNINGS', False,
                 r'Q4 FY [0-9]{4} Results:.*?Revenue:\s*\$([0-9.]+) billion', 1_000_000_000,
                 [(r'Earnings per Share:\s*GAAP:\s*\$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                  (r'Earnings per Share:\s*GAAP:\s*\$[0-9.]+;\s*Non-GAAP:\s*\$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'HD': (r'The Home Depot Announces (?P<quarter>First|Second|Third|Fourth) Quarter Fiscal (?P<year>\d{4}) Results', False,
               r'reported sales of \$([0-9.]+) billion for the second quarter', 1_000_000_000,
               [(r'or \$([0-9.]+) per diluted share, compared with net earnings', 'diluted_eps', 'GAAP diluted'),
                (r'Adjusted \(1\) diluted earnings per share .*? were \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
        'WMT': (r'Walmart reports (?P<quarter>second) quarter results.*?FY(?P<year>\d{2})', True,
                r'Revenue of \$([0-9.]+) billion', 1_000_000_000,
                [(r'GAAP EPS of \$([0-9.]+)', 'diluted_eps', 'GAAP diluted'),
                 (r'Adjusted EPS 1 of \$([0-9.]+)', 'adjusted_eps', 'non-GAAP diluted')]),
    }
    if ticker not in specs:
        raise ValueError(f'Unsupported expanded actuals ticker: {ticker}')
    period_pattern, short_year, revenue_pattern, revenue_scale, eps_specs = specs[ticker]
    fiscal_period = _period(text, period_pattern, short_year)
    revenue = re.search(revenue_pattern, text, re.I)
    if not revenue:
        raise ValueError(f'{ticker} revenue statement was not found')
    metrics = [_metric('revenue', 'GAAP', _amount(revenue.group(1), revenue_scale),
                       'USD', fiscal_period, revenue.group(0))]
    for pattern, name, basis in eps_specs:
        match = re.search(pattern, text, re.I)
        if not match:
            raise ValueError(f'{ticker} {name} statement was not found')
        metrics.append(_metric(name, basis, _amount(match.group(1)), 'USD/share',
                               fiscal_period, match.group(0)))
    return metrics


def extract_metrics(body, ticker='NVDA'):
    extractors = {'NVDA': extract_nvidia_metrics, 'AAPL': extract_apple_metrics,
                  'TSLA': extract_tesla_metrics}
    if ticker in extractors:
        return extractors[ticker](body)
    return extract_expanded_metrics(body, ticker)


def verified_exhibit(event, body):
    sec_evidence = event.get('sec_filing_evidence') or event
    exhibits = [item for item in sec_evidence.get('earnings_exhibits', [])
                if item.get('type') == 'EX-99.1']
    if len(exhibits) != 1:
        raise ValueError('Exactly one SEC EX-99.1 exhibit is required')
    digest = hashlib.sha256(body).hexdigest()
    if digest != exhibits[0].get('sha256'):
        raise ValueError('Downloaded exhibit hash does not match SEC ingestion evidence')
    return exhibits[0], digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--consensus', type=Path)
    parser.add_argument('--output', type=Path,
                        help='JSONL destination; defaults to data/actuals.jsonl')
    parser.add_argument('--event-id', action='append', dest='event_ids',
                        help='extract only selected event IDs; may be supplied more than once')
    args = parser.parse_args()
    events = [json.loads(line) for line in args.events.read_text(encoding='utf-8').splitlines() if line]
    if args.event_ids:
        requested = set(args.event_ids)
        events = [event for event in events if event['event_id'] in requested]
        missing = requested - {event['event_id'] for event in events}
        if missing:
            raise ValueError('Requested event IDs not found: ' + ', '.join(sorted(missing)))
    records = []
    responses = []
    for event in events:
        sec_evidence = event.get('sec_filing_evidence') or event
        exhibits = sec_evidence.get('earnings_exhibits', [])
        url = next((item['source_url'] for item in exhibits if item.get('type') == 'EX-99.1'), None)
        if not url:
            raise ValueError(f"Verified EX-99.1 URL is missing for {event['event_id']}")
        request = Request(url, headers={'User-Agent':'IAA-Research/0.1 iaa.contact2026@gmail.com',
                                        'Accept-Encoding':'identity'})
        with urlopen(request, timeout=30) as response:
            body = response.read(); status = response.status
        exhibit, digest = verified_exhibit(event, body)
        ticker = event['underlying_ticker']
        metrics = extract_metrics(body, ticker)
        extracted_at = datetime.now(timezone.utc).isoformat()
        records.extend([{**metric, 'event_id':event['event_id'], 'source_url':url,
                         'source_sha256':digest, 'extracted_at':extracted_at,
                         'extraction_version':f'{ticker.lower()}-ex99.1-v1'} for metric in metrics])
        responses.append({'event_id':event['event_id'], 'ticker':ticker, 'http_status':status,
                          'hash_verified':True, 'metric_count':len(metrics)})
    surprises = []
    if args.consensus:
        consensus = [json.loads(line) for line in args.consensus.read_text(encoding='utf-8').splitlines() if line]
        for estimate in consensus:
            actual = next((record for record in records if record['event_id'] == estimate['event_id']
                           and record['metric'] == estimate['metric']
                           and record['fiscal_period'] == estimate['fiscal_period']), None)
            if actual:
                surprises.append({'event_id':estimate['event_id'], 'metric':estimate['metric'],
                                  'estimate':estimate['estimate'], 'actual':actual['value'],
                                  'surprise_fraction':calculate_surprise(estimate['estimate'], actual['value']),
                                  'consensus_id':estimate['consensus_id'],
                                  'immutable_snapshot_validated':estimate['immutable_snapshot_validated']})
    root = Path(__file__).resolve().parents[1]
    output = args.output or (root / 'data' / 'actuals.jsonl')
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(''.join(json.dumps(record, sort_keys=True) + '\n' for record in records), encoding='utf-8')
    report = {'created_at':datetime.now(timezone.utc).isoformat(), 'provider':'sec_exhibit',
              'synthetic':False, 'real_exhibit_response_received':True,
              'hash_verified':all(item['hash_verified'] for item in responses),
              'event_count':len(events), 'metric_count':len(records), 'responses':responses,
              'metrics':records, 'surprises':surprises, 'output':str(output)}
    reports = root / 'reports'; reports.mkdir(exist_ok=True)
    report_path = reports / ('actuals-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report':str(report_path), 'real_exhibit_response_received':True,
                      'hash_verified':True, 'metrics':len(records), 'surprises':surprises}, indent=2))


if __name__ == '__main__': main()
