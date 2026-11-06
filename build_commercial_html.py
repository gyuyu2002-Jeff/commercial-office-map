"""Build a complete official tax-registration snapshot for GitHub Pages."""
import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import unicodedata
import zipfile
from urllib.parse import urlsplit
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from fetch_official_data import fetch_sources

ROOT = Path(__file__).resolve().parent
SHARD_SIZE = 10000
MAX_SITE_BYTES = 950_000_000
HEADERS = ['營業地址','統一編號','總機構統一編號','營業人名稱','資本額','設立日期','組織別名稱','使用統一發票','行業代號','名稱','行業代號1','名稱1','行業代號2','名稱2','行業代號3','名稱3']
COLUMNS = ['address','tax_id','head_office_tax_id','name','capital','established','organization','invoice','industry_code','industry_name','industry_code_1','industry_name_1','industry_code_2','industry_name_2','industry_code_3','industry_name_3','district_id']
COUNTIES = dict(zip(
    ['taipei','new_taipei','keelung','taoyuan','hsinchu_city','hsinchu_county','yilan','taichung','miaoli','changhua','nantou','yunlin','kaohsiung','tainan','chiayi_city','chiayi_county','pingtung','hualien','taitung','penghu','kinmen','lienchiang'],
    ['臺北市','新北市','基隆市','桃園市','新竹市','新竹縣','宜蘭縣','臺中市','苗栗縣','彰化縣','南投縣','雲林縣','高雄市','臺南市','嘉義市','嘉義縣','屏東縣','花蓮縣','臺東縣','澎湖縣','金門縣','連江縣']))
ICONS = ('apple-touch-icon.png','favicon-16x16.png','favicon-32x32.png','favicon.ico','favicon.svg','icon-192.png','icon-512.png')

def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def version_content(value):
    if isinstance(value, dict):
        return {key: version_content(child) for key, child in value.items()
                if key not in ('retrieved_at', 'downloaded_at', 'generated_at')}
    if isinstance(value, list):
        return [version_content(child) for child in value]
    return value

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def normal_address(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value).replace('台', '臺'))

def locate_address(address, area_index):
    normalized = normal_address(address)
    for county_id, name in COUNTIES.items():
        if normalized.startswith(name):
            tail = normalized[len(name):]
            for area in area_index.get(name, []):
                if tail.startswith(normal_address(area['town_name'])):
                    return county_id, area['town_code']
            return county_id, county_id + '_unknown'
    return 'unknown', 'unknown'

def parse_source_date(value):
    match = re.fullmatch(r'(\d{2})-([A-Z]{3})-(\d{2})', value)
    months = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()
    if not match or match[2] not in months:
        raise ValueError('Unrecognized tax snapshot date')
    return datetime(2000 + int(match[3]), months.index(match[2]) + 1, int(match[1])).date().isoformat()

def read_tax_rows(archive):
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if name.lower().endswith('.csv')]
        if len(names) != 1:
            raise ValueError('Expected one official CSV')
        with bundle.open(names[0]) as binary, io.TextIOWrapper(binary, encoding='utf-8-sig', newline='') as source:
            reader = csv.reader(source)
            if next(reader, None) != HEADERS:
                raise ValueError('Official CSV columns changed; refusing incomplete publication')
            yield from reader

def stock_enrichment(source_dir):
    mappings = [
        ('twse', '上市', {'tax_id':'營利事業統一編號','name':'公司名稱','stock_code':'公司代號','phone':'總機電話','chairperson':'董事長','website':'網址','date':'出表日期'}),
        ('tpex', '上櫃', {'tax_id':'UnifiedBusinessNo.','name':'CompanyName','stock_code':'SecuritiesCompanyCode','phone':'Telephone','chairperson':'Chairman','website':'WebAddress','date':'Date'})]
    manifest = json.loads((source_dir / 'manifest.json').read_text(encoding='utf-8'))
    result = {}
    for key, market, mapping in mappings:
        records = json.loads((source_dir / f'{key}.json').read_bytes())
        if not isinstance(records, list) or len(records) < 500:
            raise ValueError(f'Incomplete {key} company data')
        for record in records:
            tax_id = str(record.get(mapping['tax_id'], '')).strip()
            if not re.fullmatch(r'[0-9]{8}', tax_id) or tax_id == '00000000':
                continue
            item = {field: str(record.get(column, '')).replace('\\u3000', ' ').strip() for field, column in mapping.items() if field != 'tax_id'}
            item['website_raw'] = item['website']
            candidate = item['website']
            if re.match(r'^[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?$', candidate, re.I):
                candidate = 'https://' + candidate
            try:
                parsed = urlsplit(candidate)
                item['website'] = candidate if parsed.scheme.lower() in ('http','https') and parsed.hostname and not re.search(r'\s', candidate) else ''
            except ValueError:
                item['website'] = ''
            item.update(market=market, source_url=manifest[key]['url'])
            if tax_id in result:
                raise ValueError(f'Ambiguous listed company join: {tax_id}')
            result[tax_id] = item
    return result

def prepare_data(archive, output, geography, manifest, enrichment, industry_sections, min_records=1000000):
    output = Path(output)
    (output / 'shards').mkdir(parents=True, exist_ok=True)
    area_index = {}
    for area in geography['areas']:
        area_index.setdefault(normal_address(area['county_name']), []).append(area)
    for areas in area_index.values():
        areas.sort(key=lambda area: len(area['town_name']), reverse=True)
    counties = {}
    for county_id, name in COUNTIES.items():
        areas = area_index.get(name, [])
        if not areas:
            raise ValueError(f'Missing official geography for {name}')
        centers = [area['center'] for area in areas]
        center = [sorted(point[axis] for point in centers)[len(centers) // 2] for axis in (0, 1)]
        counties[county_id] = {'name':name, 'center':center, 'zoom':10, 'company_count':0, 'districts':[], 'shards':[]}
    counts, district_counts, industries = Counter(), Counter(), {}
    buffers = {key: [] for key in counties}
    seen_ids, source_date, row_count = set(), None, 0
    matched_enrichment = {}
    def flush(county_id):
        rows = buffers[county_id]
        if not rows:
            return
        shards = counties[county_id]['shards']
        relative = f'shards/{county_id}-{len(shards):03d}.json'
        raw = (canonical_json({'rows': rows}) + '\n').encode('utf-8')
        (output / relative).write_bytes(raw)
        shards.append({'path':relative, 'count':len(rows), 'sha256':hashlib.sha256(raw).hexdigest()})
        buffers[county_id] = []
    for row in read_tax_rows(archive):
        if len(row) != len(HEADERS):
            raise ValueError(f'Unexpected column count at record {row_count + 1}')
        if not row[1] and not any(row[1:]) and source_date is None and row_count == 0:
            source_date = parse_source_date(row[0])
            continue
        tax_id = row[1]
        if not re.fullmatch(r'[0-9]{8}', tax_id) or not row[0] or not row[3]:
            raise ValueError(f'Invalid company identity at record {row_count + 1}')
        if tax_id in seen_ids:
            raise ValueError(f'Duplicate official tax ID: {tax_id}')
        if row[4] and not re.fullmatch(r'[0-9]+', row[4]):
            raise ValueError(f'Invalid official capital for {tax_id}')
        seen_ids.add(tax_id)
        county_id, district_id = locate_address(row[0], area_index)
        if county_id not in counties:
            counties[county_id] = {'name':'地址待分類','center':[23.7,121],'zoom':7,'company_count':0,'districts':[],'shards':[]}
            buffers[county_id] = []
        buffers[county_id].append(row + [district_id])
        counts[county_id] += 1
        district_counts[(county_id, district_id)] += 1
        row_count += 1
        for index in (8, 10, 12, 14):
            if row[index] and row[index + 1]:
                industries[row[index]] = row[index + 1]
        if tax_id in enrichment:
            matched_enrichment[tax_id] = enrichment[tax_id]
        if len(buffers[county_id]) >= SHARD_SIZE:
            flush(county_id)
    if source_date is None or row_count < min_records or any(counts[key] == 0 for key in COUNTIES):
        raise ValueError('Incomplete nationwide snapshot; retain previous deployment')
    for county_id, county in counties.items():
        flush(county_id)
        county['company_count'] = counts[county_id]
        for area in sorted(area_index.get(county['name'], []), key=lambda area: area['town_code']):
            county['districts'].append({'id':area['town_code'],'name':area['town_name'],'center':area['center'],
                'company_count':district_counts[(county_id, area['town_code'])],'zoom':12})
        unknown_id = 'unknown' if county_id == 'unknown' else county_id + '_unknown'
        if district_counts[(county_id, unknown_id)]:
            county['districts'].append({'id':unknown_id,'name':'行政區待分類','company_count':district_counts[(county_id, unknown_id)]})
        if sum(shard['count'] for shard in county['shards']) != county['company_count']:
            raise ValueError('County row reconciliation failed')
        if sum(district['company_count'] for district in county['districts']) != county['company_count']:
            raise ValueError('District row reconciliation failed')
    catalog = {'schema_version':2,'data_mode':'official','columns':COLUMNS,'total_count':row_count,'counties':counties,
        'industries':industries,'industry_sections':industry_sections.get('sections',industry_sections),'enrichment':matched_enrichment,
        'industry_source':industry_sections.get('source',{}),
        'industry_classification_version':industry_sections.get('classification_version'),
        'source':dict(manifest['tax'],source_date=source_date),
        'supplemental_sources':{key:manifest[key] for key in ('twse','tpex')}, 'geography_source':geography['source'],
        'coverage':{'active_tax_registrations':row_count,'unique_tax_ids':len(seen_ids),'source_fields_preserved':len(HEADERS),
            'listed_matches':len(matched_enrichment),'unclassified_count':sum(count for (_,district),count in district_counts.items() if district.endswith('unknown'))}}
    catalog['dataset_version'] = hashlib.sha256(canonical_json(version_content(catalog)).encode('utf-8')).hexdigest()
    catalog['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    (output / 'catalog.json').write_text(canonical_json(catalog) + '\n', encoding='utf-8')
    return catalog

def build_site(root=ROOT, output=None, source_dir=None, download=False):
    root = Path(root).resolve()
    output = Path(output).resolve() if output else root / 'dist'
    if output == root or output in root.parents:
        raise ValueError('Deployment output must be separate from source directory')
    source_dir = Path(source_dir).resolve() if source_dir else root / '.cache' / 'official'
    if download or not (source_dir / 'manifest.json').exists():
        fetch_sources(source_dir)
    manifest = json.loads((source_dir / 'manifest.json').read_text(encoding='utf-8'))
    for key, filename in (('tax','BGMOPEN1.zip'),('twse','twse.json'),('tpex','tpex.json')):
        if sha256_file(source_dir / filename) != manifest[key]['sha256']:
            raise ValueError(f'Source checksum mismatch: {key}')
    geography = json.loads((root / 'config' / 'areas.json').read_text(encoding='utf-8'))
    sections = json.loads((root / 'config' / 'industry_sections.json').read_text(encoding='utf-8'))
    # Remove only explicitly resolved generated data, so no obsolete demo shard can be published.
    for target in (output / 'data', root / 'data'):
        if target.exists():
            if target.resolve().parent not in (root, output):
                raise ValueError('Unexpected generated-data directory')
            shutil.rmtree(target)
    catalog = prepare_data(source_dir / 'BGMOPEN1.zip', output / 'data', geography, manifest, stock_enrichment(source_dir), sections)
    catalog['app_version'] = hashlib.sha256(b''.join((root / asset).read_bytes() for asset in
        ('assets/app.js', 'assets/core.js', 'assets/search-worker.js'))).hexdigest()[:16]
    (output / 'data' / 'catalog.json').write_text(canonical_json(catalog) + '\n', encoding='utf-8')
    html = (root / 'src' / 'index.html').read_text(encoding='utf-8')
    for asset in ('assets/styles.css','assets/core.js','assets/app.js'):
        html = html.replace('"' + asset + '"', '"' + asset + '?v=' + sha256_file(root / asset)[:12] + '"')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(html, encoding='utf-8')
    (root / 'index.html').write_text(html, encoding='utf-8')
    shutil.copytree(output / 'data', root / 'data')
    shutil.copytree(root / 'assets', output / 'assets', dirs_exist_ok=True)
    for icon in ICONS:
        shutil.copy2(root / icon, output / icon)
    (output / '.nojekyll').write_text('', encoding='utf-8')
    total_bytes = sum(path.stat().st_size for path in output.rglob('*') if path.is_file())
    if total_bytes > MAX_SITE_BYTES:
        raise ValueError(f'Pages artifact exceeds safe capacity: {total_bytes} bytes')
    print(f"Built {catalog['total_count']:,} official records; snapshot {catalog['source']['source_date']}; {total_bytes:,} bytes")
    return catalog

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--source-dir', type=Path)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    build_site(output=args.output, source_dir=args.source_dir, download=args.download)

if __name__ == '__main__':
    main()
