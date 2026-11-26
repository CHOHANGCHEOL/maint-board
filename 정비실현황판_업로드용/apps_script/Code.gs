/**
 * 정비실 현황판 — 수정 내용 저장소 (Google Apps Script 웹 앱)
 *
 * 저장하는 것: 매물 미등록 차량 상태값, 숨긴(삭제) 차량, 부품·공임 단가, 변경 기록
 * 저장하지 않는 것: CMS 접속 정보 (CMS 데이터는 GitHub 예약 작업이 따로 갱신)
 *
 * 설치: README의 "Apps Script 배포" 순서를 따르세요.
 */

const SHEETS = {
  status: ['id', 'plate', 'status', 'updated_at'],
  hidden: ['detail_id', 'plate', 'client', 'model', 'hidden_at'],
  price: ['id', 'model', 'part', 'price', 'labor', 'sort', 'updated_at'],
  log: ['time', 'action', 'detail'],
};
const STATUS_VALUES = ['입고예정', '작업대기', '작업중'];

function sheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, SHEETS[name].length).setValues([SHEETS[name]]);
    sh.setFrozenRows(1);
  }
  return sh;
}

function rows_(name) {
  const sh = sheet_(name);
  const last = sh.getLastRow();
  if (last < 2) return [];
  const head = SHEETS[name];
  return sh.getRange(2, 1, last - 1, head.length).getValues().map((r) => {
    const o = {};
    head.forEach((h, i) => { o[h] = r[i] instanceof Date ? Utilities.formatDate(r[i], 'Asia/Seoul', 'yyyy-MM-dd HH:mm') : r[i]; });
    return o;
  });
}

function findRow_(name, key, value) {
  const sh = sheet_(name);
  const last = sh.getLastRow();
  if (last < 2) return -1;
  const col = SHEETS[name].indexOf(key) + 1;
  const vals = sh.getRange(2, col, last - 1, 1).getValues();
  for (let i = 0; i < vals.length; i++) if (String(vals[i][0]) === String(value)) return i + 2;
  return -1;
}

function upsert_(name, key, obj) {
  const sh = sheet_(name);
  const head = SHEETS[name];
  const row = head.map((h) => (obj[h] === undefined || obj[h] === null ? '' : obj[h]));
  const at = findRow_(name, key, obj[key]);
  if (at > 0) sh.getRange(at, 1, 1, head.length).setValues([row]);
  else sh.appendRow(row);
}

function remove_(name, key, value) {
  const at = findRow_(name, key, value);
  if (at > 0) sheet_(name).deleteRow(at);
}

function log_(action, detail) {
  sheet_('log').appendRow([now_(), action, JSON.stringify(detail).slice(0, 500)]);
}

function now_() { return Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm'); }

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function all_() {
  return {
    ok: true,
    status: rows_('status').map((r) => ({ id: String(r.id), status: r.status, plate: r.plate, updated_at: r.updated_at })),
    hidden: rows_('hidden').map((r) => ({ ...r, detail_id: String(r.detail_id) })),
    price: rows_('price').map((r) => ({ ...r, price: r.price === '' ? null : Number(r.price), labor: r.labor === '' ? null : Number(r.labor), sort: Number(r.sort) || 0 })),
  };
}

function doGet() {
  return out_(all_());
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const b = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const t = now_();
    switch (b.action) {
      case 'status': {
        if (STATUS_VALUES.indexOf(b.status) < 0) return out_({ ok: false, error: '허용되지 않는 상태값' });
        upsert_('status', 'id', { id: String(b.id), plate: b.plate || '', status: b.status, updated_at: t });
        log_('상태 변경', { id: b.id, plate: b.plate, status: b.status });
        break;
      }
      case 'hide': {
        upsert_('hidden', 'detail_id', { detail_id: String(b.detail_id), plate: b.plate || '', client: b.client || '', model: b.model || '', hidden_at: t });
        log_('차량 삭제(숨김)', { detail_id: b.detail_id, plate: b.plate });
        break;
      }
      case 'unhide': {
        remove_('hidden', 'detail_id', String(b.detail_id));
        log_('차량 복원', { detail_id: b.detail_id, plate: b.plate });
        break;
      }
      case 'price': {
        const num = (v) => (v === '' || v === null || v === undefined || isNaN(Number(v)) ? '' : Math.round(Number(v)));
        const at = findRow_('price', 'id', b.id);
        if (at < 0) return out_({ ok: false, error: '없는 단가 항목' });
        const cur = rows_('price').find((r) => String(r.id) === String(b.id));
        upsert_('price', 'id', { ...cur, price: num(b.price), labor: num(b.labor), updated_at: t });
        log_('단가 수정', { id: b.id, part: cur.part, model: cur.model, price: b.price, labor: b.labor });
        break;
      }
      case 'seed': {
        // 처음 한 번만: 시트가 비어 있을 때 페이지에 들어 있는 초기값을 채운다.
        if (rows_('price').length === 0 && Array.isArray(b.price)) {
          const sh = sheet_('price');
          const vals = b.price.slice(0, 1000).map((p) => [p.id, p.model, p.part, p.price == null ? '' : p.price, p.labor == null ? '' : p.labor, p.sort || 0, t]);
          if (vals.length) sh.getRange(2, 1, vals.length, SHEETS.price.length).setValues(vals);
        }
        if (rows_('status').length === 0 && Array.isArray(b.status)) {
          b.status.forEach((s) => { if (STATUS_VALUES.indexOf(s.status) >= 0) upsert_('status', 'id', { id: String(s.id), plate: s.plate || '', status: s.status, updated_at: t }); });
        }
        if (rows_('hidden').length === 0 && Array.isArray(b.hidden)) {
          b.hidden.forEach((h) => upsert_('hidden', 'detail_id', { detail_id: String(h.detail_id), plate: h.plate || '', client: h.client || '', model: h.model || '', hidden_at: t }));
        }
        log_('초기값 채움', { price: (b.price || []).length });
        break;
      }
      default:
        return out_({ ok: false, error: '알 수 없는 요청' });
    }
    return out_(all_());
  } catch (err) {
    return out_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
