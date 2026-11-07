(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CommercialMapCore = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const STATUSES = Object.freeze(['尚未拜訪', '洽談中', '已拜訪']);
  const BACKUP_KIND = 'commercial-tax-visit-backup';
  const MAX_BACKUP_BYTES = 1024 * 1024;
  const MAX_STATUS_RECORDS = 20000;
  const MAX_EXPORT_ROWS = 100000;
  const DEFAULT_CAPITAL = 'MIN_10M';
  const SOURCE_COLUMNS = ['address', 'tax_id', 'head_office_tax_id', 'name', 'capital', 'established',
    'organization', 'invoice', 'industry_code', 'industry_name', 'industry_code_1', 'industry_name_1',
    'industry_code_2', 'industry_name_2', 'industry_code_3', 'industry_name_3', 'district_id'];
  const CSV_HEADERS = ['營業地址', '統一編號', '總機構統一編號', '營業人名稱', '資本額（元）', '設立日期（來源原值）',
    '組織別', '使用統一發票', '行業代號', '行業名稱', '行業代號1', '行業名稱1', '行業代號2', '行業名稱2', '行業代號3', '行業名稱3',
    '拜訪紀錄', '證券市場', '股票代號', '上市櫃公司總機', '董事長', '公司網站（來源原值）', '公司網站連結', '上市櫃資訊來源', '稅籍來源', '來源快照日期'];

  function isRecord(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
  }

  function normalizeText(value) { return String(value ?? '').normalize('NFKC').toLocaleLowerCase().replace(/臺/g, '台').replace(/\s+/g, ''); }
  function companyId(taxId) { return /^\d{8}$/.test(String(taxId)) ? `tax_${taxId}` : null; }

  function validateStatuses(value) {
    if (!isRecord(value) || Object.keys(value).length > MAX_STATUS_RECORDS) throw new Error('紀錄格式不正確，或超過 20,000 筆備份上限。');
    const result = Object.create(null);
    for (const [id, status] of Object.entries(value)) {
      if (!/^tax_\d{8}$/.test(id) || !STATUSES.includes(status)) throw new Error('紀錄包含不合法統編或狀態；未匯入任何資料。');
      result[id] = status;
    }
    return result;
  }

  function validateBackup(value) {
    const fields = ['schema_version', 'kind', 'dataset_version', 'exported_at', 'statuses'];
    if (!isRecord(value) || Object.keys(value).length !== fields.length
      || fields.some(key => !Object.hasOwn(value, key)) || value.schema_version !== 1 || value.kind !== BACKUP_KIND
      || typeof value.dataset_version !== 'string' || !/^[a-f0-9]{64}$/.test(value.dataset_version)
      || typeof value.exported_at !== 'string' || !Number.isFinite(Date.parse(value.exported_at))) {
      throw new Error('不是正式稅籍資料版的紀錄備份；示範版紀錄不可匯入。');
    }
    return validateStatuses(value.statuses);
  }

  function loadStoredStatuses(raw) {
    if (raw === null) return Object.create(null);
    const value = JSON.parse(raw);
    if (!isRecord(value) || value.schema_version !== 1 || value.kind !== BACKUP_KIND || Object.keys(value).length !== 3) {
      throw new Error('正式拜訪紀錄格式無法辨識');
    }
    return validateStatuses(value.statuses);
  }

  function mergeStatuses(current, incoming) {
    return validateStatuses(Object.assign(Object.create(null), validateStatuses(current), validateStatuses(incoming)));
  }

  function csvCell(value) {
    let text = String(value ?? '');
    if (/^[\s\u0000-\u001f]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function csvLine(row) { return row.map(csvCell).join(',') + '\r\n'; }
  function csvDocument(rows) { return '\uFEFF' + rows.map(csvLine).join(''); }

  function safeURL(value) {
    if (typeof value !== 'string' || !/^https?:\/\//i.test(value.trim())) return null;
    try {
      const url = new URL(value.trim());
      return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
    } catch (_) { return null; }
  }

  function phoneURL(value) {
    const phone = String(value || '').normalize('NFKC').trim();
    return /^[+\d\s()-]{6,30}$/.test(phone) && /\d{2}/.test(phone.replace(/\D/g, ''))
      ? 'tel:' + phone.replace(/[\s()-]/g, '') : null;
  }

  function capitalTier(value) {
    const text = String(value ?? '').trim();
    if (!/^\d+(?:\.\d+)?$/.test(text)) return 'UNKNOWN';
    const capital = Number(text);
    if (capital >= 100000000) return 'TIER_100M';
    if (capital >= 30000000) return 'TIER_30M';
    if (capital >= 5000000) return 'TIER_5M';
    return 'TIER_UNDER_5M';
  }

  function formatCapital(value) {
    if (capitalTier(value) === 'UNKNOWN') return '來源未提供';
    return Number(value).toLocaleString('zh-TW') + ' 元';
  }

  function formatEstablished(value) {
    const text = String(value ?? '').trim();
    if (!/^\d{7}$/.test(text)) return text || '來源未提供';
    const year = Number(text.slice(0, 3)) + 1911, month = Number(text.slice(3, 5)), day = Number(text.slice(5, 7));
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
      ? `${year}-${text.slice(3, 5)}-${text.slice(5, 7)}` : text;
  }

  function matchesRow(row, filters, statuses, enrichment, ignoreStatus = false) {
    if (filters.district !== 'all' && row[16] !== filters.district) return false;
    if (filters.category !== 'ALL' && (String(row[8] || '').slice(0, 2) || 'UNKNOWN') !== filters.category) return false;
    if (filters.capital === 'MIN_10M') {
      if (capitalTier(row[4]) === 'UNKNOWN' || Number(row[4]) < 10000000) return false;
    } else if (filters.capital !== 'ALL' && capitalTier(row[4]) !== filters.capital) return false;
    if (filters.address && row[0] !== filters.address) return false;
    const info = enrichment[String(row[1])] || {};
    if (!ignoreStatus && filters.status !== 'ALL') {
      if (filters.status === 'LISTED' ? !['上市', '上櫃'].includes(info.market)
        : (statuses[companyId(row[1])] || STATUSES[0]) !== filters.status) return false;
    }
    const query = normalizeText(filters.query);
    return !query || [row[0], row[1], row[2], row[3], row[9], row[11], row[13], row[15], info.stock_code, info.chairperson]
      .some(value => normalizeText(value).includes(query));
  }

  function exportRow(row, statuses, catalog) {
    const info = catalog.enrichment[String(row[1])] || {};
    return [...row.slice(0, 16), statuses[companyId(row[1])] || STATUSES[0], info.market || '', info.stock_code || '',
      info.phone || '', info.chairperson || '', info.website_raw || info.website || '', safeURL(info.website) || '', safeURL(info.source_url) || '',
      catalog.source.url, catalog.source.source_date || catalog.source.last_modified || ''];
  }

  return { STATUSES, BACKUP_KIND, MAX_BACKUP_BYTES, MAX_STATUS_RECORDS, MAX_EXPORT_ROWS, DEFAULT_CAPITAL, SOURCE_COLUMNS, CSV_HEADERS,
    isRecord, normalizeText, companyId, validateStatuses, validateBackup, loadStoredStatuses, mergeStatuses,
    csvCell, csvLine, csvDocument, safeURL, phoneURL, capitalTier, formatCapital, formatEstablished, matchesRow, exportRow };
});
