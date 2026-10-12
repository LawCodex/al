#!/usr/bin/env python3
"""Fetch Albanian laws from the official Qendra e Botimeve Zyrtare (QBZ, https://qbz.gov.al).

QBZ runs on Alfresco; its public REST API is readable anonymously (that is what the qbz.gov.al
web app itself uses).  Steps:
  1. search all acts of document-type `ligj` (laws, incl. codes and the constitution) year by year
  2. for every act, read its associations (sources/targets): amendments (qbz:actChanges),
     repeals (qbz:actRepeals), consolidated versions (qbz:actVersion via qbz:baseAct)
  3. download the PDF of the latest official consolidated version ("tekst i konsoliduar /
     i përditësuar") or, if none, the original act plus its amending acts.
Everything is cached under RAW_DIR (default ../../_raw/al).
"""
import json, os, sys, time
import requests
from concurrent.futures import ThreadPoolExecutor

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_raw', 'al')
UA = 'LawCodex/1.0 (+https://github.com/LawCodex)'
API = 'https://qbz.gov.al/alfresco/api/-default-/public'
NODES = API + '/alfresco/versions/1/nodes/'
SEARCH = API + '/search/versions/1/search'
S = requests.Session(); S.headers['User-Agent'] = UA
DELAY = 0.5


def req(method, url, **kw):
    for i in range(6):
        try:
            r = S.request(method, url, timeout=180, **kw)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.RequestException('HTTP %d' % r.status_code)
            time.sleep(DELAY)
            return r
        except requests.RequestException as e:
            w = 5 * 2 ** i
            print('  retry', url, e, 'wait', w, file=sys.stderr, flush=True); time.sleep(w)
    raise SystemExit('giving up on ' + url)


def search_year(y, doctype='ligj'):
    out, skip = [], 0
    q = ('TYPE:"qbz:act" AND =qbz:actActType:"http://qbz.gov.al/resource/authority/document-type/%s" '
         'AND qbz:actDate:["%d-01-01T00:00:00" TO "%d-12-31T23:59:59"]' % (doctype, y - 1 if False else y, y))
    while True:
        body = {'query': {'query': q, 'language': 'afts'}, 'paging': {'maxItems': 100, 'skipCount': skip},
                'include': ['properties', 'path'], 'sort': [{'type': 'FIELD', 'field': 'cm:created', 'ascending': True}]}
        d = req('POST', SEARCH, json=body).json()['list']
        out += [e['entry'] for e in d['entries']]
        if not d['pagination']['hasMoreItems']:
            return out
        skip += 100


def assocs(nid, kind, where=None):
    out, skip = [], 0
    while True:
        params = {'maxItems': 100, 'skipCount': skip, 'include': 'properties'}
        if where:
            params['where'] = "(assocType='%s')" % where
        d = req('GET', NODES + nid + '/' + kind, params=params).json()['list']
        out += [e['entry'] for e in d['entries']]
        if not d['pagination']['hasMoreItems']:
            return out
        skip += 100


def download(nid, fn):
    if os.path.exists(fn):
        return
    r = req('GET', NODES + nid + '/content')
    if r.status_code == 200:
        open(fn + '.tmp', 'wb').write(r.content); os.replace(fn + '.tmp', fn)
    else:
        print('download failed', nid, r.status_code, file=sys.stderr)


def main():
    os.makedirs(RAW + '/meta', exist_ok=True); os.makedirs(RAW + '/pdf', exist_ok=True)
    idx = RAW + '/acts.json'
    if os.path.exists(idx):
        acts = json.load(open(idx))
    else:
        acts = []
        for y in range(1900, time.gmtime().tm_year + 1):
            a = search_year(y)
            if a:
                print(y, len(a), file=sys.stderr, flush=True)
            acts += a
        # acts without a date
        json.dump(acts, open(idx, 'w'), ensure_ascii=False)
    print(len(acts), 'laws in index', file=sys.stderr, flush=True)
    base = [a for a in acts if a.get('properties', {}).get('qbz:actType') == 'Akt bazë']
    print(len(base), 'base acts', file=sys.stderr, flush=True)

    def meta(a):
        fn = RAW + '/meta/' + a['id'] + '.json'
        if not os.path.exists(fn):
            # only the association types we use (some acts, e.g. the Constitution, have >10,000 'actBasedOn' sources)
            m = {'sources': [x for t in ('qbz:baseAct', 'qbz:actChanges', 'qbz:actRepeals') for x in assocs(a['id'], 'sources', t)],
                 'targets': assocs(a['id'], 'targets')}
            json.dump(m, open(fn + '.tmp', 'w'), ensure_ascii=False); os.replace(fn + '.tmp', fn)
    with ThreadPoolExecutor(3) as ex:
        for n, _ in enumerate(ex.map(meta, base)):
            if n % 200 == 0:
                print('meta', n, file=sys.stderr, flush=True)
    # downloads
    todo = []
    for n, a in enumerate(base):
        m = json.load(open(RAW + '/meta/' + a['id'] + '.json'))
        if any(s['association']['assocType'] == 'qbz:actRepeals' for s in m['sources']):
            continue
        vers = [s for s in m['sources'] if s['nodeType'] == 'qbz:actVersion' and s['association']['assocType'] == 'qbz:baseAct']
        if vers:
            v = max(vers, key=lambda s: (s.get('properties', {}).get('qbz:publishDate', ''), s.get('modifiedAt', '')))
            todo.append(v['id'])
            vdate = v.get('properties', {}).get('qbz:publishDate', '')
        else:
            vdate = ''
        todo.append(a['id'])
        for s in m['sources']:
            if s['association']['assocType'] == 'qbz:actChanges' and s['nodeType'] == 'qbz:act':
                sp = s.get('properties', {})
                if sp.get('qbz:publishDate', '') > vdate:
                    todo.append(s['id'])
    print(len(todo), 'files to download', file=sys.stderr, flush=True)
    with ThreadPoolExecutor(3) as ex:
        for n, _ in enumerate(ex.map(lambda i: download(i, RAW + '/pdf/' + i + '.pdf'), todo)):
            if n % 200 == 0:
                print('dl', n, file=sys.stderr, flush=True)
    print('done', file=sys.stderr)


if __name__ == '__main__':
    main()
