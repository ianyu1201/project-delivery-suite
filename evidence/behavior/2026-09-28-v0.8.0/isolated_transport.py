"""Local allowlisted CONNECT tunnel and one macOS seatbelt boundary.
Only proxy decision metadata is retained; no headers, credentials or payloads.
"""
import os
import socket
import socketserver
import select
import ssl
import threading
from pathlib import Path
from urllib.parse import urlsplit


class IsolatedTransport:
    def __init__(self, fixture, runtime):
        self.fixture = Path(fixture).resolve()
        self.runtime = Path(runtime).resolve()
        self.decisions = []
        self.upstream = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        self.prefix = None
        self.env = None

    def __enter__(self):
        self.runtime.mkdir(parents=True, exist_ok=True)
        (self.runtime / 'tmp').mkdir(exist_ok=True)
        owner = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                client = self.request
                client.settimeout(20)
                header = bytearray()
                while b'\r\n\r\n' not in header and len(header) <= 16384:
                    data = client.recv(1)
                    if not data:
                        return
                    header.extend(data)
                first = bytes(header).split(b'\r\n', 1)[0].decode('ascii', 'replace').split()
                allowed = len(first) == 3 and first[0] == 'CONNECT' and first[1].lower() == 'chatgpt.com:443'
                owner.decisions.append({'method': first[0] if first else 'invalid', 'allowed': allowed})
                if not allowed:
                    client.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n')
                    return
                upstream = None
                try:
                    if owner.upstream:
                        u = urlsplit(owner.upstream)
                        if u.scheme not in ('http', 'https') or u.username or u.password:
                            raise ValueError('unsupported upstream proxy configuration')
                        upstream = socket.create_connection((u.hostname, u.port or 80), timeout=20)
                        if u.scheme == 'https':
                            upstream = ssl.create_default_context().wrap_socket(upstream, server_hostname=u.hostname)
                        upstream.sendall(b'CONNECT chatgpt.com:443 HTTP/1.1\r\nHost: chatgpt.com:443\r\n\r\n')
                        reply = bytearray()
                        while b'\r\n\r\n' not in reply and len(reply) <= 16384:
                            d = upstream.recv(1)
                            if not d:
                                raise OSError('upstream closed')
                            reply.extend(d)
                        if bytes(reply).split(b' ', 2)[1] != b'200':
                            raise OSError('upstream rejected tunnel')
                    else:
                        upstream = socket.create_connection(('chatgpt.com', 443), timeout=20)
                    client.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                    client.settimeout(None)
                    upstream.settimeout(None)
                    while True:
                        ready, _, _ = select.select([client, upstream], [], [], 90)
                        if not ready:
                            break
                        for source in ready:
                            data = source.recv(65536)
                            if not data:
                                return
                            (upstream if source is client else client).sendall(data)
                except (OSError, ValueError, IndexError):
                    return
                finally:
                    if upstream:
                        upstream.close()

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.server = Server(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        port = self.server.server_address[1]
        def sbquote(value):
            return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'
        allowed_write = [self.fixture, self.runtime]
        home = Path.home()
        allowed_read = [self.fixture, self.runtime, home / '.nvm']
        self.profile = '\n'.join([
            '(version 1)', '(allow default)',
            '(deny file-write* (require-all ' + ' '.join('(require-not (subpath '+sbquote(p)+'))' for p in allowed_write) + ' (require-not (literal "/dev/null"))))',
            '(deny file-read-data (require-all (subpath '+sbquote(home)+') ' + ' '.join('(require-not (subpath '+sbquote(p)+'))' for p in allowed_read) + '))',
            '(deny file-read-data (require-all (subpath "/private/tmp/pds-behavior-20260928") (require-not (subpath '+sbquote(self.fixture)+'))))',
            '(deny network-outbound (require-not (remote ip "localhost:'+str(port)+'")))',
            '(deny network-bind)', '(deny network-inbound)',
        ])
        self.prefix = ['/usr/bin/sandbox-exec', '-p', self.profile]
        self.env = {k:v for k,v in os.environ.items() if not k.startswith('CODEX') and 'proxy' not in k.lower()}
        self.env.update(CODEX_HOME=str(self.runtime), TMPDIR=str(self.runtime/'tmp'), PYTHONDONTWRITEBYTECODE='1', HTTP_PROXY=f'http://127.0.0.1:{port}', HTTPS_PROXY=f'http://127.0.0.1:{port}', ALL_PROXY=f'http://127.0.0.1:{port}', NO_PROXY='')
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
