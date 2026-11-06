"""Download public official sources atomically; never substitute invented data."""
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCES = {
    'tax': {'filename': 'BGMOPEN1.zip', 'url': 'https://eip.fia.gov.tw/data/BGMOPEN1.zip', 'dataset_url': 'https://data.gov.tw/dataset/9400', 'publisher': '財政部財政資訊中心', 'license': 'https://data.gov.tw/license', 'minimum_bytes': 30000000},
    'twse': {'filename': 'twse.json', 'url': 'https://openapi.twse.com.tw/v1/opendata/t187ap03_L', 'dataset_url': 'https://openapi.twse.com.tw/', 'publisher': '臺灣證券交易所', 'minimum_bytes': 100000},
    'tpex': {'filename': 'tpex.json', 'url': 'https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O', 'dataset_url': 'https://www.tpex.org.tw/openapi/', 'publisher': '證券櫃檯買賣中心', 'minimum_bytes': 100000},
}

def fetch_sources(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, spec in SOURCES.items():
        destination = directory / spec['filename']
        partial = destination.with_suffix(destination.suffix + '.part')
        for attempt in range(3):
            try:
                request = urllib.request.Request(spec['url'], headers={'User-Agent': 'commercial-office-map/2.0 (public open data)'})
                digest, count = hashlib.sha256(), 0
                with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as output:
                    last_modified = response.headers.get('Last-Modified')
                    for block in iter(lambda: response.read(1024 * 1024), b''):
                        output.write(block)
                        digest.update(block)
                        count += len(block)
                if count < spec['minimum_bytes']:
                    raise ValueError(f'Unexpectedly small source: {key}')
                if key != 'tax' and not isinstance(json.loads(partial.read_bytes()), list):
                    raise ValueError(f'Invalid company JSON: {key}')
                partial.replace(destination)
                manifest[key] = {k: v for k, v in spec.items() if k not in ('filename', 'minimum_bytes')}
                manifest[key].update(sha256=digest.hexdigest(), bytes=count, last_modified=last_modified,
                    retrieved_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
                print(f'Downloaded {key}: {count:,} bytes', flush=True)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
    temporary = directory / 'manifest.json.part'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(directory / 'manifest.json')
    return manifest

if __name__ == '__main__':
    fetch_sources(Path(__file__).resolve().parent / '.cache' / 'official')
