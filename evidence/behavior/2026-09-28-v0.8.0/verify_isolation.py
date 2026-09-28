"""Deterministic isolation probes; never call an external host or a model."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import threading
from isolated_transport import IsolatedTransport

out = Path(__file__).resolve().parent
base = Path('/private/tmp/pds-behavior-20260928/preflight')
fixture = base / 'observer-fixture'
fixture.mkdir(parents=True, exist_ok=True)
(fixture / 'input.txt').write_text('fixture')
sibling = base / 'observer-outside'
sibling.mkdir(exist_ok=True)
(sibling / 'rubric.txt').write_text('NONSECRET_FAKE_RUBRIC')
dummy = out / 'observer-dummy-secret.txt'
dummy.write_text('NONSECRET_OBSERVER_DUMMY')
runtime = Path('/Users/Shared/pds-eval-20260928/observer')
runtime.mkdir(parents=True, exist_ok=True)
(runtime / 'fake-auth.json').write_text('{"fake":true}')
listener = socket.socket()
listener.bind(('127.0.0.1', 0))
listener.listen()
listener.settimeout(4)
port = listener.getsockname()[1]
accepted = []
def serve():
    try:
        connection, _ = listener.accept()
        accepted.append(True)
        connection.close()
    except socket.timeout:
        pass
thread = threading.Thread(target=serve)
thread.start()
with IsolatedTransport(fixture, runtime) as transport:
    probes = [
        ('fixture_read', ['/bin/cat', str(fixture / 'input.txt')], 0),
        ('fixture_write', ['/usr/bin/touch', str(fixture / 'final-allowed.txt')], 0),
        ('tmp_sibling_read_denied', ['/bin/cat', str(sibling / 'rubric.txt')], 1),
        ('tmp_sibling_write_denied', ['/usr/bin/touch', str(sibling / 'final-denied.txt')], 1),
        ('home_rubric_content_read_denied', ['/bin/cat', str(dummy)], 1),
        ('home_write_denied', ['/usr/bin/touch', str(out / 'final-denied.txt')], 1),
        ('runtime_read_exception', ['/bin/cat', str(runtime / 'fake-auth.json')], 0),
        ('runtime_write_exception', ['/usr/bin/touch', str(runtime / 'final-runtime-allowed.txt')], 0),
        ('direct_network_denied', ['/usr/bin/curl', '--noproxy', '*', '--max-time', '1', f'http://127.0.0.1:{port}/'], 7),
        ('non_model_connect_denied', ['/usr/bin/curl', '--max-time', '1', 'https://example.invalid/'], 56),
        ('plain_http_proxy_denied', ['/usr/bin/curl', '--max-time', '1', '--fail', '--proxy', transport.env['HTTPS_PROXY'], 'http://example.invalid/'], 22),
    ]
    rows = []
    for name, command, expected in probes:
        result = subprocess.run(transport.prefix + command, cwd=fixture, env=transport.env, capture_output=True, text=True, timeout=10)
        rows.append({'name': name, 'command': command, 'expected_exit_code': expected, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'passed': result.returncode == expected})
    thread.join()
    listener.close()
    report = {'transport_sha256': hashlib.sha256((out / 'isolated_transport.py').read_bytes()).hexdigest(), 'profile': transport.profile, 'probes': rows, 'direct_listener_accepted': accepted, 'proxy_decisions': transport.decisions, 'all_probe_expectations_met': all(r['passed'] for r in rows) and not accepted, 'limitations': ['Model destination chatgpt.com:443 is an intentional shared exception; no allowed-model external call is made by these probes.', 'Runtime is intentionally readable and writable by CLI and model subprocesses, including any authentication material placed there.', 'Home filesystem metadata is visible; protected file contents and writes are denied.', 'System paths and the Node runtime tree remain readable. This is a bounded functional isolation check, not an adversarial sandbox security certification.']}
(out / 'isolation-final-probes.json').write_text(json.dumps(report, ensure_ascii=False, indent=2).replace(str(Path.home()), '$HOME') + '\n')
print(json.dumps({'all_probe_expectations_met': report['all_probe_expectations_met'], 'probe_count': len(rows), 'report': str(out / 'isolation-final-probes.json')}))
dummy.unlink()
raise SystemExit(0 if report['all_probe_expectations_met'] else 1)
