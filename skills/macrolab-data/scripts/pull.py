#!/usr/bin/env python3
"""Pull the Macro Lab open data (macrolab.kr) into a local cache, downloading only what changed.

    MACROLAB_TOKEN=<key> python3 pull.py        # → ./.macrolab/ (or $MACROLAB_CACHE, or --dir)
    python3 pull.py --check                     # report what would change, download nothing
    python3 pull.py --dir ~/.cache/macrolab --base https://macrolab.kr --token <key>

The data is for Macro Lab members (2026-11-08): sign in at https://macrolab.kr, press 「AI 연결」 in the header and make a 연결 키 (a bearer
token, valid a year); pass it as MACROLAB_TOKEN or --token. Standard library only (Python >= 3.8). Reads <base>/data/manifest.json, compares
each file's sha256 with the cached copy, fetches changed files from their immutable versioned URLs, verifies them, writes atomically and keeps
manifest.json beside the files. Exit code 0 when the cache is complete, 1 on a network, authorization, verification or write failure.
Its own messages are ASCII, and stdout replaces what its encoding cannot show (a path, an OS message) with '?': on Korean Windows a pipe - the
way an AI agent runs this - is cp949, where a character it cannot encode used to stop the run before anything was downloaded (2026-11-08).
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = 'https://macrolab.kr'
UA = 'macrolab-pull/1.1 (+https://macrolab.kr/ai.html)'
SAFE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z')   # panel.csv, dictionary.json, daily.csv - never a path, a drive (C:x) or a dot file


def file_url(base, url):
    """A file's URL on the server being pulled: the manifest names its own origin, so `--base` (a mirror, a local server) keeps the path only."""
    p = urllib.parse.urlsplit(url)
    return base + p.path if p.scheme and p.netloc != urllib.parse.urlsplit(base).netloc else url


TOKEN = ''


def fetch(url, timeout=60):
    headers = {'User-Agent': UA, 'Accept-Encoding': 'gzip'}
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if (r.headers.get('Content-Encoding') or '').lower() == 'gzip':
            data = gzip.decompress(data)
        return data


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_atomic(path, data):
    d = os.path.dirname(path) or '.'
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.pull-')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.chmod(tmp, 0o644)   # mkstemp makes 0600; a data cache is read by other tools too
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    try:   # never die on a character the console or pipe cannot encode (stderr already escapes it)
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):   # stdout replaced by a host, or none (pythonw)
        pass
    ap = argparse.ArgumentParser(description='Pull the Macro Lab open data into a local cache.')
    ap.add_argument('--dir', default=os.environ.get('MACROLAB_CACHE') or os.path.join('.', '.macrolab'), help='cache folder (default ./.macrolab or $MACROLAB_CACHE)')
    ap.add_argument('--base', default=os.environ.get('MACROLAB_BASE') or DEFAULT_BASE, help='server (default https://macrolab.kr)')
    ap.add_argument('--check', action='store_true', help='report what would change; download nothing')
    ap.add_argument('--token', default=os.environ.get('MACROLAB_TOKEN') or '', help='your Macro Lab connection key (default $MACROLAB_TOKEN)')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    global TOKEN
    TOKEN = a.token.strip()
    base = a.base.rstrip('/')
    out = os.path.abspath(os.path.expanduser(a.dir))
    say = (lambda *x: None) if a.quiet else (lambda *x: print(*x))

    try:
        manifest = json.loads(fetch(base + '/data/manifest.json').decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 401:   # members only: no key, or an expired one
            print('%s asks for a member key: sign in at %s, press "Connect AI" (AI 연결) in the header, make a connection key and pass it as MACROLAB_TOKEN (or --token)' % (base, base), file=sys.stderr)
        else:
            print('could not read %s/data/manifest.json: %s' % (base, e), file=sys.stderr)
        return 1
    except Exception as e:   # a network error, a timeout, a cut-off body or bad JSON: say which and stop
        print('could not read %s/data/manifest.json: %s' % (base, e), file=sys.stderr)
        return 1
    files = [f for f in (manifest.get('files') if isinstance(manifest, dict) else None) or [] if isinstance(f, dict)]
    if not files:
        print('the manifest lists no files', file=sys.stderr)
        return 1

    try:
        os.makedirs(out, exist_ok=True)
        gi = os.path.join(out, '.gitignore')
        if not os.path.exists(gi):
            write_atomic(gi, b'*\n')   # a data cache is never committed
    except OSError as e:
        print('could not use the cache folder %s: %s' % (out, e), file=sys.stderr)
        return 1

    changed, same, failed = [], [], []
    for f in files:
        name, want = f.get('name'), f.get('sha256')
        if not isinstance(name, str) or not SAFE_NAME.match(name) or not f.get('url'):
            continue
        path = os.path.join(out, name)
        if os.path.isfile(path) and want and sha256_of(path) == want:
            same.append(name)
            continue
        changed.append(f)
    say('Macro Lab open data %s - panel %s..%s (%s months, %s series), daily series %s' % (
        manifest.get('version'), manifest.get('panel_first'), manifest.get('panel_last'), manifest.get('panel_months'), manifest.get('variables'), manifest.get('daily_series')))
    if a.check:
        say('up to date: %s' % (', '.join(same) or 'none'))
        say('would download: %s' % (', '.join('%s (%s bytes)' % (f['name'], f.get('bytes')) for f in changed) or 'nothing'))
        return 0
    for f in changed:
        name, url, want = f['name'], file_url(base, f['url']), f.get('sha256')
        try:
            data = fetch(url)
        except Exception as e:
            failed.append('%s: %s' % (name, e)); continue
        got = hashlib.sha256(data).hexdigest()
        if want and got != want:
            failed.append('%s: sha256 mismatch (manifest %s, downloaded %s); the snapshot may have changed, run again' % (name, want[:12], got[:12])); continue
        try:
            write_atomic(os.path.join(out, name), data)
        except OSError as e:   # on Windows a file open in another program (Excel) cannot be replaced
            failed.append('%s: could not write it (%s); close it if another program has it open, then run again' % (name, e)); continue
        say('downloaded %-16s %8d bytes  %s' % (name, len(data), url))
    if not failed:
        try:
            write_atomic(os.path.join(out, 'manifest.json'), json.dumps(manifest, ensure_ascii=False, indent=1).encode('utf-8'))
        except OSError as e:
            failed.append('manifest.json: could not write it (%s)' % e)
    say('cache: %s' % out)
    for name in same:
        say('unchanged  %s' % name)
    for msg in failed:
        print('FAILED %s' % msg, file=sys.stderr)
    if failed:
        return 1
    say('files: ' + ', '.join(sorted(n for n in os.listdir(out) if not n.startswith('.'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
