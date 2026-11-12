const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const Core = require('../assets/core.js');
const root = path.join(__dirname, '..');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

async function app(t) {
  // Isolated DOM and worker responses; no network, real browser storage, or published data is changed.
  const dom = new JSDOM(fs.readFileSync(path.join(root, 'src/index.html'), 'utf8'), {
    url: 'https://example.invalid/', runScripts: 'dangerously', pretendToBeVisual: true
  });
  t.after(() => dom.window.close());
  const { window } = dom, queries = [];
  const county = name => ({ name, company_count: 2, center: [25, 121], districts: [{ id: 'D1', name: '中壢區', company_count: 2 }], shards: [] });
  const catalog = { schema_version: 2, data_mode: 'official', dataset_version: 'a'.repeat(64), columns: Core.SOURCE_COLUMNS,
    source: {}, counties: { taoyuan: county('桃園市'), taipei: county('臺北市') },
    industry_sections: { '45': '批發業', '46': '批發業', '47': '零售業', '48': '零售業', '62': '電腦程式設計', '63': '資訊服務' },
    enrichment: { '23492169': { market: '上市', stock_code: '5292', phone: '(03)4272889', chairperson: '鄭石治' } } };
  let onMessage;
  window.fetch = async () => ({ ok: true, json: async () => window.JSON.parse(JSON.stringify(catalog)) });
  window.Worker = class {
    addEventListener(type, fn) { if (type === 'message') onMessage = fn; }
    postMessage(message) { if (message.type === 'query') queries.push(message); }
    terminate() {}
  };
  window.eval(fs.readFileSync(path.join(root, 'assets/core.js'), 'utf8'));
  window.eval(fs.readFileSync(path.join(root, 'assets/app.js'), 'utf8'));
  await pause(20);
  assert.equal(queries.length, 1, 'application initializes without a DOM error');
  const document = window.document, get = id => document.getElementById(id), last = () => queries.at(-1);
  const reply = (rows, id = last().id) => onMessage({ data: { type: 'done', id, rows, count: rows.length,
    districtCounts: { D1: rows.length }, statusCounts: { ALL: rows.length, 尚未拜訪: rows.length }, addressCount: rows.length } });
  return { window, document, get, queries, last, reply };
}

const company = ['桃園市中壢區中央里中山路８８號１７樓', '23492169', '', '華懋科技股份有限公司', '463188000',
  '0810425', '股份有限公司', 'Y', '433212', '管道工程', '433211', '冷凍、通風、空調系統裝修工程', '', '', '', '', 'D1'];

test('defaults are visible, suggestions use returned companies, and full details remain available', async t => {
  const ui = await app(t);
  assert.equal(ui.last().filters.capital, 'MIN_10M');
  assert.equal(ui.last().filters.market, 'ALL');
  assert.match(ui.get('activeFilters').textContent, /資本額 1,000 萬以上/);
  assert.match(ui.get('searchScope').textContent, /桃園市/);
  ui.get('searchInput').value = '華懋 中壢'; ui.get('btnDoSearch').click(); ui.reply([company]);
  assert.equal(ui.last().filters.query, '華懋 中壢');
  assert.equal(ui.get('searchSuggestions').children[0].value, company[3]);
  assert.match(ui.get('searchSuggestions').children[0].label, /23492169.*5292/);
  const details = ui.document.querySelector('.company-details');
  assert.equal(details.open, false);
  assert.match(details.textContent, /463,188,000 元/);
  assert.match(details.textContent, /冷凍、通風/);
  assert.match(details.textContent, /是（Y）/);
  const options = [...ui.get('industrySelect').options];
  assert.equal(options.filter(option => option.textContent === '批發業').length, 1);
  assert.equal(options.find(option => option.textContent === '批發業').value, '45,46');
});

test('market and visit selections combine; district and county changes retain the search', async t => {
  const ui = await app(t);
  ui.get('searchInput').value = '華懋 中壢'; ui.get('btnDoSearch').click();
  ui.document.querySelector('[data-market="LISTED"]').click();
  ui.document.querySelector('[data-status="尚未拜訪"]').click();
  ui.window.openBuildingDirectory(company[0]);
  const oldId = ui.last().id;
  ui.document.querySelector('#districtNavBar [data-value="D1"]').click();
  assert.equal(ui.last().filters.query, '華懋 中壢');
  assert.equal(ui.last().filters.market, 'LISTED');
  assert.equal(ui.last().filters.status, '尚未拜訪');
  assert.equal(ui.last().filters.address, '');
  ui.window.switchCounty('taipei');
  assert.equal(ui.last().countyId, 'taipei');
  assert.equal(ui.last().filters.district, 'all');
  assert.equal(ui.last().filters.query, '華懋 中壢');
  assert.equal(ui.last().filters.market, 'LISTED');
  assert.equal(ui.last().filters.status, '尚未拜訪');
  ui.reply([company], oldId);
  assert.equal(ui.document.querySelectorAll('.company-card').length, 0, 'old county response is ignored');
});

test('empty results offer targeted recovery, while clear-all and restore-default remain distinct', async t => {
  const ui = await app(t);
  ui.get('searchInput').value = '不存在'; ui.get('btnDoSearch').click(); ui.reply([]);
  assert.match(ui.get('clientList').textContent, /桃園市.*資本額/s);
  assert.match(ui.get('clientList').textContent, /不存在/);
  const removeCapital = [...ui.document.querySelectorAll('.empty-actions button')].find(node => node.textContent.includes('取消資本額'));
  removeCapital.click();
  assert.equal(ui.last().filters.capital, 'ALL');
  assert.equal(ui.last().filters.query, '不存在');
  ui.get('btnResetFilter').click();
  assert.equal(ui.last().filters.capital, 'MIN_10M'); assert.equal(ui.last().filters.query, '');
  ui.get('btnClearFilters').click();
  assert.equal(ui.last().filters.capital, 'ALL'); assert.equal(ui.last().countyId, 'taoyuan');
});

test('Chinese composition never sends an unfinished query or treats candidate Enter as search', async t => {
  const ui = await app(t), input = ui.get('searchInput');
  input.dispatchEvent(new ui.window.CompositionEvent('compositionstart'));
  input.value = '華'; input.dispatchEvent(new ui.window.InputEvent('input', { isComposing: true }));
  input.dispatchEvent(new ui.window.KeyboardEvent('keydown', { key: 'Enter', isComposing: true }));
  await pause(350); assert.equal(ui.queries.length, 1);
  input.value = '華懋'; input.dispatchEvent(new ui.window.CompositionEvent('compositionend'));
  input.dispatchEvent(new ui.window.InputEvent('input'));
  await pause(350); assert.equal(ui.queries.length, 2);
  assert.equal(ui.last().filters.query, '華懋');
});

test('help opens from the visible control, closes with Escape and restores keyboard focus', async t => {
  const ui = await app(t), trigger = ui.document.querySelector('.search-help-row button');
  trigger.focus(); trigger.click();
  assert.equal(ui.get('modalHelp').style.display, 'flex');
  assert.equal(ui.get('appContainer').inert, true);
  ui.document.dispatchEvent(new ui.window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.equal(ui.get('modalHelp').hidden, true);
  assert.equal(ui.document.activeElement, trigger);
});
