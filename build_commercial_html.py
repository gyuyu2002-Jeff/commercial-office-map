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
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value).replace('台', '臺').replace('\\u3000', ''))

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
    catalog = {'schema_version':2,'data_mode':'official','data_scope':'office' if office_buildings_only else 'registry','columns':COLUMNS,'total_count':row_count,'total_buildings':total_buildings,'counties':counties,
        'industries':industries,'industry_sections':industry_sections.get('sections',industry_sections),'enrichment':matched_enrichment,
        'industry_source':industry_sections.get('source',{}),
        'industry_classification_version':industry_sections.get('classification_version'),
        'source':dict(manifest['tax'],source_date=source_date),
        'supplemental_sources':{key:manifest[key] for key in ('twse','tpex')}, 'geography_source':geography['source'],
        'building_filter':COMMERCIAL_BUILDING_RULE if office_buildings_only else None,
        'coverage':{'active_tax_registrations':source_total_rows if source_total_rows is not None else row_count,
            'commercial_office_tenants':row_count if office_buildings_only else None,'commercial_buildings':total_buildings if office_buildings_only else None,
            'published_registrations':row_count,
            'unique_tax_ids':len(seen_ids),'source_fields_preserved':len(HEADERS),
            'listed_matches':len(matched_enrichment),'unclassified_count':sum(count for (_,district),count in district_counts.items() if district.endswith('unknown'))}}
    catalog['dataset_version'] = hashlib.sha256(canonical_json(version_content(catalog)).encode('utf-8')).hexdigest()
    catalog['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    (output / 'catalog.json').write_text(canonical_json(catalog) + '\n', encoding='utf-8')
    return catalog

def single_roster_door(address):
    text = normal_address(address)
    if text.count('號') != 1 or any(token in text for token in ('至', '~', '～', '、', '及', '等', '(', ')', '；', ';', ',')):
        return None
    if '-' in text.split('號')[0] or not re.search(r'\d+(?:之\d+)?號', text):
        return None  # Hyphens can mean either a range or a sub-number; never guess.
    return base_building_address(text)


def build_named_config(archive, manual, imported, geography, manifest):
    config = json.loads(json.dumps(manual))
    config['sources'].update(imported['sources'])
    tax_source = dict(manifest['tax'], title='財政部全國稅籍：大樓管理組織登記名稱',
        checked_at=parse_source_date(next(read_tax_rows(archive))[0]))
    config['sources']['tax_management'] = tax_source
    area_index = {}
    for area in geography['areas']:
        area_index.setdefault(normal_address(area['county_name']), []).append(area)
    for areas in area_index.values(): areas.sort(key=lambda a: len(a['town_name']), reverse=True)
    candidates = [dict(row, name_status='government_registry') for row in imported['records']]
    missing_districts = set()
    for row in candidates:
        row['name'] = row['name'] if isinstance(row['name'], str) else ''
        row['address'] = row['address'] if isinstance(row['address'], str) else ''
        if row['address'] and not normal_address(row['address']).startswith(COUNTIES[row['county_id']]):
            row['address'] = COUNTIES[row['county_id']] + row['address']
        base = single_roster_door(row['address'])
        county_id, district_id = locate_address(row['address'], area_index)
        if base and county_id == row['county_id'] and district_id.endswith('_unknown'): missing_districts.add(base)
    observed = {key: set() for key in missing_districts}
    missing_counties = {key for key,name in COUNTIES.items() if any(address.startswith(name) for address in observed)}
    missing_prefixes = tuple(COUNTIES[key] for key in missing_counties)
    for row in read_tax_rows(archive):
        if not row[1]: continue
        is_committee = row[3].endswith('管理委員會') and re.search(r'大[樓廈厦]|公寓|社區|廣場|商業|商務|經貿|金融|商辦|科技', row[3])
        if not is_committee and not normal_address(row[0]).startswith(missing_prefixes): continue
        county_id, district_id = locate_address(row[0], area_index)
        if county_id not in COUNTIES or district_id.endswith('_unknown'): continue
        if county_id in missing_counties:
            district = next(a['town_name'] for a in area_index[COUNTIES[county_id]] if a['town_code'] == district_id)
            base = base_building_address(row[0])
            key = base.replace(COUNTIES[county_id] + district, COUNTIES[county_id], 1)
            if key in observed: observed[key].add(base)
        if is_committee:
            candidates.append({'name':row[3], 'address':row[0], 'source_id':'tax_management', 'county_id':county_id,
                'record':row[1], 'name_status':'tax_registry'})
    occupied = {address for building in config['buildings'] for address in building['addresses']}
    report = {key: {'input':0,'accepted':0,'duplicate_door':0,'ambiguous_address':0,'unknown_district':0,'unsupported_name':0,'missing_fields':0}
        for key in config['sources'] if key in imported['sources'] or key == 'tax_management'}
    for row in candidates:
        stat = report[row['source_id']]; stat['input'] += 1
        name = str(row['name']).strip()
        if not name or not row['address']:
            stat['missing_fields'] += 1; continue
        if not name or '管理負責人' in name or re.fullmatch(r'(?:公寓|大樓|大廈|大厦|社區|管理委員會)+', name):
            stat['unsupported_name'] += 1; continue
        base = single_roster_door(row['address'])
        if not base: stat['ambiguous_address'] += 1; continue
        if base in observed and len(observed[base]) == 1: base = next(iter(observed[base]))
        county_id, district_id = locate_address(base, area_index)
        if county_id != row['county_id'] or district_id.endswith('_unknown'):
            stat['unknown_district'] += 1; continue
        if base in occupied: stat['duplicate_door'] += 1; continue
        district = next(a['town_name'] for a in area_index[COUNTIES[county_id]] if a['town_code'] == district_id)
        key = 'building_' + hashlib.sha256((name+'|'+base).encode()).hexdigest()[:12]
        config['buildings'].append({'id':key,'name':name,'aliases':[],'name_status':row['name_status'],
            'county_id':county_id,'district':district,'addresses':[base],
            'checked_at':config['sources'][row['source_id']]['checked_at'],
            'references':[{'source_id':row['source_id'],'record':row['record'],'name':name,'address':row['address']}],
            'note':'此為政府名冊或稅籍登記的管理組織名稱與單一門牌，不代表已實地核對招牌、建築用途或所有門牌。'})
        occupied.add(base); stat['accepted'] += 1
    for stat in report.values():
        if stat['input'] != sum(value for key,value in stat.items() if key != 'input'):
            raise ValueError('Building-name import reconciliation failed')
    config['import_report'] = report
    config['updated_at'] = max(source['checked_at'] for source in config['sources'].values())
    config['unavailable_sources'] = imported.get('unavailable_sources', [])
    config['coverage_note'] = '完整保留本期全國營業中稅籍；大樓名稱僅包含有來源的管理清冊、登記管理組織與人工核對資料。管理組織名稱不等於現場招牌；地址範圍或無法唯一對應者未自動配對。名稱與實際租戶不保證全台完整。'
    return config


def attach_named_buildings(catalog, config, data_dir):
    if config.get('schema_version') != 1 or not config.get('buildings'):
        raise ValueError('Named-building configuration is missing or invalid')
    sources = config['sources']
    for source in sources.values():
        if urlsplit(source['url']).scheme != 'https' or not source.get('checked_at'):
            raise ValueError('Named-building sources require an HTTPS URL and verification date')
    seen_ids, seen_addresses, counts, door_shards = set(), set(), {}, {}
    buildings = []
    for building in config['buildings']:
        county = catalog['counties'].get(building['county_id'])
        addresses = building['addresses']
        name_status = building.get('name_status', 'verified')
        if name_status not in ('verified', 'address_only', 'government_registry', 'tax_registry'):
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
            counts[building['county_id']] = Counter()
            door_shards[building['county_id']] = {}
            for shard in county['shards']:
                for row in json.loads((data_dir / shard['path']).read_text(encoding='utf-8'))['rows']:
                    door = base_building_address(row[0])
                    counts[building['county_id']][door] += 1
                    door_shards[building['county_id']].setdefault(door, set()).add(shard['path'])
        address_counts = {address: counts[building['county_id']][address] for address in addresses}
        paths = set().union(*(door_shards[building['county_id']].get(address, set()) for address in addresses))
        buildings.append(dict(building, address_counts=address_counts, company_count=sum(address_counts.values()),
            shard_paths=[shard['path'] for shard in county['shards'] if shard['path'] in paths]))
    catalog.update(named_buildings=buildings, building_name_sources=sources,
        building_names_updated_at=config['updated_at'], building_names_coverage=config['coverage_note'],
        building_import_report=config.get('import_report', {}), unavailable_building_sources=config.get('unavailable_sources', []))
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
    from import_building_sources import import_sources
    roster_path = root / '.cache/buildings/inputs.json'
    if download or not roster_path.exists():
        import_sources(root / 'config/building_import_sources.json', roster_path)
    imported = json.loads(roster_path.read_text(encoding='utf-8'))
    named_config = build_named_config(source_dir / 'BGMOPEN1.zip',
        json.loads((root / 'config/named_buildings.json').read_text(encoding='utf-8')), imported, geography, manifest)
    print(f"Prepared {len(named_config['buildings']):,} sourced name/door entries", flush=True)
    enrichment = stock_enrichment(source_dir)
    catalog = prepare_data(source_dir / 'BGMOPEN1.zip', output / 'data', geography, manifest, enrichment, sections)
    print(f"Prepared {catalog['total_count']:,} office-filtered records", flush=True)
    registry = prepare_data(source_dir / 'BGMOPEN1.zip', output / 'data/registry', geography, manifest, enrichment, sections, office_buildings_only=False)
    print(f"Prepared {registry['total_count']:,} full nationwide registrations", flush=True)
    attach_named_buildings(registry, named_config, output / 'data/registry')
    attach_named_buildings(catalog, named_config, output / 'data')
    full_names = {entry['id']:entry for entry in registry['named_buildings']}
    for entry in catalog['named_buildings']:
        entry['registry_company_count'] = full_names[entry['id']]['company_count']
    for county in registry['counties'].values():
        for shard in county['shards']: shard['path'] = 'registry/' + shard['path']
    for entry in registry['named_buildings']:
        entry['shard_paths'] = ['registry/' + path for path in entry['shard_paths']]
    coverage = {'source_rows':catalog['coverage']['active_tax_registrations'], 'registry_rows':registry['total_count'],
        'office_rows':catalog['total_count'], 'counties':[]}
    for county_id, county in registry['counties'].items():
        names = [entry for entry in registry['named_buildings'] if entry['county_id'] == county_id]
        statuses = Counter(entry.get('name_status','verified') for entry in names)
        coverage['counties'].append({'id':county_id,'name':county['name'],'registry_rows':county['company_count'],
            'office_rows':catalog['counties'].get(county_id,{}).get('company_count',0), 'name_sources':dict(statuses)})
    if coverage['source_rows'] != coverage['registry_rows']:
        raise ValueError('Full nationwide registration count does not match the source')
    catalog['nationwide_coverage'] = registry['nationwide_coverage'] = coverage
    app_version = hashlib.sha256(b''.join((root / asset).read_bytes() for asset in
        ('assets/app.js', 'assets/core.js', 'assets/search-worker.js'))).hexdigest()[:16]
    for item, filename in ((catalog, 'catalog.json'), (registry, 'registry/catalog.json')):
        item['app_version'] = app_version
        content = {key:value for key,value in item.items() if key not in ('dataset_version','app_version')}
        item['dataset_version'] = hashlib.sha256(canonical_json(version_content(content)).encode('utf-8')).hexdigest()
        (output / 'data' / filename).write_text(canonical_json(item) + '\n', encoding='utf-8')
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
