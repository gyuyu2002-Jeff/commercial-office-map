const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createHash, webcrypto } = require('node:crypto');
const Core = require('../assets/core.js');
const version = 'a'.repeat(64);
const backup = statuses => ({ schema_version: 1, kind: Core.BACKUP_KIND,
  dataset_version: version, exported_at: '2026-11-06T12:00:00.000Z', statuses });
const filters = () => ({ district: 'all', category: 'ALL', capital: 'ALL', address: '', status: 'ALL', query: '' });
const row = (index, district = 'D1') => ['臺北市中正區忠孝路１號', String(index + 1).padStart(8, '0'), '',
  `實際來源公司 ${index}`, '0', '1130101', '有限公司', 'Y', '620100', '電腦程式設計業', '', '', '', '', '', '', district];

test('CSV preserves all source text, quotes, newlines, Unicode, and neutralizes formula prefixes', () => {
  assert.equal(Core.csvCell('ACME "Taiwan", Co.'), '"ACME ""Taiwan"", Co."');
  assert.equal(Core.csvCell('第一行\n第二行'), '"第一行\n第二行"');
  assert.equal(Core.csvDocument([['名稱', '統編'], ['公司', '00123456']]), '\uFEFF"名稱","統編"\r\n"公司","00123456"\r\n');
  for (const value of ['=1+1', '+SUM(A1)', '-1+2', '@SUM(A1)', '  =1+1', '\t=1+1', '\r+1', '\u0000@X']) {
    assert.ok(Core.csvCell(value).startsWith('"\''), JSON.stringify(value));
  }
});

test('official backup namespace rejects demo data, unknown states, prototype properties and extra fields', () => {
  assert.deepEqual({ ...Core.validateBackup(backup({ tax_00123456: '已拜訪' })) }, { tax_00123456: '已拜訪' });
  for (const statuses of [{ demo_123: '已拜訪' }, { tax_00123456: 'invalid' }, { tax_123: '已拜訪' }, [], null,
    JSON.parse('{"__proto__":"已拜訪"}')]) assert.throws(() => Core.validateBackup(backup(statuses)));
  for (const value of [{ ...backup({}), kind: 'commercial-office-map-status-backup' }, { ...backup({}), schema_version: 2 },
    { ...backup({}), extra: 'x' }, { ...backup({}), exported_at: 'invalid' }, { ...backup({}), dataset_version: '' }]) {
    assert.throws(() => Core.validateBackup(value));
  }
});

test('formal storage does not migrate demo records and restore preserves other counties and orphan records', () => {
  assert.deepEqual({ ...Core.loadStoredStatuses(null) }, {});
  assert.throws(() => Core.loadStoredStatuses(JSON.stringify({ schema_version: 3, statuses: { demo_123: '已拜訪' } })));
  const current = { tax_00123456: '已拜訪', tax_87654321: '洽談中' };
  assert.deepEqual({ ...Core.mergeStatuses(current, { tax_00123456: '尚未拜訪', tax_00000001: '已拜訪' }) },
    { tax_00123456: '尚未拜訪', tax_87654321: '洽談中', tax_00000001: '已拜訪' });
  assert.equal(current.tax_00123456, '已拜訪');
});

test('search normalizes full-width digits, 台/臺 and embedded address spacing', () => {
  assert.equal(Core.normalizeText(' 嘉義市東　區 １２３號 '), '嘉義市東區123號');
  assert.equal(Core.normalizeText('臺北ＡＢＣ'), '台北abc');
  const record = row(1);
  assert.equal(Core.matchesRow(record, { ...filters(), query: '台北市中正區忠孝路1號' }, {}, {}), true);
  assert.equal(Core.matchesRow(record, { ...filters(), query: '00000002' }, {}, {}), true);
});

test('capital zero is factual, unknown remains unknown, and official metadata is never synthesized', () => {
  assert.equal(Core.formatCapital('0'), '0 元');
  assert.equal(Core.capitalTier(''), 'UNKNOWN');
  assert.equal(Core.capitalTier('5000000'), 'TIER_5M');
  assert.equal(Core.capitalTier('30000000'), 'TIER_30M');
  assert.equal(Core.capitalTier('100000000'), 'TIER_100M');
  assert.equal(Core.formatEstablished('1130101'), '2024-01-01');
  assert.equal(Core.formatEstablished('1130231'), '1130231');
  const record = row(1);
  assert.equal(Core.matchesRow(record, { ...filters(), status: 'LISTED' }, {}, {}), false);
  assert.equal(Core.matchesRow(record, { ...filters(), status: '已拜訪' }, { tax_00000002: '已拜訪' }, {}), true);
  record[8] = '';
  assert.equal(Core.matchesRow(record, { ...filters(), category: 'UNKNOWN' }, {}, {}), true);
});

test('safe links reject executable URLs while CSV preserves raw official website text', () => {
  assert.equal(Core.safeURL('javascript:alert(1)'), null);
  assert.equal(Core.safeURL('data:text/html,test'), null);
  assert.equal(Core.safeURL('https://example.com'), 'https://example.com/');
  assert.equal(Core.phoneURL('02-1234-5678轉20'), null);
  assert.equal(Core.phoneURL('(02)1234-5678'), 'tel:0212345678');
  const catalog = { enrichment: { '00000001': { market: '上市', website_raw: 'www.example.com', website: 'https://www.example.com', phone: '02-123轉10' } },
    source: { url: 'https://example.com/source.zip', source_date: '2026-11-06' } };
  const exported = Core.exportRow(row(0), {}, catalog);
  assert.equal(exported.length, Core.CSV_HEADERS.length);
  assert.equal(exported[Core.CSV_HEADERS.indexOf('公司網站（來源原值）')], 'www.example.com');
  assert.equal(exported[Core.CSV_HEADERS.indexOf('來源快照日期')], '2026-11-06');
  assert.deepEqual(exported.slice(0, 16), row(0).slice(0, 16));
});

function workerHarness(customFetch, timeoutMs) {
  const messages = [], files = new Map(), requests = [];
  let listener;
  const self = { location: new URL('https://example.com/assets/search-worker.js?v=test'), CommercialMapCore: Core,
    postMessage(message) { messages.push(message); }, addEventListener(type, callback) { if (type === 'message') listener = callback; } };
  const fetch = async (url, options) => {
    const filename = new URL(url).pathname.replace('/data/', ''); requests.push(filename);
    if (customFetch) return customFetch(filename, options, files);
    if (!files.has(filename)) return new Response('', { status: 404 });
    return new Response(files.get(filename));
  };
  const context = vm.createContext({ self, importScripts() {}, fetch, URL, AbortController, DOMException, TextDecoder, Uint8Array,
    Uint32Array, Blob, crypto: webcrypto, setTimeout: (callback, delay) => setTimeout(callback, timeoutMs ?? delay), clearTimeout, console });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../assets/search-worker.js'), 'utf8'), context);
  const catalog = { dataset_version: version, enrichment: {}, source: { url: 'https://example.com/raw.zip', source_date: '2026-11-06' }, counties: {} };
  function addCounty(id, slices) {
    const shards = slices.map((records, index) => {
      const filename = `shards/${id}-${index}.json`, text = JSON.stringify({ rows: records }); files.set(filename, text);
      return { path: filename, count: records.length, sha256: createHash('sha256').update(text).digest('hex') };
    });
    catalog.counties[id] = { company_count: slices.reduce((sum, records) => sum + records.length, 0), shards };
  }
  const send = message => listener({ data: message });
  const initialize = () => send({ type: 'init', catalog });
  return { messages, files, requests, catalog, addCounty, send, initialize };
}

test('worker scans every shard, returns 40-row pages, and CSV contains all matches rather than one page', async () => {
  const h = workerHarness();
  const records = Array.from({ length: 95 }, (_, i) => row(i, i % 2 ? 'D1' : 'D2'));
  h.addCounty('taipei', [records.slice(0, 30), records.slice(30, 60), records.slice(60)]);
  await h.initialize(); await h.send({ type: 'query', id: 1, countyId: 'taipei', filters: filters(), statuses: {} });
  const done = h.messages.find(message => message.type === 'done');
  assert.equal(done.count, 95); assert.equal(done.rows.length, 40);
  assert.equal(Object.values(done.districtCounts).reduce((a, b) => a + b, 0), 95);
  assert.equal(h.messages.filter(message => message.type === 'progress').length, 3);
  await h.send({ type: 'page', id: 1, offset: 40 });
  const page = h.messages.find(message => message.type === 'page');
  assert.equal(page.rows.length, 40); assert.equal(page.rows[0][1], '00000041');
  await h.send({ type: 'export', id: 1 });
  const exported = h.messages.find(message => message.type === 'export');
  assert.equal(exported.count, 95);
  const text = await exported.blob.text();
  assert.equal(text.split('\r\n').filter(Boolean).length, 96);
  assert.ok(text.includes('"00000095"'));
});

test('worker applies visit status, normalized search, and real address grouping consistently', async () => {
  const h = workerHarness(); h.addCounty('taipei', [[row(0), row(1), row(2)]]); await h.initialize();
  await h.send({ type: 'query', id: 2, countyId: 'taipei', filters: { ...filters(), status: '尚未拜訪', query: '台北' }, statuses: { tax_00000001: '已拜訪' } });
  const done = h.messages.find(message => message.type === 'done');
  assert.equal(done.count, 2); assert.equal(done.statusCounts.ALL, 3); assert.equal(done.statusCounts['已拜訪'], 1);
  await h.send({ type: 'directory', id: 2, requestId: 1, offset: 0, query: '忠孝路1號' });
  const directory = h.messages.find(message => message.type === 'directory');
  assert.equal(directory.total, 1); assert.equal(directory.addresses[0].count, 2);
});

test('worker rejects mixed-version shards, missing shards, and count mismatches without claiming completion', async () => {
  for (const failure of ['hash', 'missing', 'count']) {
    const h = workerHarness(); h.addCounty('taipei', [[row(0)], [row(1)]]);
    const second = h.catalog.counties.taipei.shards[1];
    if (failure === 'hash') h.files.set(second.path, JSON.stringify({ rows: [row(2)] }));
    if (failure === 'missing') h.files.delete(second.path);
    if (failure === 'count') second.count = 2;
    await h.initialize(); await h.send({ type: 'query', id: 3, countyId: 'taipei', filters: filters(), statuses: {} });
    assert.ok(h.messages.some(message => message.type === 'error'), failure);
    assert.equal(h.messages.some(message => message.type === 'done'), false, failure);
    await h.send({ type: 'export', id: 3 });
    assert.equal(h.messages.some(message => message.type === 'export'), false, failure);
  }
});

test('switching counties aborts an outstanding fetch and prevents stale completion', async () => {
  let started;
  const waiting = new Promise(resolve => { started = resolve; });
  const h = workerHarness(async (filename, options, files) => {
    if (filename.startsWith('shards/slow-')) return new Promise((resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')), { once: true }); started();
    });
    return new Response(files.get(filename));
  });
  h.addCounty('slow', [[row(0)]]); h.addCounty('fast', [[row(1)]]); await h.initialize();
  const old = h.send({ type: 'query', id: 4, countyId: 'slow', filters: filters(), statuses: {} });
  await waiting;
  await h.send({ type: 'query', id: 5, countyId: 'fast', filters: filters(), statuses: {} }); await old;
  assert.deepEqual(h.messages.filter(message => message.type === 'done').map(message => message.id), [5]);
});

test('worker limits decoded shard cache and reloads evicted pages without losing results', async () => {
  const h = workerHarness();
  h.addCounty('taipei', Array.from({ length: 5 }, (_, part) => Array.from({ length: 50 }, (_, i) => row(part * 50 + i))));
  await h.initialize(); await h.send({ type: 'query', id: 6, countyId: 'taipei', filters: filters(), statuses: {} });
  assert.equal(h.requests.length, 5);
  await h.send({ type: 'page', id: 6, offset: 0 });
  assert.equal(h.requests.length, 6, 'first shard was evicted and fetched again');
  await h.send({ type: 'page', id: 6, offset: 200 });
  assert.equal(h.requests.length, 6, 'recent shard remains cached');
  assert.equal(h.messages.filter(message => message.type === 'page').at(-1).rows[0][1], '00000201');
});

test('worker timeout produces a retryable error rather than waiting forever or reporting success', async () => {
  const h = workerHarness((filename, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')), { once: true });
  }), 5);
  h.addCounty('taipei', [[row(0)]]); await h.initialize();
  await h.send({ type: 'query', id: 7, countyId: 'taipei', filters: filters(), statuses: {} });
  assert.match(h.messages.find(message => message.type === 'error').message, /45 秒/);
  assert.equal(h.messages.some(message => message.type === 'done'), false);
});
