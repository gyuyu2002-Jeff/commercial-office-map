import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from build_commercial_html import (ROOT, HEADERS, COUNTIES, COLUMNS, base_building_address, canonical_json,
    identify_commercial_buildings, locate_address, normal_address, parse_floor_number, parse_source_date,
    prepare_data, read_tax_rows, version_content, attach_named_buildings)

class OfficialDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = json.loads((ROOT / 'config/areas.json').read_text(encoding='utf-8'))
        cls.area_index = {}
        for area in cls.geo['areas']:
            cls.area_index.setdefault(normal_address(area['county_name']), []).append(area)
        cls.rows = []
        for i, (county_id, name) in enumerate(COUNTIES.items()):
            area = cls.area_index[name][0]
            cls.rows.append([name + area['town_name'] + '測試路１號', f'{i+1:08d}', '', '測試公司'+str(i), '0', '1151106', '有限公司', 'Y', '620199', '其他電腦程式設計', '', '', '', '', '', ''])
        cls.manifest = {key: {'url':'https://example.invalid/'+key, 'sha256':'a'*64} for key in ('tax','twse','tpex')}

    def archive(self, directory, rows, headers=HEADERS, date='06-NOV-26'):
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow([date] + ['']*15)
        writer.writerows(rows)
        path = Path(directory) / 'source.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('source.csv', '\ufeff'+output.getvalue())
        return path

    def build_fixture(self, directory, rows, office_buildings_only=False):
        archive = self.archive(directory, rows)
        return prepare_data(archive, Path(directory)/'data', self.geo, self.manifest, {}, {'62':'電腦程式設計'}, min_records=1, office_buildings_only=office_buildings_only)

    def test_official_area_matching_does_not_truncate_zheng_or_city_names(self):
        for address, expected in [('桃園市平鎮區延平路１號','平鎮區'), ('高雄市前鎮區中山路1號','前鎮區'), ('臺南市新市區1號','新市區')]:
            county, code = locate_address(address, self.area_index)
            self.assertEqual(next(a['town_name'] for a in self.geo['areas'] if a['town_code']==code),expected)
        self.assertEqual(locate_address('新竹市科學園區', self.area_index), ('hsinchu_city','hsinchu_city_unknown'))
        self.assertEqual(locate_address('臺北市', self.area_index), ('taipei','taipei_unknown'))
        county, code = locate_address('嘉義市東　區民權路１號', self.area_index)
        self.assertEqual(next(a['town_name'] for a in self.geo['areas'] if a['town_code']==code),'東區')

    def test_source_date_row_is_metadata_not_company_and_preserves_all_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = self.build_fixture(directory, self.rows)
            self.assertEqual(catalog['source']['source_date'],'2026-11-06')
            self.assertEqual(catalog['total_count'],22)
            self.assertEqual(catalog['columns'],COLUMNS)
            for row, county_id in zip(self.rows, COUNTIES):
                shard = catalog['counties'][county_id]['shards'][0]
                actual = json.loads((Path(directory)/'data'/shard['path']).read_text(encoding='utf-8'))['rows'][0]
                self.assertEqual(actual[:16], row)
                self.assertEqual(actual[4],'0')
                self.assertEqual(actual[1],row[1])

    def test_duplicate_and_invalid_identity_stop_publication(self):
        for rows in [self.rows + [self.rows[0]], [list(self.rows[0])] + self.rows[1:]]:
            if len(rows)==22:
                rows[0][1]='not-a-tax-id'
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                self.build_fixture(directory, rows)

    def test_unknown_address_is_preserved_and_reconciled(self):
        rows = [list(row) for row in self.rows]
        rows[0][0]='臺北市'
        rows.append(['無法辨識的原文地址','99999999','','未分類企業','100','1151106','獨資','N','','','','','','','',''])
        with tempfile.TemporaryDirectory() as directory:
            catalog = self.build_fixture(directory, rows)
            self.assertEqual(catalog['total_count'],23)
            self.assertEqual(catalog['coverage']['unclassified_count'],2)
            self.assertEqual(catalog['counties']['unknown']['company_count'],1)
            self.assertEqual(sum(c['company_count'] for c in catalog['counties'].values()),23)

    def test_missing_county_or_changed_schema_stops_publication(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            self.build_fixture(directory,self.rows[:-1])
        with tempfile.TemporaryDirectory() as directory:
            archive=self.archive(directory,self.rows,headers=['wrong']+HEADERS[1:])
            with self.assertRaises(ValueError):
                list(read_tax_rows(archive))
        with self.assertRaises(ValueError):
            parse_source_date('not a date')

    def test_dataset_version_tracks_content_and_not_download_clock(self):
        left = {'source': {'sha256':'a'*64, 'retrieved_at':'2026-11-06'}}
        right = {'source': {'sha256':'a'*64, 'retrieved_at':'2026-11-07'}}
        self.assertEqual(version_content(left),version_content(right))
        right['source']['sha256']='b'*64
        self.assertNotEqual(version_content(left),version_content(right))

    def test_published_stock_contacts_are_exact_tax_id_joins(self):
        catalog = json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        lookup = {}
        for key, tax, phone, chair, website in [('twse','營利事業統一編號','總機電話','董事長','網址'),
                ('tpex','UnifiedBusinessNo.','Telephone','Chairman','WebAddress')]:
            for row in json.loads((ROOT/f'.cache/official/{key}.json').read_bytes()):
                lookup[str(row.get(tax,''))]=(row.get(phone,''),row.get(chair,''),row.get(website,''))
        for tax_id, info in catalog['enrichment'].items():
            expected = tuple(str(value).replace('\\u3000',' ').strip() for value in lookup[tax_id])
            self.assertEqual((info['phone'],info['chairperson'],info['website_raw']),expected)
        self.assertEqual(catalog['coverage']['listed_matches'],len(catalog['enrichment']))
        self.assertIn('dataset_url',catalog['industry_source'])

    def test_named_building_provenance_exact_doors_and_counts(self):
        catalog = json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        config = json.loads((ROOT/'config/named_buildings.json').read_text(encoding='utf-8'))
        self.assertEqual(len(catalog['named_buildings']), len(config['buildings']))
        self.assertEqual(catalog['building_name_sources'], config['sources'])
        self.assertEqual({b['county_id'] for b in catalog['named_buildings']}, set(catalog['counties']), 'every county has a first verified door entry')
        door_only = [b for b in catalog['named_buildings'] if b.get('name_status') == 'address_only']
        self.assertEqual([b['county_id'] for b in door_only], ['lienchiang'])
        self.assertEqual(door_only[0]['name'], '馬祖村8號')
        self.assertEqual(door_only[0]['aliases'], [])
        counts = Counter(base_building_address(row[0]) for county in catalog['counties'].values() for shard in county['shards']
            for row in json.loads((ROOT/'data'/shard['path']).read_text(encoding='utf-8'))['rows'])
        for building, original in zip(catalog['named_buildings'], config['buildings']):
            self.assertEqual({key: building[key] for key in original}, original)
            self.assertEqual(building['company_count'], sum(counts[address] for address in building['addresses']))
            self.assertEqual(building['address_counts'], {address: counts[address] for address in building['addresses']})
        motian = next(b for b in catalog['named_buildings'] if b['name'] == '摩天金融大樓')
        self.assertEqual(motian['addresses'], ['桃園市桃園區中正路1247號', '桃園市桃園區中正路1249號'])
        self.assertNotIn('桃園市桃園區中正路1248號', motian['addresses'])
        old_version = catalog['dataset_version']
        attach_named_buildings(catalog, config, ROOT/'data')
        self.assertEqual(catalog['dataset_version'], old_version, 'unchanged names and data give a stable version')
        config['buildings'][0]['aliases'].append('測試別名')
        attach_named_buildings(catalog, config, ROOT/'data')
        self.assertNotEqual(catalog['dataset_version'], old_version)

    def test_invalid_named_building_associations_stop_publication(self):
        catalog = json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        original = json.loads((ROOT/'config/named_buildings.json').read_text(encoding='utf-8'))
        for failure in ('duplicate', 'floor', 'county', 'source', 'fake_name'):
            config = json.loads(json.dumps(original))
            if failure == 'duplicate':
                config['buildings'].append(config['buildings'][0])
            elif failure == 'floor':
                config['buildings'][0]['addresses'][0] += '8樓'
            elif failure == 'county':
                config['buildings'][0]['county_id'] = 'taipei'
            elif failure == 'fake_name':
                config['buildings'][0]['name_status'] = 'address_only'
            else:
                config['buildings'][0]['references'][0]['source_id'] = 'missing'
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                attach_named_buildings(catalog, config, ROOT/'data')

    def test_commercial_building_filter_keeps_office_towers_and_excludes_street_shops(self):
        self.assertEqual(base_building_address('桃園市桃園區同德里中正路１０７１號１４樓之６'), '桃園市桃園區中正路1071號')
        self.assertEqual(base_building_address('桃園市中壢區中央西路一段１號３樓'), '桃園市中壢區中央西路1段1號')
        self.assertEqual(base_building_address('連江縣南竿鄉介壽村256號2樓'), '連江縣南竿鄉介壽村256號')
        self.assertEqual(parse_floor_number('桃園市桃園區中正路１０７１號十四樓之２'), 14)
        rows = []
        tax_seq = 1
        for county_id, name in COUNTIES.items():
            town = self.area_index[name][0]['town_name']
            for fl in (1, 2, 4, 6, 8, 8, 10, 12):
                li = '中興里' if fl % 2 else ''
                sec = '一段' if fl % 2 else '1段'
                rows.append([f'{name}{town}{li}測試路{sec}100號{fl}樓', f'{tax_seq:08d}', '', f'商辦公司{tax_seq}', '10000000', '1151106', '股份有限公司', 'Y', '620199', '其他電腦程式設計', '', '', '', '', '', ''])
                tax_seq += 1
        taoyuan_town = self.area_index['桃園市'][0]['town_name']
        rows.append([f'桃園市{taoyuan_town}測試街9號', f'{tax_seq:08d}', '', '街邊一樓店面', '100000', '1151106', '獨資', 'N', '471900', '其他零售', '', '', '', '', '', ''])
        tax_seq += 1
        for fl in (1, 2, 4, 6, 8, 8, 10, 12):
            rows.append([f'桃園市{taoyuan_town}測試路10巷5弄1號{fl}樓', f'{tax_seq:08d}', '', f'巷弄住宅{tax_seq}', '1000000', '1151106', '有限公司', 'Y', '620199', '其他電腦程式設計', '', '', '', '', '', ''])
            tax_seq += 1
        with tempfile.TemporaryDirectory() as directory:
            catalog = self.build_fixture(directory, rows, office_buildings_only=True)
            self.assertEqual(catalog['total_count'], len(COUNTIES) * 8)
            self.assertEqual(catalog['total_buildings'], len(COUNTIES))
            self.assertEqual(catalog['coverage']['commercial_office_tenants'], len(COUNTIES) * 8)

    def test_entire_published_snapshot_matches_every_original_field(self):
        catalog = json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['data_mode'],'official')
        self.assertGreater(catalog['total_count'],100000)
        self.assertGreater(catalog['coverage']['commercial_buildings'],4000)
        self.assertEqual(len(catalog['counties']),22)
        qualifying_buildings, _, _ = identify_commercial_buildings(ROOT/'.cache/official/BGMOPEN1.zip',self.area_index)
        source_hashes, counts = {}, Counter()
        for row in read_tax_rows(ROOT/'.cache/official/BGMOPEN1.zip'):
            if not row[1]:
                continue
            if parse_floor_number(row[0]) is None or base_building_address(row[0]) not in qualifying_buildings:
                continue
            county_id, _ = locate_address(row[0],self.area_index)
            source_hashes.setdefault(county_id,hashlib.sha256()).update(canonical_json(row).encode('utf-8'))
            counts[county_id] += 1
        self.assertEqual(sum(counts.values()),catalog['total_count'])
        for county_id, county in catalog['counties'].items():
            digest, count = hashlib.sha256(), 0
            self.assertEqual(county['company_count'],counts[county_id])
            for shard in county['shards']:
                raw = (ROOT/'data'/shard['path']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),shard['sha256'])
                rows = json.loads(raw)['rows']
                self.assertEqual(len(rows),shard['count'])
                for row in rows:
                    self.assertEqual(len(row),17)
                    digest.update(canonical_json(row[:16]).encode('utf-8'))
                    count += 1
            self.assertEqual(count,counts[county_id])
            self.assertEqual(digest.hexdigest(),source_hashes[county_id].hexdigest())
        self.assertFalse((ROOT/'dist/data/counties').exists())
        self.assertFalse((ROOT/'dist/commercial_database_taiwan.json').exists())

if __name__ == '__main__':
    unittest.main()
