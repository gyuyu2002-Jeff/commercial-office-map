"""Read complete configured public rosters; retain only names, addresses and provenance."""
import argparse
import csv
import hashlib
import io
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def xlsx_rows(raw):
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings = [''.join(n.itertext()) for n in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        rels = {n.attrib['Id']: n.attrib['Target'] for n in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet', ns):
            if not sheet.attrib['name'].endswith('區'):
                continue  # District sheets only; the city-wide sheet duplicates them.
            target = rels[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            filename = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            for row in ET.fromstring(archive.read(filename)).findall('s:sheetData/s:row', ns):
                values = {}
                for cell in row.findall('s:c', ns):
                    value = cell.findtext('s:v', '', ns)
                    if cell.attrib.get('t') == 's': value = strings[int(value)]
                    elif cell.attrib.get('t') == 'inlineStr': value = ''.join(cell.find('s:is', ns).itertext())
                    values[cell.attrib['r'].rstrip('0123456789')] = value
                if row.attrib['r'] != '1' and values.get('A') and values.get('B'):
                    yield {'name': values['A'], 'address': values['B'], 'record': sheet.attrib['name'] + '!A' + row.attrib['r'] + ':B' + row.attrib['r']}


def download(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return response.read()
        except Exception:
            if attempt == 2: raise
            time.sleep(attempt + 1)


def import_sources(config_path, output):
    output = Path(output)
    previous = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {'sources':{},'records':[]}
    specs = json.loads(Path(config_path).read_text(encoding='utf-8'))['sources']
    result = {'schema_version': 1, 'sources': {}, 'records': [], 'unavailable_sources': []}
    for spec in specs:
        try:
            records, hashes = read_source(spec)
        except Exception as error:
            reason = '本次無法取得並驗證完整清冊；未將部分分頁列入。'
            result['unavailable_sources'].append(dict(id=spec['id'],title=spec['title'],url=spec['url'],unavailable_reason=reason))
            if spec['id'] in previous['sources']:
                result['unavailable_sources'][-1]['unavailable_reason'] += '沿用上次完整快照，日期：' + previous['sources'][spec['id']]['checked_at'] + '。'
                result['sources'][spec['id']] = previous['sources'][spec['id']]
                result['records'].extend(row for row in previous['records'] if row['source_id'] == spec['id'])
                print('Retained previous verified roster: ' + spec['id'], flush=True)
            else:
                print('Unavailable complete roster: ' + spec['id'], flush=True)
                if spec.get('required'): raise ValueError('Required complete roster unavailable: ' + spec['id']) from error
            continue
        meta = {key: spec[key] for key in ('title', 'url', 'download_url', 'county_id')}
        meta.update(rows=len(records), pages=len(hashes), page_sha256=hashes,
            sha256=hashlib.sha256(''.join(hashes).encode()).hexdigest(), checked_at=datetime.now(timezone.utc).date().isoformat())
        result['sources'][spec['id']] = meta
        result['records'].extend(dict(record, source_id=spec['id'], county_id=spec['county_id']) for record in records)
        print(f"Imported {spec['id']}: {len(records):,} source rows, {len(hashes)} pages", flush=True)
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.part')
    temporary.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temporary.replace(output)
    return result


def read_source(spec):
    records, hashes, previous_pages = [], [], set()
    for page in range(300):
        url = spec['download_url'].replace('{page}', str(page)).replace('{start}', str(page * 100 + 1))
        raw = download(url)
        digest = hashlib.sha256(raw).hexdigest()
        if digest in previous_pages: raise ValueError('Repeated roster page: ' + spec['id'])
        previous_pages.add(digest); hashes.append(digest)
        if spec['format'] == 'xlsx':
            entries = list(xlsx_rows(raw))
        else:
            if spec['format'] == 'csv':
                reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig').lstrip('\ufeff')))
                if not {spec['name_field'], spec['address_field']} <= set(reader.fieldnames or []):
                    raise ValueError('Roster columns changed: ' + spec['id'])
                rows = list(reader)
            else:
                rows = json.loads(raw)
                if spec['format'] == 'apm': rows = rows['data']
                if not isinstance(rows, list): raise ValueError('Invalid roster: ' + spec['id'])
            entries = [{'name': r[spec['name_field']], 'address': r[spec['address_field']],
                'record': 'row ' + str(len(records) + i + 1)} for i, r in enumerate(rows)]
        records.extend(entries)
        if not spec.get('page_size') or len(entries) < spec['page_size']: break
    else:
        raise ValueError('Roster pagination did not finish: ' + spec['id'])
    if len(records) < spec['minimum_rows']: raise ValueError('Incomplete roster: ' + spec['id'])
    for record in records:
        if '管理負責人' in str(record['name']):
            record['name'] = record['address'] = ''  # Personal manager names/addresses are not retained.
    return records, hashes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'config/building_import_sources.json')
    parser.add_argument('--output', type=Path, default=ROOT/'.cache/buildings/inputs.json')
    args = parser.parse_args()
    import_sources(args.config, args.output)
