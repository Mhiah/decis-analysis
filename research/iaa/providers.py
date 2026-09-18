"""Read-only market data providers with explicit provenance and error categories."""
import json
import socket
import ssl
from datetime import datetime, timezone
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://api.bitget.com/api/v3/market/'
TRANSPORT_ERRORS = {'DNS', 'CONNECTION', 'TIMEOUT', 'TLS', 'NETWORK'}


class DataProvider(Protocol):
    name: str
    synthetic: bool
    anchor_ms: int | None

    def instruments(self) -> dict: ...
    def ticker(self, symbol: str) -> dict: ...
    def candles(self, symbol: str, end_ms: int, limit: int = 100) -> dict: ...


def error_kind(exc):
    cause = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(cause, socket.gaierror):
        return 'DNS'
    if isinstance(cause, (TimeoutError, socket.timeout)):
        return 'TIMEOUT'
    if isinstance(cause, ssl.SSLError):
        return 'TLS'
    if isinstance(cause, ConnectionError):
        return 'CONNECTION'
    return 'NETWORK'


class BitgetProvider:
    name = 'bitget'
    synthetic = False
    anchor_ms = None

    def __init__(self, opener=None, timeout=15, dns_fallback=False):
        self.opener = opener or urlopen
        if dns_fallback:
            from .dns_transport import DNSFallbackOpener
            self.opener = DNSFallbackOpener(self.opener)
        self.timeout = timeout

    def _fetch(self, endpoint, **params):
        url = BASE + endpoint + '?' + urlencode(params)
        result = {'provider': self.name, 'synthetic': False, 'url': url,
                  'retrieved_at': datetime.now(timezone.utc).isoformat(), 'ok': False,
                  'http_response_received': False, 'api_response_received': False}
        try:
            req = Request(url, headers={'User-Agent': 'IAA-Research-Audit/0.2'})
            result['transport'] = {'route': 'system_dns', 'fallback_attempted': False}
            req.iaa_transport = result['transport']
            with self.opener(req, timeout=self.timeout) as response:
                result.update(http_response_received=True, http_status=response.status)
                body = json.load(response)
            result['body'] = body
            if not isinstance(body, dict) or not isinstance(body.get('code'), str):
                result.update(error_kind='SCHEMA', error='Missing Bitget response code')
            else:
                result['api_response_received'] = True
                if body['code'] != '00000':
                    result.update(error_kind='API', error=str(body.get('msg', body['code'])))
                elif not isinstance(body.get('data'), list):
                    result.update(error_kind='SCHEMA', error='Expected list in data')
                elif endpoint in ('instruments', 'tickers') and not all(isinstance(x, dict) for x in body['data']):
                    result.update(error_kind='SCHEMA', error='Expected object records')
                elif endpoint == 'history-candles' and not all(isinstance(x, list) and len(x) >= 5 for x in body['data']):
                    result.update(error_kind='SCHEMA', error='Expected candle arrays')
                else:
                    result['ok'] = True
        except HTTPError as exc:
            result.update(http_response_received=True, http_status=exc.code,
                          error_kind='HTTP', error=f'HTTP {exc.code}: {exc.reason}')
            exc.close()
        except (URLError, OSError) as exc:
            result.update(error_kind=error_kind(exc), error=f'{type(exc).__name__}: {exc}')
        except (ValueError, UnicodeError) as exc:
            result.update(error_kind='DECODE', error=f'{type(exc).__name__}: {exc}')
        return result

    def instruments(self):
        return self._fetch('instruments', category='SPOT')

    def ticker(self, symbol):
        return self._fetch('tickers', category='SPOT', symbol=symbol)

    def candles(self, symbol, end_ms, limit=100):
        if not 1 <= limit <= 100:
            raise ValueError('Candle limit must be between 1 and 100')
        return self._fetch('history-candles', category='SPOT', symbol=symbol,
                           interval='1m', endTime=end_ms, limit=limit, type='market')


class MockProvider:
    """Deterministic fixtures. No network calls, current-price claims or live provenance."""
    name = 'mock'
    synthetic = True
    anchor_ms = 1789128000000
    symbols = ('RAAPLUSDT', 'RMSFTUSDT', 'RNVDAUSDT')

    def _result(self, data):
        return {'provider': self.name, 'synthetic': True, 'ok': True,
                'http_response_received': False, 'api_response_received': False,
                'fixture_version': 'v1', 'body': {'code': '00000', 'msg': 'SYNTHETIC FIXTURE', 'data': data}}

    def _check_symbol(self, symbol):
        if symbol not in self.symbols:
            raise ValueError(f'Unknown fixture symbol: {symbol}')

    def instruments(self):
        return self._result([{'symbol': s, 'category': 'SPOT', 'isReality': 'yes',
                              'status': 'online'} for s in self.symbols])

    def ticker(self, symbol):
        self._check_symbol(symbol)
        return self._result([{'symbol': symbol, 'bid1Price': '100.69', 'ask1Price': '100.71',
                              'bid1Size': '50', 'ask1Size': '50', 'ts': str(self.anchor_ms)}])

    def candles(self, symbol, end_ms, limit=100):
        self._check_symbol(symbol)
        if not 1 <= limit <= 100:
            raise ValueError('Candle limit must be between 1 and 100')
        end = int(end_ms) // 60000 * 60000
        return self._result([[str(end - (limit-i)*60000), '100', '100.8', '99.9',
                              f'{100+i*.007:.3f}', '50', '5000'] for i in range(limit)])


def select_provider(mode, live=None, dns_fallback=False):
    """Fallback is explicit, applies only before a dataset starts, and retains failure."""
    if dns_fallback and mode not in ('bitget', 'auto'):
        raise ValueError('DNS fallback is available only for REST bitget/auto providers')
    if mode == 'mock':
        provider = MockProvider()
        return provider, provider.instruments(), None
    if mode not in ('bitget', 'auto', 'bgc', 'bgc-auto'):
        raise ValueError('Provider must be bitget, mock, auto, bgc or bgc-auto')
    if mode.startswith('bgc'):
        from .bgc_provider import BGCProvider
        provider = live or BGCProvider()
    else:
        provider = live or BitgetProvider(dns_fallback=dns_fallback)
    initial = provider.instruments()
    if mode in ('auto', 'bgc-auto') and not initial['ok'] and initial.get('error_kind') in TRANSPORT_ERRORS:
        fallback = MockProvider()
        return fallback, fallback.instruments(), initial
    return provider, initial, None
