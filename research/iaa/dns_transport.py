"""Optional DNS-only recovery for public Bitget GETs. No OS settings are changed."""
import http.client
import ipaddress
import json
import socket
import ssl
import time
from contextlib import contextmanager
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

HOST = 'api.bitget.com'
RESOLVER = 'https://dns.google/resolve?name=api.bitget.com&type=A'


class DNSFallbackOpener:
    def __init__(self, opener=None, dns_ttl_seconds=300):
        self.opener = opener or urlopen
        self.dns_ttl_seconds = dns_ttl_seconds
        self._addresses = None
        self._resolved_at = 0
        self._conn = None
        self._connected_address = None

    def resolve(self, timeout):
        with self.opener(Request(RESOLVER, headers={'Accept': 'application/dns-json'}), timeout=timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or payload.get('Status') != 0:
            raise socket.gaierror('Public DNS resolution failed')
        addresses = []
        for answer in payload.get('Answer', []):
            if answer.get('type') == 1:
                address = ipaddress.ip_address(answer['data'])
                if address.version != 4 or not address.is_global:
                    raise ValueError('Non-public DNS answer rejected')
                if str(address) not in addresses:
                    addresses.append(str(address))
        if not addresses:
            raise socket.gaierror('Public DNS returned no A records')
        return addresses[:2]

    def cached_addresses(self, timeout):
        now = time.monotonic()
        if self._addresses and now - self._resolved_at < self.dns_ttl_seconds:
            return self._addresses, True
        self._addresses = self.resolve(timeout)
        self._resolved_at = now
        return self._addresses, False

    def close(self):
        if self._conn:
            self._conn.close()
        self._conn = None
        self._connected_address = None

    def _connect(self, address, timeout):
        raw = socket.create_connection((address, 443), timeout=timeout)
        try:
            tls = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST)
        except Exception:
            raw.close()
            raise
        conn = http.client.HTTPConnection(HOST, timeout=timeout)
        conn.sock = tls
        self._conn = conn
        self._connected_address = address
        return conn

    @contextmanager
    def __call__(self, request, timeout=15):
        parsed = urlsplit(request.full_url)
        if (parsed.scheme != 'https' or parsed.hostname != HOST or parsed.port not in (None, 443)
                or parsed.username or parsed.password or request.get_method() != 'GET'):
            raise ValueError('DNS fallback only permits HTTPS GET to api.bitget.com')
        trace = getattr(request, 'iaa_transport', {})
        if not self._addresses:
            try:
                response = self.opener(request, timeout=timeout)
            except (URLError, OSError) as exc:
                cause = exc.reason if isinstance(exc, URLError) else exc
                if not isinstance(cause, socket.gaierror):
                    raise  # Never bypass proxy, TLS, HTTP, timeout or application failures.
                trace.update(system_dns_error=str(cause), fallback_attempted=True, resolver=RESOLVER)
            else:
                with response:
                    yield response
                return
        else:
            trace.update(system_dns_error='system DNS failed earlier in this provider session',
                         fallback_attempted=True, resolver=RESOLVER)
        addresses, cache_hit = self.cached_addresses(timeout)
        trace['resolved_addresses'] = addresses
        trace['resolver_cache_hit'] = cache_hit
        last_error = None
        candidates = ([self._connected_address] if self._conn else []) + [
            address for address in addresses if address != self._connected_address]
        for address in candidates:
            try:
                reused = self._conn is not None and address == self._connected_address
                conn = self._conn if reused else self._connect(address, timeout)
                path = parsed.path + ('?' + parsed.query if parsed.query else '')
                conn.request('GET', path, headers={'Host': HOST, 'Accept': 'application/json',
                                                  'User-Agent': 'IAA-Research-Audit/0.3'})
                response = conn.getresponse()
                trace.update(route='dns_over_https', connected_address=address, tls_verification=True,
                             connection_reused=reused)
                if response.status >= 400:
                    raise HTTPError(request.full_url, response.status, response.reason, response.headers, None)
                # Yield outside the retry block: consumer decoding errors must not retry.
            except (ssl.SSLError, HTTPError):
                self.close()
                raise
            except (OSError, http.client.HTTPException) as exc:
                self.close()
                last_error = exc
                continue
            try:
                yield response
            finally:
                response.close()
                if getattr(response, 'will_close', False):
                    self.close()
            return
        raise last_error or OSError('No address could be reached')
