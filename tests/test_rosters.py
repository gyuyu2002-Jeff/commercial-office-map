import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from import_building_sources import read_source, import_sources


class RosterTests(unittest.TestCase):
    def spec(self):
        return dict(id='roster',title='測試清冊',url='https://example.invalid/roster',download_url='https://example.invalid?page={page}',
            county_id='taoyuan',format='json',name_field='name',address_field='address',page_size=2,minimum_rows=2)

    def test_all_pages_are_read_and_unrelated_personal_columns_are_not_retained(self):
        pages = [json.dumps([{'name':'大樓甲','address':'中正路1號','主任委員':'私人欄位'},
            {'name':'大樓乙管理負責人某人','address':'私人地址'}]).encode(), b'[]']
        with patch('import_building_sources.download',side_effect=pages):
            rows, hashes = read_source(self.spec())
        self.assertEqual(len(rows),2); self.assertEqual(len(hashes),2)
        self.assertEqual(set(rows[0]), {'name','address','record'})
        self.assertEqual((rows[1]['name'],rows[1]['address']),('',''))

    def test_repeated_page_is_rejected_and_not_treated_as_complete(self):
        page = json.dumps([{'name':'甲','address':'1號'},{'name':'乙','address':'2號'}]).encode()
        with patch('import_building_sources.download',return_value=page), self.assertRaisesRegex(ValueError,'Repeated'):
            read_source(self.spec())

    def test_failed_refresh_keeps_the_last_complete_roster_and_reports_the_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            config, output = Path(directory)/'config.json',Path(directory)/'inputs.json'
            config.write_text(json.dumps({'sources':[self.spec()]}),encoding='utf-8')
            pages = [json.dumps([{'name':'甲','address':'1號'},{'name':'乙','address':'2號'}]).encode(),b'[]']
            with patch('import_building_sources.download',side_effect=pages): previous = import_sources(config,output)
            with patch('import_building_sources.download',side_effect=ConnectionError('offline')): current = import_sources(config,output)
            self.assertEqual(current['records'],previous['records'])
            self.assertEqual(current['sources'],previous['sources'])
            self.assertEqual(len(current['unavailable_sources']),1)
