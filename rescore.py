"""Reapply current screening rules to captured evidence without revisiting websites."""
import json
from pathlib import Path
from audit import ROOT,save,tracker_map
from rules import result,tracking,ui_rules
def main():
    mapping=tracker_map();count=0
    for path in (ROOT/'docs/results').glob('*.json'):
        row=json.loads(path.read_text(encoding='utf-8'))
        if row['outcome']!='observed':continue
        folder=ROOT/'docs/evidence'/row['domain'];states={}
        for p in folder.glob('*.json'):
            state=json.loads(p.read_text(encoding='utf-8'))
            if 'cookies' not in state:continue
            state['tracking'],state['signals'],state['uncertain_signals']=tracking(state['cookies'],state['requests'],mapping)
            if state.get('frame_errors') and state['tracking']['status']=='pass':state['tracking']=result('unknown','Some frames could not be inspected.')
            states[p.stem]=state;save(p,state)
        if 'before' not in states:continue
        ease,prominence=ui_rules(states['before'])
        row['checks']['prominence']=prominence
        if ease['status']=='fail':row['checks']['reject']=ease
        elif ease['status']=='pass' and row['checks']['reject']['status']=='fail':
            if row.get('steps') and len(row['steps'])>1:pass
            else:row['checks']['reject']=result('unknown','Refusal control recognised by updated rules; journey needs a new capture.')
        row['checks']['before']=states['before']['tracking']
        refusal=states.get('reject-'+str(len(row.get('steps',[]))))
        if refusal and refusal.get('frame_errors'):
            if row['checks']['reject']['status']=='pass':row['checks']['reject']=result('unknown','Refusal interface could not be fully inspected.')
            row['checks']['after']=result('unknown','Refusal completion could not be verified across all frames.')
            row['checks']['persists']=result('unknown','Refusal completion could not be verified across all frames.')
        if row['checks']['persists']['status'] in ('pass','fail'):
            names=sorted(n for n in states if n.startswith('reject-') and int(n.split('-')[1])<=len(row.get('steps',[])))
            checks=[states[n]['tracking'] for n in ([names[-1]] if names else [])+(['reload'] if 'reload' in states else [])]
            if checks:row['checks']['after']=max(checks,key=lambda x:{'pass':0,'unknown':1,'fail':2}[x['status']])
        if states.get('reload',{}).get('frame_errors') and row['checks']['persists']['status']=='pass':row['checks']['persists']=result('unknown','Reload frames could not be fully inspected.')
        row['rules_version']='0.1.1';save(path,row);count+=1
    print(f'Rescored {count} observed results. Captures and timestamps retained.')
if __name__=='__main__':main()
