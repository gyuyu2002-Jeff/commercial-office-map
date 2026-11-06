(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CommercialMapCore = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const STATUSES = Object.freeze(['尚未拜訪', '洽談中', '已拜訪']);
  const BACKUP_KIND = 'commercial-office-map-status-backup';
  const MAX_BACKUP_BYTES = 1024 * 1024;

  function isRecord(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
  }

  function validateStatuses(value, knownIds) {
    if (!isRecord(value) || Object.keys(value).length > knownIds.size) throw new Error('紀錄格式或筆數不正確。');
    const result = Object.create(null);
    for (const [id, status] of Object.entries(value)) {
      if (!/^demo_[a-f0-9]{24}$/.test(id) || !knownIds.has(id) || !STATUSES.includes(status)) {
        throw new Error('紀錄包含未知企業或不允許的狀態；未匯入任何資料。');
      }
      result[id] = status;
    }
    return result;
  }

  function validateBackup(value, knownIds) {
    const fields = ['schema_version', 'kind', 'dataset_version', 'exported_at', 'statuses'];
    if (!isRecord(value) || Object.keys(value).length !== fields.length
      || fields.some(key => !Object.hasOwn(value, key))
      || value.schema_version !== 1 || value.kind !== BACKUP_KIND
      || typeof value.dataset_version !== 'string' || !/^[a-f0-9]{64}$/.test(value.dataset_version)
      || typeof value.exported_at !== 'string' || !Number.isFinite(Date.parse(value.exported_at))) {
      throw new Error('不是本網站支援的紀錄備份檔。');
    }
    return validateStatuses(value.statuses, knownIds);
  }

  function migrateLegacy(value, legacyMap) {
    const result = Object.create(null);
    if (!isRecord(value)) return result;
    for (const [legacyId, status] of Object.entries(value)) {
      if (Object.hasOwn(legacyMap, legacyId) && STATUSES.includes(status)) result[legacyMap[legacyId]] = status;
    }
    return result;
  }

  function loadStoredStatuses(currentJSON, legacyJSON, legacyMap, knownIds) {
    if (currentJSON !== null) {
      const value = JSON.parse(currentJSON);
      if (!isRecord(value) || value.schema_version !== 3 || Object.keys(value).length !== 2) throw new Error('紀錄格式無法辨識');
      return { statuses: validateStatuses(value.statuses, knownIds), migrated: false };
    }
    return { statuses: migrateLegacy(legacyJSON === null ? {} : JSON.parse(legacyJSON), legacyMap), migrated: legacyJSON !== null };
  }

  function mergeStatuses(current, incoming, knownIds) {
    return Object.assign(Object.create(null), validateStatuses(current, knownIds), validateStatuses(incoming, knownIds));
  }

  function csvCell(value) {
    let text = String(value ?? '');
    if (/^[\s\u0000-\u001f]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function csvDocument(rows) {
    return '\uFEFF' + rows.map(row => row.map(csvCell).join(',')).join('\r\n');
  }

  function filterCompanies(companies, filters, ignoreStatus) {
    const query = (filters.query || '').trim().toLocaleLowerCase();
    return companies.filter(company => {
      if (filters.district !== 'all' && company.district_id !== filters.district) return false;
      if (filters.category !== 'ALL' && company.category !== filters.category) return false;
      if (filters.capital !== 'ALL' && company.capital_tier !== filters.capital) return false;
      if (filters.building !== 'ALL' && company.building_id !== filters.building) return false;
      if (!ignoreStatus && filters.status !== 'ALL') {
        if (filters.status === 'LISTED' ? !company.is_listed : company.status !== filters.status) return false;
      }
      return !query || ['name', 'building_name', 'address', 'tax_id', 'rep_name']
        .some(key => String(company[key] || '').toLocaleLowerCase().includes(query));
    });
  }

  return { STATUSES, BACKUP_KIND, MAX_BACKUP_BYTES, isRecord, validateStatuses, validateBackup,
    migrateLegacy, loadStoredStatuses, mergeStatuses, csvCell, csvDocument, filterCompanies };
});
