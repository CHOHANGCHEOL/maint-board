#!/usr/bin/env python3
"""정비실 현황판 데이터 갱신기.

data/*.json (CMS 조회 결과)을 읽어 저장소 루트 index.html 안의
`const D = {...};` 한 줄만 새 데이터로 바꾼다. 페이지 디자인·기능은 그대로 둔다.

- data/에 없는 데이터셋은 기존 index.html 값을 유지한다.
  (price / hidden / unreg_status 는 페이지가 Apps Script에서 실시간으로 읽으므로 보통 그대로 둔다.)
- 공개 페이지이므로 개인 고객명(`..._개인`)은 모든 데이터셋에서 "개인고객"으로 가린다.
- 데이터 내용이 이전과 같으면 파일을 건드리지 않는다(갱신 시각만 바뀌는 커밋 방지).

사용: python3 build.py            → 바뀌었으면 "changed", 아니면 "unchanged" 출력
      python3 build.py --force    → 내용이 같아도 갱신 시각을 새로 씀
"""
import copy
import datetime
import html
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
PAGE = os.path.join(os.path.dirname(BASE), 'index.html')
CMS_NAMES = ['prep_list', 'prep_parts', 'relist', 'materials', 'trend', 'returns_unreg', 'returns',
             'ret_summary', 'ret_model', 'boxes_m', 'crossbars_m']
EDIT_NAMES = ['price', 'hidden', 'unreg_status']
D_LINE = re.compile(r'^const D = (.*);$', re.M)
UPD_SPAN = re.compile(r'(<span id="upd">)[^<]*(</span>)')


def load(name):
    p = os.path.join(DATA, name + '.json')
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        d = json.load(f)
    if isinstance(d, dict):
        d = d.get('rows') or d.get('data') or []
    if not isinstance(d, list):
        raise SystemExit(f'{name}.json 형식 오류: 리스트가 아님')
    return d


def mask(rows):
    for r in rows:
        if isinstance(r, dict) and str(r.get('client') or '').endswith('_개인'):
            r['client'] = '개인고객'
    return rows


def main():
    force = '--force' in sys.argv
    with open(PAGE, encoding='utf-8') as f:
        page = f.read()
    m = D_LINE.search(page)
    if not m:
        raise SystemExit('index.html에서 `const D = ...;` 줄을 찾지 못했습니다.')
    old = json.loads(m.group(1))

    new = copy.deepcopy({k: v for k, v in old.items() if k != "meta"})
    loaded = {}
    for n in CMS_NAMES + EDIT_NAMES:
        rows = load(n)
        if rows is not None:
            new[n] = rows
            loaded[n] = len(rows)
    for k, v in new.items():
        if isinstance(v, list):
            mask(v)

    old_body = {k: v for k, v in old.items() if k != 'meta'}
    if new == old_body and not force:
        print('unchanged', loaded)
        return

    kst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst)
    meta = {'updated': now.strftime('%Y-%m-%d %H:%M'), 'today': now.strftime('%Y-%m-%d'),
            'tomorrow': (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')}
    payload = json.dumps({'meta': meta, **new}, ensure_ascii=False).replace('<', '\\u003c')
    page = page[:m.start(1)] + payload + page[m.end(1):]
    page = UPD_SPAN.sub(lambda x: x.group(1) + html.escape(meta['updated']) + x.group(2), page, count=1)
    with open(PAGE, 'w', encoding='utf-8') as f:
        f.write(page)
    print('changed', meta['updated'], loaded)


if __name__ == '__main__':
    main()
