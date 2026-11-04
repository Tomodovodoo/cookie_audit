"""Build the public dataset from captures. Untested entries remain explicit."""
import argparse,csv, hashlib, json, shutil,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
KEYS=['reject','prominence','before','after','persists']
DPG='https://www.dpgmediagroup.com/en-NL/permission-brands'
MEDIAHUIS='https://www.mediahuis.com/nl/merken'
GROUPS={
    'DPG Media':('ad.nl nu.nl volkskrant.nl parool.nl trouw.nl bndestem.nl bd.nl gelderlander.nl destentor.nl ed.nl pzc.nl tubantia.nl autoweek.nl indebuurt.nl intermediair.nl libelle.nl margriet.nl nationalevacaturebank.nl qmusic.nl sportnieuws.nl vtwonen.nl independer.nl deondernemer.nl flair.nl kekmama.nl oudersvannu.nl story.nl totaaltv.nl veronicasuperguide.nl viva.nl',DPG),
    'Mediahuis':('nrc.nl telegraaf.nl limburger.nl noordhollandsdagblad.nl dvhn.nl lc.nl haarlemsdagblad.nl gooieneemlander.nl leidschdagblad.nl dumpert.nl metronieuws.nl culy.nl manners.nl',MEDIAHUIS),
    'FD Mediagroep':('fd.nl bnr.nl','https://fdmg.nl/over-ons/'),
    'AutoScout24':('autoscout24.nl autotrack.nl gaspedaal.nl','https://www.mediahuis.com/en/news/autotrack-and-gaspedaal.nl-become-part-of-autoscout24'),
}
EXTRA_GROUPS={
    'rtl.nl':('DPG Media','https://www.dpgmediagroup.com/en-NL/about-dpg-media/organisation/history-dpg-media'),
    'rtlnieuws.nl':('DPG Media','https://jaarverslag.dpgmediagroup.com/2025-nl/de_overname_van_rtl'),
    'tweakers.net':('DPG Media','https://www.dpgmediagroup.com/en-NL/about-dpg-media/organisation/history-dpg-media'),
    'linda.nl':('DPG Media','https://www.dpgmediagroup.com/nl-BE/over-dpg-media/nieuws/overname-rtl-nederland-en-digitale-groei-stuwen-de-resultaten-van-dpg-mediaedia'),
}
NAMES={'ad.nl':'AD','nrc.nl':'NRC','bol.com':'bol','abnamro.nl':'ABN AMRO','rabobank.nl':'Rabobank','marktplaats.nl':'Marktplaats','nu.nl':'NU.nl'}
def main(domains=None,sites_path=ROOT/'data/sites.json'):
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    sites=json.loads(sites_path.read_text(encoding='utf-8'));rows=[]
    custom=sites_path.resolve()!=(ROOT/'data/sites.json').resolve()
    for s in sites:
        path=docs/'results'/f'{s["domain"]}.json'
        row=json.loads(path.read_text(encoding='utf-8')) if path.exists() and (domains is None or s['domain'] in domains) else {**s,'outcome':'not_tested','checks':{k:{'status':'unknown','reason':'Not yet tested.'} for k in KEYS}}
        row.update(s)
        row['name']=NAMES.get(row['domain'],s.get('name',row['domain']))
        if row.get('tested_at'):
            row['result_file']=f'results/{row["domain"]}.json'
            initial=docs/'evidence'/row['domain']/'before.json'
            if initial.exists():
                shot=json.loads(initial.read_text(encoding='utf-8')).get('screenshot')
                if shot:row['screenshot']=f'evidence/{row["domain"]}/{shot}'
                row['capture_files']=[f'evidence/{row["domain"]}/{p.name}' for p in initial.parent.glob('*.json')]
            else:row.pop('evidence',None)
        for company,(group_domains,source) in GROUPS.items():
            if row['domain'] in group_domains.split():row.update(company=company,company_source=source)
        if row['domain'] in EXTRA_GROUPS:
            company,source=EXTRA_GROUPS[row['domain']];row.update(company=company,company_source=source)
        row['failures']=sum(v['status']=='fail' for v in row['checks'].values())
        row['passes']=sum(v['status']=='pass' for v in row['checks'].values())
        rows.append(row)
    rows.sort(key=lambda r:(-r['failures'],r.get('rank') or 999999,r['domain']))
    output={'generated_at':datetime.now(timezone.utc).isoformat(),'custom_cohort':custom,'input_manifest':sites_path.name,'sources':json.loads((ROOT/'data/sources.json').read_text(encoding='utf-8')),'excluded':0 if custom else len(json.loads((ROOT/'data/excluded.json').read_text(encoding='utf-8'))),'supplemental':sum(r['cohort']=='Supplemental .nl global ranking' for r in rows),'rows':rows}
    (docs/'audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    nl=json.loads((docs/'nl.json').read_text(encoding='utf-8'))
    index=docs/'index.html'
    if index.exists():
        version=hashlib.sha256(b''.join((docs/name).read_bytes() for name in ('app.js','nl.json','style.css','audit.json'))).hexdigest()[:16]
        index.write_text(re.sub(r'src="app\.js(?:\?v=[0-9a-f]+)?"',f'src="app.js?v={version}"',index.read_text(encoding='utf-8')),encoding='utf-8')
        for html in docs.glob('*.html'):
            html.write_text(re.sub(r'href="((?:/cookie_audit/)?style\.css)(?:\?v=[0-9a-f]+)?"',lambda m:f'href="{m[1]}?v={version}"',html.read_text(encoding='utf-8')),encoding='utf-8')
    with (docs/'audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['Naam','Bedrijfsgroep','Website','Selectie','Nederlandse bronrang','Wereldrang aanvulling','Bezoekstatus']+[nl['checks'][k] for k in KEYS]+['Gemeten op UTC','Bewijs'])
        for r in rows:writer.writerow([r['name'],r.get('company') or '', 'https://'+r['domain'],nl['cohorts'].get(r['cohort'],'Eigen selectie'),r.get('rank'),r.get('global_rank'),nl['outcomes'][r['outcome']]]+[nl['statuses'][r['checks'][k]['status']] for k in KEYS]+[r.get('tested_at',''),r.get('evidence') or r.get('result_file','')])
    included={r['domain'] for r in rows if r['outcome']!='not_tested'}
    manifest={str(p.relative_to(docs)).replace('\\','/'):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n') if p.suffix=='.json' else p.read_bytes()).hexdigest() for p in (docs/'evidence').rglob('*') if p.is_file() and p.parent.name in included} if (docs/'evidence').exists() else {}
    (docs/'evidence-sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name in ['sources.json','excluded.json'] :shutil.copyfile(ROOT/'data'/name,docs/name)
    print(f'Built {len(rows)} rows, {sum(r["outcome"]!="not_tested" for r in rows)} attempted; {len(manifest)} evidence files.')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--domains',help='Publish only these captures; other ranked sites remain not tested.')
    parser.add_argument('--sites',type=Path,default=ROOT/'data/sites.json',help='Same manifest supplied to audit.py.')
    args=parser.parse_args();main(set(args.domains.split(',')) if args.domains else None,args.sites)
