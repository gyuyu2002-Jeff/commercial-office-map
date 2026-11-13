"""Build a commercial-office-building snapshot from official tax-registration data for GitHub Pages."""
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
CORP_ORGS = frozenset({'股份有限公司','有限公司','本國公司設立之分公司','外國公司在臺分公司','外國公司認許及報備在臺營業之分公司'})
CN_DIGITS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
COMMERCIAL_BUILDING_RULE = {
    'exclude_substrings': ['巷', '弄'],
    'require_floor': True,
    'primary': {'min_tenants': 8, 'min_corporates': 5, 'min_upper_floors': 3, 'min_max_floor': 5},
    'county_fallback': {'min_tenants': 4, 'min_corporates': 3, 'min_upper_floors': 2, 'min_max_floor': 5},
}

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

def parse_floor_number(address):
    match = re.search(r'(\d+|[一二三四五六七八九十]+)樓', normal_address(address))
    if not match:
        return None
    token = match.group(1)
    if token.isdigit():
        return int(token)
    if token == '十':
        return 10
    if token.startswith('十'):
        return 10 + CN_DIGITS.get(token[1:], 0)
    if '十' in token:
        head, tail = token.split('十', 1)
        return CN_DIGITS.get(head, 0) * 10 + CN_DIGITS.get(tail, 0)
    return CN_DIGITS.get(token)

def _replace_cn_section(match):
    token = match.group(1)
    if token == '十':
        return '10段'
    if token.startswith('十') and len(token) == 2:
        return f'{10 + CN_DIGITS.get(token[1], 0)}段'
    return f'{CN_DIGITS.get(token, token)}段'

def base_building_address(address):
    text = normal_address(address)
    text = re.sub(r'^([^市縣]{2,3}[市縣][^區鄉鎮市]{1,4}[區鄉鎮市])([^\d號樓巷弄]{1,6}[村里])(?:\d+鄰)?(?=[^\d]+?(?:路|街|大道|段))', r'\1', text)
    text = re.sub(r'^([^市縣]{2,3}[市縣][^區鄉鎮市]{1,4}[區鄉鎮市])\d+鄰', r'\1', text)
    text = re.sub(r'(十[一二三四五六七八九]|[一二三四五六七八九十])段', _replace_cn_section, text)
    match = re.match(r'^(.+?\d+(?:[-之]\d+)?號)', text)
    if not match:
        return text
    return re.sub(r'(\d+)-(\d+號)$', r'\1之\2', match.group(1))

def qualify_building(base, total, corps, upper_floors, max_floor, criteria):
    if any(token in base for token in COMMERCIAL_BUILDING_RULE['exclude_substrings']):
        return False
    return (
        total >= criteria['min_tenants']
        and corps >= criteria['min_corporates']
        and len(upper_floors) >= criteria['min_upper_floors']
        and max_floor >= criteria['min_max_floor']
    )

def identify_commercial_buildings(archive, area_index):
    stats = {}
    seen_ids, source_date, row_count = set(), None, 0
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
        row_count += 1
        county_id, _ = locate_address(row[0], area_index)
        floor = parse_floor_number(row[0])
        if county_id in COUNTIES and floor is not None:
            base = base_building_address(row[0])
            entry = stats.get(base)
            if entry is None:
                entry = [county_id, 0, 0, set(), 0]
                stats[base] = entry
            entry[1] += 1
            if row[6] in CORP_ORGS:
                entry[2] += 1
            if floor >= 2:
                entry[3].add(floor)
            if floor > entry[4]:
                entry[4] = floor
    qualifying = {}
    counties_covered = set()
    for base, (county_id, total, corps, upper_floors, max_floor) in stats.items():
        if qualify_building(base, total, corps, upper_floors, max_floor, COMMERCIAL_BUILDING_RULE['primary']):
            qualifying[base] = county_id
            counties_covered.add(county_id)
    for base, (county_id, total, corps, upper_floors, max_floor) in stats.items():
        if county_id not in counties_covered and qualify_building(base, total, corps, upper_floors, max_floor, COMMERCIAL_BUILDING_RULE['county_fallback']):
            qualifying[base] = county_id
    return qualifying, row_count, source_date

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

def prepare_data(archive, output, geography, manifest, enrichment, industry_sections, min_records=100000, office_buildings_only=True):
    output = Path(output)
    (output / 'shards').mkdir(parents=True, exist_ok=True)
    area_index = {}
    for area in geography['areas']:
        area_index.setdefault(normal_address(area['county_name']), []).append(area)
    for areas in area_index.values():
        areas.sort(key=lambda area: len(area['town_name']), reverse=True)
    qualifying_buildings, source_total_rows, scan_date = (
        identify_commercial_buildings(archive, area_index) if office_buildings_only else (None, None, None)
    )
    building_counts = Counter(qualifying_buildings.values()) if qualifying_buildings is not None else Counter()
    counties = {}
    for county_id, name in COUNTIES.items():
        areas = area_index.get(name, [])
        if not areas:
            raise ValueError(f'Missing official geography for {name}')
        centers = [area['center'] for area in areas]
        center = [sorted(point[axis] for point in centers)[len(centers) // 2] for axis in (0, 1)]
        counties[county_id] = {'name':name, 'center':center, 'zoom':10, 'company_count':0, 'building_count':building_counts[county_id], 'districts':[], 'shards':[]}
    counts, district_counts, industries = Counter(), Counter(), {}
    buffers = {key: [] for key in counties}
    seen_ids, source_date, row_count = set(), scan_date, 0
    matched_enrichment = {}
    seen_building_bases = set()
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
        if not row[1] and not any(row[1:]) and row_count == 0 and len(seen_ids) == 0:
            parsed = parse_source_date(row[0])
            if source_date is None:
                source_date = parsed
            continue
        tax_id = row[1]
        if not re.fullmatch(r'[0-9]{8}', tax_id) or not row[0] or not row[3]:
            raise ValueError(f'Invalid company identity at record {row_count + 1}')
        if tax_id in seen_ids:
            raise ValueError(f'Duplicate official tax ID: {tax_id}')
        if row[4] and not re.fullmatch(r'[0-9]+', row[4]):
            raise ValueError(f'Invalid official capital for {tax_id}')
        seen_ids.add(tax_id)
        if qualifying_buildings is not None:
            if parse_floor_number(row[0]) is None:
                continue
            base = base_building_address(row[0])
            if base not in qualifying_buildings:
                continue
            seen_building_bases.add(base)
        else:
            seen_building_bases.add(base_building_address(row[0]))
        county_id, district_id = locate_address(row[0], area_index)
        if county_id not in counties:
            counties[county_id] = {'name':'地址待分類','center':[23.7,121],'zoom':7,'company_count':0,'building_count':0,'districts':[],'shards':[]}
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
    if qualifying_buildings is not None:
        for county_id in COUNTIES:
            counties[county_id]['building_count'] = building_counts[county_id]
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
    total_buildings = len(qualifying_buildings) if qualifying_buildings is not None else len(seen_building_bases)
    catalog = {'schema_version':2,'data_mode':'official','columns':COLUMNS,'total_count':row_count,'total_buildings':total_buildings,'counties':counties,
        'industries':industries,'industry_sections':industry_sections.get('sections',industry_sections),'enrichment':matched_enrichment,
        'industry_source':industry_sections.get('source',{}),
        'industry_classification_version':industry_sections.get('classification_version'),
        'source':dict(manifest['tax'],source_date=source_date),
        'supplemental_sources':{key:manifest[key] for key in ('twse','tpex')}, 'geography_source':geography['source'],
        'building_filter':COMMERCIAL_BUILDING_RULE if office_buildings_only else None,
        'coverage':{'active_tax_registrations':source_total_rows if source_total_rows is not None else row_count,
            'commercial_office_tenants':row_count,'commercial_buildings':total_buildings,
            'unique_tax_ids':len(seen_ids),'source_fields_preserved':len(HEADERS),
            'listed_matches':len(matched_enrichment),'unclassified_count':sum(count for (_,district),count in district_counts.items() if district.endswith('unknown'))}}
    catalog['dataset_version'] = hashlib.sha256(canonical_json(version_content(catalog)).encode('utf-8')).hexdigest()
    catalog['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    (output / 'catalog.json').write_text(canonical_json(catalog) + '\n', encoding='utf-8')
    return catalog

def attach_named_buildings(catalog, config, data_dir):
    if config.get('schema_version') != 1 or not config.get('buildings'):
        raise ValueError('Named-building configuration is missing or invalid')
    sources = config['sources']
    for source in sources.values():
        if urlsplit(source['url']).scheme != 'https' or not source.get('checked_at'):
            raise ValueError('Named-building sources require an HTTPS URL and verification date')
    seen_ids, seen_addresses, counts = set(), set(), {}
    buildings = []
    for building in config['buildings']:
        county = catalog['counties'].get(building['county_id'])
        addresses = building['addresses']
        name_status = building.get('name_status', 'verified')
        if name_status not in ('verified', 'address_only'):
            raise ValueError('Unknown building-name verification status')
        if name_status == 'address_only' and (building['aliases'] or len(addresses) != 1
                or building['name'] != addresses[0].removeprefix(COUNTIES[building['county_id']] + building['district'])):
            raise ValueError('Address-only entries must use the door text without invented names or aliases')
        if (not county or building['id'] in seen_ids or not building['name'].strip()
                or not addresses or not building.get('references') or not building.get('checked_at')
                or building['district'] not in {d['name'] for d in county['districts']}):
            raise ValueError('Invalid named-building identity, district or provenance')
        for reference in building['references']:
            if reference['source_id'] not in sources:
                raise ValueError('Unknown named-building source')
        for address in addresses:
            if (address in seen_addresses or base_building_address(address) != address
                    or not address.startswith(county['name'] + building['district']) or not address.endswith('號')):
                raise ValueError(f'Named-building address must be a unique, exact canonical door: {address}')
            seen_addresses.add(address)
        seen_ids.add(building['id'])
        if building['county_id'] not in counts:
            counts[building['county_id']] = Counter(
                base_building_address(row[0]) for shard in county['shards']
                for row in json.loads((data_dir / shard['path']).read_text(encoding='utf-8'))['rows'])
        address_counts = {address: counts[building['county_id']][address] for address in addresses}
        buildings.append(dict(building, address_counts=address_counts, company_count=sum(address_counts.values())))
    catalog.update(named_buildings=buildings, building_name_sources=sources,
        building_names_updated_at=config['updated_at'], building_names_coverage=config['coverage_note'])
    # Names, aliases and door associations are part of the published data version.
    content = {key: value for key, value in catalog.items() if key not in ('dataset_version', 'app_version')}
    catalog['dataset_version'] = hashlib.sha256(canonical_json(version_content(content)).encode('utf-8')).hexdigest()


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
    attach_named_buildings(catalog, json.loads((root / 'config/named_buildings.json').read_text(encoding='utf-8')), output / 'data')
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
    print(f"Built {catalog['total_count']:,} commercial-office records across {catalog['total_buildings']:,} buildings; snapshot {catalog['source']['source_date']}; {total_bytes:,} bytes")
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
