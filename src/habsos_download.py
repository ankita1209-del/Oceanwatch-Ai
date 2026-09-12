import os
import requests
import json
import pandas as pd


OUT_PATH = 'data/raw/habsos.csv'
META_PATH = 'data/metadata/habsos_source.json'

def try_urls():
    urls = [
        'https://www.ncei.noaa.gov/access/habsos/habsos.csv',
        'https://www.ncei.noaa.gov/access/services/data/v1?dataset=habsos&format=csv',
        'https://www.ncei.noaa.gov/access/habsos'
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=30)
            if r.status_code == 200 and len(r.content) > 100:
                # Save
                with open(OUT_PATH, 'wb') as f:
                    f.write(r.content)
                with open(META_PATH, 'w') as m:
                    json.dump({'url': u, 'status': 'downloaded'}, m, indent=2)
                print('Downloaded HABSOS from', u)
                return True
        except Exception:
            continue
    return False


def try_erddap_search():
    # Try coastwatch ERDDAP search CSV for habsos
    search_url = 'https://coastwatch.pfeg.noaa.gov/erddap/search/index.csv?searchFor=habsos'
    try:
        df = pd.read_csv(search_url)
        df.to_csv('data/metadata/erddap_habsos_search.csv', index=False)
        with open(META_PATH, 'w') as m:
            json.dump({'erddap_search_rows': len(df)}, m, indent=2)
        print('ERDDAP search saved')
        return True
    except Exception:
        return False


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)

    ok = try_urls()
    if not ok:
        print('Direct URLs failed, trying ERDDAP search...')
        ok2 = try_erddap_search()
        if not ok2:
            print('HABSOS download failed. See data/metadata for logs.')
            with open(META_PATH, 'w') as m:
                json.dump({'status': 'failed'}, m, indent=2)
            return
    # Quick inspect
    try:
        df = pd.read_csv(OUT_PATH)
        print('HABSOS rows:', len(df))
        cols = df.columns.tolist()
        with open(META_PATH, 'r') as m:
            meta = json.load(m)
        meta.update({'rows': len(df), 'columns': cols})
        with open(META_PATH, 'w') as m:
            json.dump(meta, m, indent=2)
    except Exception:
        print('Downloaded file may not be CSV or is missing; check', OUT_PATH)


if __name__ == '__main__':
    main()
