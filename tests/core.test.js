const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Core = require('../assets/core.js');

const first = 'demo_' + '1'.repeat(24);
const second = 'demo_' + '2'.repeat(24);
const third = 'demo_' + '3'.repeat(24);
const known = new Set([first, second, third]);
const legacyMap = { C_1001: first, C_1002: second };
const version = 'a'.repeat(64);
const backup = statuses => ({ schema_version: 1, kind: Core.BACKUP_KIND,
  dataset_version: version, exported_at: '2026-11-06T12:00:00.000Z', statuses });

test('CSV preserves commas, quotes, embedded newlines, Unicode, and CRLF record boundaries', () => {
  assert.equal(Core.csvCell('ACME "Taiwan", Co.'), '"ACME ""Taiwan"", Co."');
  assert.equal(Core.csvCell('第一行\n第二行'), '"第一行\n第二行"');
  assert.equal(Core.csvCell(null), '""');
  assert.equal(Core.csvDocument([['名稱', '地址'], ['示範 "A"', '臺北,一樓']]),
    '\uFEFF"名稱","地址"\r\n"示範 ""A""","臺北,一樓"');
});

test('CSV neutralizes formulas including leading whitespace/control-character bypasses', () => {
  for (const value of ['=1+1', '+SUM(A1)', '-1+2', '@SUM(A1)', '  =1+1', '\t=1+1', '\r+1', '\u0000@X', '\t00123']) {
    assert.ok(Core.csvCell(value).startsWith('"\''), JSON.stringify(value));
  }
  assert.equal(Core.csvCell('A-公司'), '"A-公司"');
  assert.equal(Core.csvCell('正常企業'), '"正常企業"');
});

test('restore accepts known identities across counties and only whitelisted visit states', () => {
  assert.deepEqual({ ...Core.validateBackup(backup({ [first]: '已拜訪', [second]: '洽談中' }), known) },
    { [first]: '已拜訪', [second]: '洽談中' });
  for (const statuses of [{ ['demo_' + 'f'.repeat(24)]: '已拜訪' }, { [first]: '<script>' }, { C_1001: '已拜訪' }, [], null,
    JSON.parse('{"__proto__":"已拜訪"}')]) {
    assert.throws(() => Core.validateBackup(backup(statuses), known));
  }
});

test('backup schema rejects other applications, versions, unknown properties, and malformed metadata', () => {
  const valid = backup({});
  for (const value of [{ ...valid, schema_version: 2 }, { ...valid, kind: 'other' }, { ...valid, extra: 'x' },
    { ...valid, exported_at: 'invalid' }, { ...valid, dataset_version: '' }, { statuses: {} }, null, []]) {
    assert.throws(() => Core.validateBackup(value, known));
  }
});

test('legacy migration imports explicit saved overrides, ignores invalid values, and leaves absent records unset', () => {
  const saved = JSON.stringify({ C_1001: '已拜訪', C_1002: 'invalid', C_9999: '洽談中' });
  const migrated = Core.loadStoredStatuses(null, saved, legacyMap, known);
  assert.equal(migrated.migrated, true);
  assert.deepEqual({ ...migrated.statuses }, { [first]: '已拜訪' });
  assert.equal(Object.hasOwn(migrated.statuses, second), false);
  assert.deepEqual({ ...Core.loadStoredStatuses(null, null, legacyMap, known).statuses }, {});
});

test('v3 wins over legacy permanently, including an empty v3 record set', () => {
  const legacy = JSON.stringify({ C_1001: '已拜訪' });
  const current = JSON.stringify({ schema_version: 3, statuses: { [first]: '洽談中' } });
  const result = Core.loadStoredStatuses(current, legacy, legacyMap, known);
  assert.equal(result.migrated, false);
  assert.equal(result.statuses[first], '洽談中');
  assert.deepEqual({ ...Core.loadStoredStatuses(JSON.stringify({ schema_version: 3, statuses: {} }), legacy, legacyMap, known).statuses }, {});
  assert.throws(() => Core.loadStoredStatuses('{broken', legacy, legacyMap, known));
});

test('restore merge preserves records from other counties, applies imported conflicts, and does not mutate inputs', () => {
  const current = { [first]: '已拜訪', [second]: '洽談中' };
  const incoming = { [first]: '尚未拜訪', [third]: '已拜訪' };
  assert.deepEqual({ ...Core.mergeStatuses(current, incoming, known) },
    { [first]: '尚未拜訪', [second]: '洽談中', [third]: '已拜訪' });
  assert.equal(current[first], '已拜訪');
  assert.equal(Object.hasOwn(current, third), false);
});

test('filters combine with status and update immediately when status changes', () => {
  const a = { id: first, name: 'Alpha', building_name: 'One', address: '桃園路', district_id: 'north', category: 'IT', capital_tier: 'large', building_id: 'B1', status: '尚未拜訪', is_listed: true };
  const b = { ...a, id: second, name: 'Beta', status: '已拜訪' };
  const f = { district: 'north', category: 'IT', capital: 'large', building: 'B1', status: '尚未拜訪', query: '桃園' };
  assert.deepEqual(Core.filterCompanies([a, b], f), [a]);
  assert.equal(Core.filterCompanies([a, b], f, true).length, 2);
  a.status = '已拜訪';
  assert.equal(Core.filterCompanies([a, b], f).length, 0);
  assert.equal(Core.filterCompanies([a, b], { ...f, status: 'ALL', query: 'ALPHA' }).length, 1);
  assert.equal(Core.filterCompanies([a, b], { ...f, category: 'Finance' }).length, 0);
});

test('built catalogue identities validate all counties and support old saved IDs', () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/catalog.json'), 'utf8'));
  const ids = new Set(Object.values(catalog.legacy_id_map));
  let recordCount = 0;
  const samples = {};
  for (const countyId of Object.keys(catalog.counties)) {
    const data = JSON.parse(fs.readFileSync(path.join(__dirname, `../data/counties/${countyId}.json`), 'utf8'));
    for (const c of data.companies) {
      assert.equal(catalog.legacy_id_map[c.legacy_id], c.id);
      assert.ok(ids.has(c.id));
      recordCount++;
    }
    if (data.companies.length) samples[data.companies[0].id] = '已拜訪';
  }
  assert.equal(ids.size, recordCount);
  assert.equal(Object.keys(Core.validateBackup({ ...backup(samples), dataset_version: catalog.dataset_version }, ids)).length,
    Object.keys(catalog.counties).length);
});
