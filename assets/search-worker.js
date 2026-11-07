'use strict';
importScripts('core.js' + self.location.search);
const Core = self.CommercialMapCore;
let catalog, current;
const cache = new Map();
const CACHE_LIMIT = 3;

function send(type, data) { self.postMessage({ type, ...data }); }
function checkCurrent(job) {
  if (current !== job || job.controller.signal.aborted) throw new DOMException('Cancelled', 'AbortError');
}

async function readRows(shard, job) {
  checkCurrent(job);
  if (cache.has(shard.path)) {
    const rows = cache.get(shard.path);
    cache.delete(shard.path); cache.set(shard.path, rows);
    return rows;
  }
  const url = new URL('../data/' + shard.path, self.location.href);
  url.searchParams.set('v', catalog.dataset_version);
  const controller = new AbortController();
  let timedOut = false;
  const cancel = () => controller.abort();
  job.controller.signal.addEventListener('abort', cancel, { once: true });
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 45000);
  let buffer;
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`資料分片載入失敗（HTTP ${response.status}）。`);
    buffer = await response.arrayBuffer();
  } catch (error) {
    if (timedOut) throw new Error('資料分片載入超過 45 秒；請確認網路後重試。');
    throw error;
  } finally {
    clearTimeout(timeout); job.controller.signal.removeEventListener('abort', cancel);
  }
  checkCurrent(job);
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  if (hash !== shard.sha256) throw new Error('資料版本校驗不符，可能正在更新；請重新整理後再試。');
  const data = JSON.parse(new TextDecoder().decode(buffer));
  checkCurrent(job);
  if (!Array.isArray(data.rows) || data.rows.length !== shard.count
    || data.rows.some(row => !Array.isArray(row) || row.length !== Core.SOURCE_COLUMNS.length || !Core.companyId(row[1]))) {
    throw new Error('資料分片格式或筆數不一致；請重新整理後再試。');
  }
  cache.set(shard.path, data.rows);
  while (cache.size > CACHE_LIMIT) cache.delete(cache.keys().next().value);
  return data.rows;
}

async function query(message) {
  if (current) current.controller.abort();
  const county = catalog.counties[message.countyId];
  if (!county) throw new Error('找不到此縣市資料。');
  const job = { id: message.id, countyId: message.countyId, controller: new AbortController(),
    filters: { ...message.filters, query: Core.normalizeText(message.filters.query) }, statuses: Core.validateStatuses(message.statuses),
    matches: [], otherMatches: [], count: 0, scanned: 0, total: county.company_count, preview: [[], []], districtCounts: Object.create(null),
    statusCounts: { ALL: 0, LISTED: 0, 尚未拜訪: 0, 洽談中: 0, 已拜訪: 0 }, sectionCounts: Object.create(null),
    addresses: new Map(), complete: false };
  current = job;
  for (const shard of county.shards) {
    const rows = await readRows(shard, job), hits = [[], []];
    for (let index = 0; index < rows.length; index++) {
      const row = rows[index];
      if (job.filters.district === 'all' || row[16] === job.filters.district) {
        const section = String(row[8] || '').slice(0, 2) || 'UNKNOWN';
        job.sectionCounts[section] = (job.sectionCounts[section] || 0) + 1;
      }
      if (!Core.matchesRow(row, job.filters, job.statuses, catalog.enrichment, true)) continue;
      const visit = job.statuses[Core.companyId(row[1])] || Core.STATUSES[0];
      const listed = ['上市', '上櫃'].includes(catalog.enrichment[String(row[1])]?.market);
      job.statusCounts.ALL++;
      job.statusCounts[visit]++;
      if (listed) job.statusCounts.LISTED++;
      if (job.filters.status !== 'ALL' && (job.filters.status === 'LISTED' ? !listed : visit !== job.filters.status)) continue;
      const priority = listed ? 0 : 1;
      hits[priority].push(index);
      job.count++;
      if (job.preview[priority].length < 40) job.preview[priority].push(row);
      job.districtCounts[row[16]] = (job.districtCounts[row[16]] || 0) + 1;
      const address = String(row[0] || '');
      job.addresses.set(address, (job.addresses.get(address) || 0) + 1);
    }
    if (hits[0].length) job.matches.push({ shard, indices: Uint32Array.from(hits[0]) });
    if (hits[1].length) job.otherMatches.push({ shard, indices: Uint32Array.from(hits[1]) });
    job.scanned += rows.length;
    send('progress', { id: job.id, scanned: job.scanned, total: job.total, count: job.count, rows: job.preview.flat().slice(0, 40),
      statusCounts: job.statusCounts, districtCounts: job.districtCounts });
  }
  checkCurrent(job);
  if (job.scanned !== job.total) throw new Error('縣市資料總筆數不一致；搜尋尚未完成。');
  // Stable partition across every shard keeps pages and exports in the same listed-first order.
  job.matches.push(...job.otherMatches);
  job.otherMatches = [];
  job.complete = true;
  send('done', { id: job.id, count: job.count, rows: job.preview.flat().slice(0, 40), statusCounts: job.statusCounts,
    districtCounts: job.districtCounts, sectionCounts: job.sectionCounts, addressCount: job.addresses.size });
}

async function page(message) {
  const job = current;
  if (!job || job.id !== message.id || !job.complete) return;
  let skipped = 0;
  const result = [];
  for (const match of job.matches) {
    if (skipped + match.indices.length <= message.offset) { skipped += match.indices.length; continue; }
    const rows = await readRows(match.shard, job);
    for (let i = Math.max(0, message.offset - skipped); i < match.indices.length && result.length < 40; i++) result.push(rows[match.indices[i]]);
    skipped += match.indices.length;
    if (result.length >= 40) break;
  }
  checkCurrent(job);
  send('page', { id: job.id, offset: message.offset, rows: result });
}

function directory(message) {
  const job = current;
  if (!job || job.id !== message.id || !job.complete) return;
  if (!job.addressList) job.addressList = Array.from(job.addresses, ([address, count]) => ({ address, count }))
    .sort((a, b) => a.address.localeCompare(b.address, 'zh-Hant'));
  const text = Core.normalizeText(message.query);
  const addresses = text ? job.addressList.filter(item => Core.normalizeText(item.address).includes(text)) : job.addressList;
  send('directory', { id: job.id, requestId: message.requestId, total: addresses.length,
    offset: message.offset, addresses: addresses.slice(message.offset, message.offset + 40) });
}

async function exportCSV(message) {
  const job = current;
  if (!job || job.id !== message.id || !job.complete) return;
  if (job.count > Core.MAX_EXPORT_ROWS) throw new Error('結果超過 100,000 筆；請篩選行政區，或下載官方完整來源。');
  const parts = ['\uFEFF', Core.csvLine(Core.CSV_HEADERS)];
  let completed = 0;
  for (const match of job.matches) {
    const rows = await readRows(match.shard, job);
    const lines = [];
    for (const index of match.indices) lines.push(Core.csvLine(Core.exportRow(rows[index], job.statuses, catalog)));
    parts.push(lines.join(''));
    completed += match.indices.length;
    send('exportProgress', { id: job.id, completed, total: job.count });
  }
  checkCurrent(job);
  send('export', { id: job.id, count: completed, blob: new Blob(parts, { type: 'text/csv;charset=utf-8' }) });
}

self.addEventListener('message', async event => {
  const message = event.data;
  try {
    if (message.type === 'init') { catalog = message.catalog; cache.clear(); return; }
    if (message.type === 'cancel') { if (current) current.controller.abort(); return; }
    if (!catalog) throw new Error('資料目錄尚未載入。');
    if (message.type === 'query') await query(message);
    else if (message.type === 'page') await page(message);
    else if (message.type === 'directory') directory(message);
    else if (message.type === 'export') await exportCSV(message);
  } catch (error) {
    if (error.name === 'AbortError') return;
    send('error', { id: message.id, operation: message.type, message: error.message || '資料載入失敗。' });
  }
});
