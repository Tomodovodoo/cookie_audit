"""Download versioned inputs; never call a global ranking a Dutch traffic ranking."""
import csv, hashlib, io, json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from exclusions import EXPLICIT,excluded as nsfw

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'CookieAuditResearch/0.1'}), timeout=60).read()
def write(name, value):
    (DATA/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
def main():
    sources = {
        'ranking': 'https://netapi.com/top-websites/nl/download/',
        'adult_filter': 'https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn-only/hosts',
        'trackers': 'https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json',
    }
    raw = {key: fetch(url) for key,url in sources.items()}
    write('sources.json', {key:{'url':url,'retrieved':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(raw[key]).hexdigest()} for key,url in sources.items()})
    (DATA/'ranking.csv').write_bytes(raw['ranking'])
    adult = {line.split()[1].removeprefix('www.') for line in raw['adult_filter'].decode().splitlines() if line.startswith(('0.0.0.0 ', '127.0.0.1 ')) and len(line.split())>1}
    adult |= EXPLICIT
    rows, excluded = [], []
    for item in csv.reader(io.StringIO(raw['ranking'].decode('utf-8-sig'))):
        if len(item)<2 or not item[0].isdigit(): continue
        rank, domain = int(item[0]), item[1].strip().lower().removeprefix('www.')
        if not re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}',domain): raise ValueError(domain)
        record = {'rank':rank,'domain':domain,'name':domain,'company':None,'cohort':'NetAPI Netherlands top 1000'}
        if nsfw(domain,adult):
            excluded.append({**record,'reason':'adult blocklist or conservative NSFW exclusion'}); continue
        rows.append(record)
    # User-requested calibration sites stay explicit if absent from the ranked sample.
    for domain in ['bol.com','abnamro.nl','rabobank.nl','nrc.nl','ad.nl','marktplaats.nl']:
        if not any(x['domain']==domain for x in rows): rows.append({'rank':None,'domain':domain,'name':domain,'company':None,'cohort':'user supplied calibration'})
    write('sites.json', rows)
    write('excluded.json', excluded)
    write('adult-domains.json', sorted(adult))
    trackers = json.loads(raw['trackers'])
    write('trackers.json', trackers)
    print(f'{len(rows)} eligible sites; {len(excluded)} excluded. Original ranks retained, no fabricated replacements.')
if __name__=='__main__': main()
