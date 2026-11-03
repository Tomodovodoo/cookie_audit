"""Build the public dataset from captures. Untested entries remain explicit."""
import argparse,csv, hashlib, json, shutil
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
KEYS=['reject','prominence','before','after','persists']
DPG='https://www.dpgmediagroup.com/en-NL/permission-brands'
MEDIAHUIS='https://www.mediahuis.com/nl/merken'
GROUPS={
    'DPG Media':('ad.nl nu.nl volkskrant.nl parool.nl trouw.nl bndestem.nl bd.nl gelderlander.nl destentor.nl ed.nl pzc.nl tubantia.nl autoweek.nl autotrack.nl indebuurt.nl intermediair.nl libelle.nl margriet.nl nationalevacaturebank.nl qmusic.nl sportnieuws.nl vtwonen.nl independer.nl',DPG),
    'Mediahuis':('nrc.nl telegraaf.nl limburger.nl noordhollandsdagblad.nl dvhn.nl lc.nl haarlemsdagblad.nl gooieneemlander.nl leidschdagblad.nl dumpert.nl metronieuws.nl culy.nl manners.nl',MEDIAHUIS),
}
NAMES={'ad.nl':'AD','nrc.nl':'NRC','bol.com':'bol','abnamro.nl':'ABN AMRO','rabobank.nl':'Rabobank','marktplaats.nl':'Marktplaats','nu.nl':'NU.nl'}
def main(domains=None):
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    sites=json.loads((ROOT/'data/sites.json').read_text(encoding='utf-8'));rows=[]
    for s in sites:
        path=docs/'results'/f'{s["domain"]}.json'
        row=json.loads(path.read_text(encoding='utf-8')) if path.exists() and (domains is None or s['domain'] in domains) else {**s,'outcome':'not_tested','checks':{k:{'status':'unknown','reason':'Not yet tested.'} for k in KEYS}}
        row['name']=NAMES.get(row['domain'],row['domain'])
        if row.get('tested_at'):
            initial=docs/'evidence'/row['domain']/'before.json'
            if initial.exists():
                shot=json.loads(initial.read_text(encoding='utf-8')).get('screenshot')
                if shot:row['screenshot']=f'evidence/{row["domain"]}/{shot}'
                row['capture_files']=[f'evidence/{row["domain"]}/{p.name}' for p in initial.parent.glob('*.json')]
        for company,(group_domains,source) in GROUPS.items():
            if row['domain'] in group_domains.split():row.update(company=company,company_source=source)
        row['failures']=sum(v['status']=='fail' for v in row['checks'].values())
        row['passes']=sum(v['status']=='pass' for v in row['checks'].values())
        rows.append(row)
    rows.sort(key=lambda r:(-r['failures'],r.get('rank') or 999999,r['domain']))
    output={'generated_at':datetime.now(timezone.utc).isoformat(),'sources':json.loads((ROOT/'data/sources.json').read_text(encoding='utf-8')),'excluded':len(json.loads((ROOT/'data/excluded.json').read_text(encoding='utf-8'))),'supplemental':sum(r['cohort']=='Supplemental .nl global ranking' for r in rows),'rows':rows}
    (docs/'audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    with (docs/'audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['Company / site','Group','Website','Cohort','NL source rank','Supplemental global rank','Outcome']+KEYS+['Tested UTC','Evidence'])
        for r in rows:writer.writerow([r['name'],r.get('company') or 'Unverified','https://'+r['domain'],r['cohort'],r.get('rank'),r.get('global_rank'),r['outcome']]+[r['checks'][k]['status'] for k in KEYS]+[r.get('tested_at',''),r.get('evidence','')])
    manifest={str(p.relative_to(docs)).replace('\\','/'):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n') if p.suffix=='.json' else p.read_bytes()).hexdigest() for p in (docs/'evidence').rglob('*') if p.is_file() and (domains is None or p.parent.name in domains)} if (docs/'evidence').exists() else {}
    (docs/'evidence-sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name in ['sources.json','excluded.json'] :shutil.copyfile(ROOT/'data'/name,docs/name)
    print(f'Built {len(rows)} rows, {sum(r["outcome"]!="not_tested" for r in rows)} attempted; {len(manifest)} evidence files.')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--domains',help='Publish only these captures; other ranked sites remain not tested.')
    args=parser.parse_args();main(set(args.domains.split(',')) if args.domains else None)
