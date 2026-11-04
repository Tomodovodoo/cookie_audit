"""Reapply current screening rules to captured evidence without revisiting websites."""
import json
from pathlib import Path
from audit import ROOT,save,tracker_map,sanitise_state
from rules import result,tracking,ui_rules,advertising_consent_remains,unfinished_refusal
def main():
    mapping=tracker_map();count=0
    for path in (ROOT/'docs/results').glob('*.json'):
        row=json.loads(path.read_text(encoding='utf-8'))
        if row['outcome']!='observed':continue
        folder=ROOT/'docs/evidence'/row['domain'];states={}
        for p in folder.glob('*.json'):
            state=sanitise_state(json.loads(p.read_text(encoding='utf-8')))
            if 'cookies' not in state:continue
            state['tracking'],state['signals'],state['uncertain_signals']=tracking(state['cookies'],state['requests'],mapping)
            if state.get('limited_capture'):state['tracking']=result('unknown','Browser-agent UI observation has no complete network/HttpOnly-cookie capture.')
            if state.get('blocked'):state['tracking']=result('unknown','Block page, not a completed observation.')
            if state.get('frame_errors') and state['tracking']['status']=='pass':state['tracking']=result('unknown','Some frames could not be inspected.')
            states[p.stem]=state;save(p,state)
        if 'before' not in states:continue
        if states['before'].get('blocked'):
            row['outcome']='blocked';row['checks']={k:result('unknown','Page blocked browser verification; not an assessable visit.') for k in row['checks']}
            save(path,row);count+=1;continue
        ease,prominence=ui_rules(states['before'])
        row['checks']['prominence']=prominence
        if ease['status']=='fail':row['checks']['reject']=ease
        elif ease['status']=='unknown' and states['before'].get('frame_errors'):row['checks']['reject']=ease
        elif ease['status']=='pass' and row['checks']['reject']['status']=='fail':
            if row.get('steps') and len(row['steps'])>1:pass
            else:row['checks']['reject']=result('unknown','Refusal control recognised by updated rules; journey needs a new capture.')
        row['checks']['before']=states['before']['tracking']
        refusal=states.get('reject-'+str(len(row.get('steps',[]))))
        if refusal and (refusal.get('frame_errors') or refusal.get('blocked')):
            if row['checks']['reject']['status']=='pass':row['checks']['reject']=result('unknown','Refusal interface could not be fully inspected.')
            row['checks']['after']=result('unknown','Refusal completion could not be verified across all frames.')
            row['checks']['persists']=result('unknown','Refusal completion could not be verified across all frames.')
        if row['checks']['persists']['status'] in ('pass','fail'):
            names=sorted(n for n in states if n.startswith('reject-') and int(n.split('-')[1])<=len(row.get('steps',[])))
            checks=[states[n]['tracking'] for n in ([names[-1]] if names else [])+(['reload'] if 'reload' in states else [])]
            if checks:row['checks']['after']=max(checks,key=lambda x:{'pass':0,'unknown':1,'fail':2}[x['status']])
        if (states.get('reload',{}).get('frame_errors') or states.get('reload',{}).get('blocked')) and row['checks']['persists']['status'] in ('pass','fail'):row['checks']['persists']=result('unknown','Reload was blocked or could not be fully inspected.')
        if refusal and advertising_consent_remains(refusal):row['checks']['reject']=result('fail','After refusal, the consent manager still reported advertising or special-feature consent. See the captured consent_state receipt.')
        if refusal and unfinished_refusal(states['before'],refusal):
            if row['checks']['reject']['status']!='fail':row['checks']['reject']=result('unknown','Refusal led to an unfinished purchase/subscription flow, not verified refusal.')
            row['checks']['after']=result('unknown','No completed refusal on the audited website was observed.')
            row['checks']['persists']=result('unknown','Reload of a purchase/subscription flow does not establish refusal persistence.')
        row['rules_version']='0.2.0';save(path,row);count+=1
    print(f'Rescored {count} observed results. Captures and timestamps retained.')
if __name__=='__main__':main()
