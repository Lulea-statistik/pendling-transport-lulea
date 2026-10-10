#!/usr/bin/env python3
"""Inspect published Norrbotten NVDB GPKG; no raw data persists after run."""
import json
import os
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://lastkajen.trafikverket.se/api'
PACKAGE_ID = 10155
FILE_NAME = 'Norrbottens_län_GeoPackage.zip'

def api(path, bearer=None, form=None):
    headers = {'Accept': 'application/json'}
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
    data = None
    if form is not None:
        data = urlencode(form).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = Request(BASE + path, headers=headers, data=data)
    with urlopen(req, timeout=120) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RuntimeError('Oversized API response')
    return json.loads(raw.decode('utf-8'))

def gpkg_metadata(path):
    db = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    try:
        tables = db.execute('SELECT table_name, data_type, srs_id FROM gpkg_contents').fetchall()
        geometries = db.execute('SELECT table_name, column_name, geometry_type_name, srs_id FROM gpkg_geometry_columns').fetchall()
        crs = db.execute('SELECT srs_id, organization, organization_coordsys_id FROM gpkg_spatial_ref_sys').fetchall()
        return {
            'tables': [dict(zip(('name', 'type', 'srs_id'), row)) for row in tables],
            'geometry_columns': [dict(zip(('table', 'column', 'geometry_type', 'srs_id'), row)) for row in geometries],
            'coordinate_systems': [dict(zip(('srs_id', 'authority', 'code'), row)) for row in crs],
        }
    finally:
        db.close()

def main():
    user = os.environ.get('LASTKAJEN_USERNAME')
    password = os.environ.get('LASTKAJEN_PASSWORD')
    if not user or not password:
        raise RuntimeError('Missing credentials')
    login = api('/Identity/Login', form={'UserName': user, 'Password': password})
    bearer = login.get('access_token') if isinstance(login, dict) else None
    if not bearer:
        raise RuntimeError('No access token returned')
    files = api('/DataPackage/GetDataPackageFiles?' + urlencode({'id': PACKAGE_ID}), bearer=bearer)
    if not isinstance(files, list) or not any(isinstance(f, dict) and f.get('name') == FILE_NAME for f in files):
        raise RuntimeError('Target file absent from package')
    ticket = api('/file/GetDataPackageDownloadToken?' + urlencode({'id': PACKAGE_ID, 'fileName': FILE_NAME}), bearer=bearer)
    if not isinstance(ticket, str):
        raise RuntimeError('Unexpected one-time ticket response')
    with tempfile.TemporaryDirectory() as directory:
        archive_path = Path(directory) / 'norrbotten.zip'
        url = BASE + '/File/GetDataPackageFile?' + urlencode({'token': ticket})
        size = 0
        with urlopen(url, timeout=180) as response, archive_path.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 1_500_000_000:
                    raise RuntimeError('Download exceeds 1.5 GB limit')
                output.write(chunk)
        result = {
            'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
            'package_id': PACKAGE_ID, 'source_file': FILE_NAME, 'archive_bytes': size,
            'archive_entries': [], 'geopackages': [],
        }
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                result['archive_entries'].append({'name': entry.filename, 'uncompressed_bytes': entry.file_size})
                if not entry.filename.lower().endswith('.gpkg'):
                    continue
                if entry.file_size > 8_000_000_000:
                    raise RuntimeError('Geopackage exceeds extraction limit')
                extracted = Path(directory) / ('part_' + str(len(result['geopackages'])) + '.gpkg')
                with archive.open(entry) as src, extracted.open('wb') as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                result['geopackages'].append({'file': entry.filename, **gpkg_metadata(extracted)})
                extracted.unlink()
        Path('lastkajen_schema.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Schema inventory ready:', len(result['geopackages']), 'GeoPackage files')

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Inspection failed. Check API access, format, available runner disk space.', file=sys.stderr)
        sys.exit(1)
