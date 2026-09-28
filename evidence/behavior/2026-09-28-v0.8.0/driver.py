#!/usr/bin/env python3
"""Isolated actual-model collector. Outcome classification is performed separately."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import re
import time
from isolated_transport import IsolatedTransport

PREFIX = 'plugins/project-delivery-suite/skills/project-delivery-suite/'
EXCLUDE = ('evals/', 'references/behavior-evaluation.md', 'scripts/evaluate_behavior.py', 'scripts/test_')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def snapshot(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            result[str(p.relative_to(root))] = {'symlink': os.readlink(p)}
        elif p.is_file():
            data = p.read_bytes()
            result[str(p.relative_to(root))] = {'sha256': digest(data), 'mode': oct(p.stat().st_mode & 0o777), 'bytes': len(data)}
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True)
    ap.add_argument('--attempt', default='1')
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[3]
    out = Path(__file__).resolve().parent / (args.case + '-' + args.attempt)
    out.mkdir(exist_ok=False)
    fixture = Path('/private/tmp/pds-behavior-20260928') / out.name
    fixture.mkdir(parents=True, exist_ok=False)
    def git(*argv):
        return subprocess.check_output(['git', '-C', str(repo), *argv])
    cases = json.loads(git('show', args.commit + ':' + PREFIX + 'evals/behavior-cases.json'))
    case = next(c for c in cases['cases'] if c['id'] == args.case)
    for name, content in case['fixture_files'].items():
        p = fixture / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    skill_root = fixture / '.agents/skills/project-delivery-suite'
    skill_manifest = {}
    omitted = []
    paths = git('ls-tree', '-r', '--name-only', args.commit, '--', PREFIX).decode().splitlines()
    for path in paths:
        rel = path[len(PREFIX):]
        if any(rel.startswith(ex) for ex in EXCLUDE):
            omitted.append(rel)
            continue
        data = git('show', args.commit + ':' + path)
        target = skill_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        skill_manifest[rel] = digest(data)
    prompt = ('使用当前夹具内 .agents/skills/project-delivery-suite/SKILL.md 处理下面的用户请求。'
              '工作范围仅限当前目录；不得访问其他用户项目，不得调用外部服务。'
              '所需源文件和本地 Skill 均已提供。\n\n' + case['prompt'])
    (out / 'prompt.txt').write_text(prompt)
    save(out / 'input-files.json', case['fixture_files'])
    save(out / 'skill-manifest.json', {'commit': args.commit, 'included': skill_manifest, 'excluded_for_blinding': omitted})
    before = snapshot(fixture)
    save(out / 'before.json', before)
    snapshot_hash = digest(json.dumps(before, sort_keys=True, ensure_ascii=False).encode())
    runtime = Path('/Users/Shared/pds-eval-20260928') / out.name
    runtime.mkdir(parents=True, exist_ok=False, mode=0o700)
    auth_source = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json'
    shutil.copyfile(auth_source, runtime / 'auth.json')
    (runtime / 'auth.json').chmod(0o600)
    launcher = Path(shutil.which('codex')).resolve()
    candidates = list(launcher.parent.parent.glob('node_modules/@openai/*/vendor/*/bin/codex'))
    executable = str(candidates[0]) if len(candidates) == 1 else str(launcher)
    command = [executable, 'exec', '--ignore-user-config', '--json', '--color', 'never',
               '--skip-git-repo-check', '-C', str(fixture), '-s', 'danger-full-access',
               '-m', args.model, '-c', 'model_reasoning_effort="' + args.effort + '"',
               '-c', 'approval_policy="never"', '-c', 'web_search="disabled"',
               '-c', 'features.apps=false', '-c', 'features.multi_agent=false',
               '-c', 'mcp_servers={}', '-c', 'shell_environment_policy.inherit="core"',
               '-c', 'shell_environment_policy.set={PYTHONDONTWRITEBYTECODE="1",GIT_CONFIG_GLOBAL="/dev/null",GIT_CONFIG_NOSYSTEM="1"}', '-']
    for feature in ('plugins', 'remote_plugin', 'browser_use', 'browser_use_external', 'computer_use', 'in_app_browser', 'image_generation', 'hooks', 'shell_snapshot', 'skill_mcp_dependency_install', 'workspace_dependencies'):
        command[-1:-1] = ['-c', 'features.' + feature + '=false']
    started = time.time()
    timed_out = False
    with IsolatedTransport(fixture, runtime) as transport:
        (out / 'sandbox-profile.sb').write_text(transport.profile.replace(str(Path.home()), '$HOME'))
        with (out / 'raw-trace.jsonl').open('wb') as raw, (out / 'stderr.txt').open('wb') as err:
            process = subprocess.Popen(transport.prefix + command, stdin=subprocess.PIPE, stdout=raw, stderr=err, env=transport.env, cwd=fixture)
            try:
                process.communicate(prompt.encode(), timeout=600)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.terminate()
                process.communicate(timeout=20)
        save(out / 'network-decisions.json', transport.decisions)
    elapsed = time.time() - started
    (runtime / 'auth.json').unlink(missing_ok=True)
    rollouts = list(runtime.glob('sessions/**/*.jsonl'))
    if len(rollouts) == 1:
        shutil.copyfile(rollouts[0], out / 'full-rollout.jsonl')
    redactions = {}
    for log_name in ('raw-trace.jsonl', 'stderr.txt', *(['full-rollout.jsonl'] if (out / 'full-rollout.jsonl').exists() else [])):
        log = out / log_name
        original = log.read_bytes()
        sanitized = original.decode(errors='replace').replace(str(Path.home()), '$HOME')
        if log_name == 'stderr.txt':
            sanitized = re.sub(r'(https?://[^\s?()]+)\?[^\s()]+', r'\1?[QUERY_REDACTED]', sanitized)
        log.write_text(sanitized)
        redactions[log_name] = {'original_sha256': digest(original), 'published_sha256': digest(log.read_bytes()), 'changed': original != log.read_bytes()}
    save(out / 'redactions.json', {'rules': ['personal home prefix replaced with $HOME', 'stderr URL query strings removed'], 'logs': redactions})
    after = snapshot(fixture)
    save(out / 'after.json', after)
    changed = {name: {'before': before.get(name), 'after': after.get(name)}
               for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)}
    save(out / 'changes.json', changed)
    output_files = {}
    for name in after:
        if not name.startswith('.agents/'):
            p = fixture / name
            if p.is_file() and not p.is_symlink():
                output_files[name] = p.read_text(errors='replace')
    save(out / 'output-files.json', output_files)
    events = []
    for line in (out / 'raw-trace.jsonl').read_text().splitlines():
        try: events.append(json.loads(line))
        except ValueError: pass
    usage = [e.get('usage') for e in events if e.get('type') == 'turn.completed']
    save(out / 'collector.json', {
        'case_id': args.case, 'run_id': out.name, 'run_kind': 'actual_model' if any(e.get('type') == 'turn.completed' for e in events) else 'infrastructure_failure',
        'model': args.model, 'skill_commit': args.commit,
        'configuration': {'reasoning_effort': args.effort, 'tool_policy': 'Single OS sandbox restricts writes to fixture/isolated CLI runtime and denies home reads except CLI binaries; outbound network only local CONNECT proxy allowing chatgpt.com:443 for inference; no apps/MCP/web/multi-agent/approvals. CLI internal sandbox disabled to avoid unsupported nested seatbelt.', 'input_snapshot_sha256': snapshot_hash},
        'command': [x.replace(str(Path.home()), '$HOME') for x in command], 'fixture': str(fixture), 'duration_seconds': elapsed,
        'usage': usage, 'exit_code': process.returncode, 'timed_out': timed_out,
        'raw_trace': {'file': 'raw-trace.jsonl', 'sha256': digest((out / 'raw-trace.jsonl').read_bytes())},
        'cost_usd': None, 'full_rollout_retained': (out / 'full-rollout.jsonl').exists(), 'model_identity_note': 'Explicit CLI model selection; server-resolved model revision is not exposed in JSONL.',
    })
    print(json.dumps({'run': out.name, 'exit_code': process.returncode, 'seconds': elapsed, 'changes': list(changed), 'usage': usage}))

if __name__ == '__main__':
    main()
