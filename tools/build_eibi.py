#!/usr/bin/env python3
"""Build eibi.js (the schedule SW 1's "on now" list reads) from EiBi's season files.

Usage:  python3 tools/build_eibi.py a26      (season code: a26, b26, a27 ...)
Fetches sked-<season>.csv, freq-<season>.txt and README.TXT from http://www.eibispace.de/dx/
(or reads them from --dir if already downloaded) and writes eibi.js next to radio.html.

EiBi data: free to download, use, copy and distribute (see README.TXT, section A).
"""
import sys, re, json, os, datetime, urllib.request, argparse

BASE = 'http://www.eibispace.de/dx/'
ap = argparse.ArgumentParser()
ap.add_argument('season')
ap.add_argument('--dir', default=None, help='folder holding already-downloaded source files')
ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'eibi.js'))
a = ap.parse_args()
season = a.season.lower()

def get(name):
    if a.dir:
        return open(os.path.join(a.dir, name), 'rb').read().decode('latin-1')
    with urllib.request.urlopen(BASE + name, timeout=60) as r:
        return r.read().decode('latin-1')

sked = get('sked-%s.csv' % season).splitlines()
freq = get('freq-%s.txt' % season)
readme = get('README.TXT')

# season validity and last update, from the frequency list's header
m = re.search(r'Valid (\w+ \d+, \d{4}) - (\w+ \d+, \d{4})', freq)
d0, d1 = [datetime.datetime.strptime(x, '%B %d, %Y').date().isoformat() for x in m.groups()]
m = re.search(r'Last update: (\w+ \d+, \d{4})', freq)
updated = datetime.datetime.strptime(m.group(1), '%b %d, %Y').date().isoformat() if m else ''

# code tables from the README
start = readme.index('D) Codes used.')
iL = readme.index('   I) Language codes.', start + 200)
iC = readme.index('   II) Country codes.', iL)
iT = readme.index('   III) Target-area codes.', iC)
lang = {}
for line in readme[iL:iC].splitlines():
    mm = re.match(r'^   (\S{1,3})\s{2,}(.+)$', line)
    if not mm: continue
    name = re.sub(r'\s*\[[^\]]*\]\s*$', '', mm.group(2))
    name = re.split(r':| \(', name)[0].strip()
    lang[mm.group(1)] = name
itu = {}
for line in readme[iC:iT].splitlines():
    mm = re.match(r'^   ([A-Z0-9]{1,3})\s{2,}(.+)$', line)
    if mm: itu[mm.group(1)] = re.split(r' \(', re.sub(r'\s*\*$', '', mm.group(2)))[0].strip()
itu['G'] = 'United Kingdom'

rows = []
for line in sked[1:]:
    p = line.split(';')
    if len(p) != 11: continue
    try:
        f = float(p[0]); t0, t1 = [int(x) for x in p[1].split('-')]; pc = int(p[8] or 0)
    except ValueError:
        continue
    if pc % 10 == 8: continue                      # inactive entry
    sd = p[9].strip() if re.match(r'^\d{4}$', p[9].strip()) else ''
    ed = re.sub(r'\[.*?\]', '', p[10]).strip()
    ed = ed if re.match(r'^\d{4}$', ed) else ''
    rows.append([int(f) if f == int(f) else f, t0, t1, p[2].strip(), p[3].strip(), p[4].strip(), p[5].strip(), p[6].strip(), pc, sd, ed])

used_l = {r[6] for r in rows}; used_c = {r[4] for r in rows} | {r[7] for r in rows}
out = {
    'season': season.upper(), 'from': d0, 'to': d1, 'updated': updated, 'built': datetime.date.today().isoformat(),
    'lang': {k: v for k, v in lang.items() if k in used_l},
    'itu': {k: v for k, v in itu.items() if k in used_c},
    'rows': rows,
}
with open(a.out, 'w', encoding='utf-8') as fh:
    fh.write('// EiBi shortwave schedule %s (eibispace.de), free to copy and distribute. Built by tools/build_eibi.py.\n' % season.upper())
    fh.write('window.EIBI=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('season %s  valid %s to %s  updated %s  rows %d  languages %d  countries %d  -> %s (%d bytes)' % (
    season.upper(), d0, d1, updated, len(rows), len(out['lang']), len(out['itu']), a.out, os.path.getsize(a.out)))
