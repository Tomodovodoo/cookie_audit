"""Extend the filtered country cohort with explicitly labelled globally ranked .nl sites."""
import csv,io,json,re
from datetime import datetime,timezone
from prepare import DATA,fetch,write
from exclusions import excluded
def main():
    sites=json.loads((DATA/'sites.json').read_text(encoding='utf-8'))
    sites=[s for s in sites if s['cohort']!='Supplemental .nl global ranking']
    seen={s['domain'] for s in sites};adult=set(json.loads((DATA/'adult-domains.json').read_text(encoding='utf-8')))
    url='https://netapi.com/netapi_top1mln.csv';raw=fetch(url);extra=[]
    for item in csv.reader(io.StringIO(raw.decode('utf-8-sig'))):
        if len(sites)+len(extra)>=1000:break
        if len(item)<2 or not item[0].isdigit():continue
        rank,domain=int(item[0]),item[1].strip().lower()
        if not domain.endswith('.nl') or domain in seen or excluded(domain,adult):continue
        extra.append({'rank':None,'global_rank':rank,'domain':domain,'name':domain,'company':None,'cohort':'Supplemental .nl global ranking'});seen.add(domain)
    write('sites.json',sites+extra)
    write('supplemental-sites.json',extra)
    sources=json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
    sources['supplemental_global_ranking']={'url':url,'retrieved':datetime.now(timezone.utc).isoformat(),'selected':len(extra),'method':'Highest globally ranked eligible .nl domains absent from the filtered country cohort; not assigned a Netherlands rank.'}
    write('sources.json',sources)
    print(f'{len(sites)} country-cohort sites + {len(extra)} labelled supplements = {len(sites)+len(extra)} targets.')
if __name__=='__main__':main()
