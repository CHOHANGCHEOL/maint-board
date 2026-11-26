#!/usr/bin/env python3
"""정비실 현황판 정적 페이지 생성기.
data/*.json (CMS 조회 결과 + 대시보드 저장값)을 읽어 index.html 한 장을 만든다.
사용: python3 build.py  (data/ 폴더 기준, 결과는 index.html)
"""
import json, os, re, datetime, html

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
NAMES = ['prep_list', 'prep_parts', 'relist', 'materials', 'trend', 'returns_unreg', 'returns',
         'ret_summary', 'ret_model', 'boxes_m', 'crossbars_m', 'price', 'hidden', 'unreg_status']


def load(name):
    p = os.path.join(DATA, name + '.json')
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8') as f:
        d = json.load(f)
    if isinstance(d, dict):
        d = d.get('rows') or d.get('data') or []
    return d


def mask_client(name):
    """개인 고객 이름은 공개 페이지에서 가린다."""
    if not name:
        return name
    s = str(name)
    if s.endswith('_개인'):
        return '개인고객'
    return s


def main():
    data = {n: load(n) for n in NAMES}
    for key in ('prep_list', 'returns_unreg', 'returns'):
        for r in data[key]:
            r['client'] = mask_client(r.get('client'))
    for r in data['hidden']:
        r['client'] = mask_client(r.get('client'))
    kst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst)
    meta = {'updated': now.strftime('%Y-%m-%d %H:%M'), 'today': now.strftime('%Y-%m-%d'),
            'tomorrow': (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')}
    payload = json.dumps({'meta': meta, **data}, ensure_ascii=False).replace('<', '\\u003c')
    with open(os.path.join(BASE, 'template.html'), encoding='utf-8') as f:
        tpl = f.read()
    api = os.environ.get('MAINT_API_URL', '')
    cfg = os.path.join(BASE, 'config.json')
    if not api and os.path.exists(cfg):
        with open(cfg, encoding='utf-8') as f:
            api = json.load(f).get('api_url', '')
    if api and not re.match(r'^https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec$', api):
        raise SystemExit('config.json의 api_url 형식이 Apps Script 웹 앱 주소가 아닙니다: ' + api)
    out = tpl.replace("'__API_URL__'", json.dumps(api)).replace('/*__DATA__*/null', payload).replace('__UPDATED__', html.escape(meta['updated']))
    with open(os.path.join(BASE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(out)
    print('built index.html', meta['updated'], {k: len(v) for k, v in data.items()})


if __name__ == '__main__':
    main()
