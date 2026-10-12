#!/usr/bin/env python3
"""Convert Albanian laws fetched by al_fetch.py (QBZ PDFs) to Markdown.

Usage: al_convert.py RAW_DIR OUT_DIR
"""
import datetime, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from al_textmd import structure, pdftotext

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()


def slug(s, n=70):
    s = unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:n].rstrip('-')


def yq(s):
    return '"' + re.sub(r'\s+', ' ', s).strip().replace('\\', '\\\\').replace('"', '\\"') + '"'


def d10(s):
    return (s or '')[:10] or None


def pdf_md(nid):
    fn = os.path.join(RAW, 'pdf', nid + '.pdf')
    if not os.path.exists(fn):
        return None
    t = pdftotext(fn)
    if len(t.strip()) < 200:
        return None
    return structure(t)


def main():
    acts = json.load(open(os.path.join(RAW, 'acts.json')))
    base = [a for a in acts if a.get('properties', {}).get('qbz:actType') == 'Akt bazë']
    counts, skipped = {}, {'repealed': 0, 'notext': 0}
    for a in base:
        p = a['properties']
        m = json.load(open(os.path.join(RAW, 'meta', a['id'] + '.json')))
        repealers = [s for s in m['sources'] if s['association']['assocType'] == 'qbz:actRepeals']
        if repealers:
            skipped['repealed'] += 1
            continue
        vers = [s for s in m['sources'] if s['nodeType'] == 'qbz:actVersion' and s['association']['assocType'] == 'qbz:baseAct']
        main_md, version, vdate, vurl = None, 'original', '', None
        if vers:
            v = max(vers, key=lambda s: (s.get('properties', {}).get('qbz:publishDate', ''), s.get('modifiedAt', '')))
            main_md = pdf_md(v['id'])
            if main_md:
                version = 'consolidated'
                vdate = v.get('properties', {}).get('qbz:publishDate', '')
                vurl = v.get('properties', {}).get('qbz:url')
        if not main_md:
            main_md = pdf_md(a['id'])
            vdate = ''
        if not main_md:
            skipped['notext'] += 1
            continue
        amend = sorted([s for s in m['sources'] if s['association']['assocType'] == 'qbz:actChanges' and s['nodeType'] == 'qbz:act'],
                       key=lambda s: s.get('properties', {}).get('qbz:publishDate', ''))
        later = [s for s in amend if s.get('properties', {}).get('qbz:publishDate', '') > vdate]
        appended = []
        for s in later:
            t = pdf_md(s['id'])
            if t:
                sp = s.get('properties', {})
                appended.append((sp, t))
        url = p.get('qbz:url', '')
        m2 = re.search(r'/eli/ligj/(\d{4})/(\d{2})/(\d{2})/([^/]+)$', url)
        y, mo, dd, num = (m2.groups() if m2 else ((p.get('qbz:actDate') or '0000')[:4], '00', '00', p.get('qbz:actNumber', '')))
        title = re.sub(r'\s+', ' ', p.get('qbz:actTitle', '')).strip()
        ident = 'Ligj nr. %s, datë %s.%s.%s' % (num, dd, mo, y)
        t_up = title.upper()
        if num == '8417' and y == '1998':
            sub, typ = 'kushtetuta', 'constitution'
        elif t_up.startswith('KODI') or re.match(r'^PËR KODIN\b', t_up):
            sub, typ = 'kode', 'code'
        else:
            sub, typ = 'ligje/%s' % y, 'act'
        fn = '%s-%s-%s-%s-%s.md' % (y, mo, dd, slug(num, 15), slug(title, 70))
        path = os.path.join(OUT, sub, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        last = d10(vdate) if version == 'consolidated' else None
        if appended:
            last = d10(appended[-1][0].get('qbz:publishDate')) or last
        fm = ['---', 'title: ' + yq(title), 'identifier: ' + yq(ident), 'eli: ' + yq(url), 'type: ' + typ,
              'jurisdiction: al', 'language: sq', 'date: %s-%s-%s' % (y, mo, dd)]
        if last:
            fm.append('last_amended: ' + last)
        fm += ['status: in_force', 'text_version: ' + version + ('_with_later_amendments' if appended else ''),
               'official_journal: ' + yq('Fletorja Zyrtare nr. %s/%s' % (p.get('qbz:actOfficialJournalNr', ''), (p.get('qbz:actOfficialJournalDate') or '')[:4])),
               'source: ' + yq(url.replace('http://', 'https://'))]
        if vurl:
            fm.append('consolidated_version: ' + yq(vurl.replace('http://', 'https://')))
        fm += ['retrieved: ' + TODAY, '---']
        body = main_md
        if appended:
            body += '\n\n## Ndryshime të mëvonshme (tekste të plota të akteve ndryshuese)\n'
            for sp, t in appended:
                head = 'Ligj nr. %s — %s' % (sp.get('qbz:actNumber', ''), re.sub(r'\s+', ' ', sp.get('qbz:actTitle', '')))
                body += '\n\n### %s\n\n*%s*\n\n%s' % (head, sp.get('qbz:url', '').replace('http://', 'https://'),
                                                    re.sub(r'^(#{3,5}) ', lambda mm: '#' * min(len(mm.group(1)) + 1, 6) + ' ', t, flags=re.M))
        open(path, 'w').write('\n'.join(fm) + '\n\n# ' + ident + ' — ' + title + '\n\n' + body + '\n')
        counts[(typ, version, bool(appended))] = counts.get((typ, version, bool(appended)), 0) + 1
    print(skipped, file=sys.stderr)
    for k, v in sorted(counts.items()):
        print(k, v, file=sys.stderr)


if __name__ == '__main__':
    main()
