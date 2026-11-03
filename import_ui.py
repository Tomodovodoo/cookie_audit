"""Import a recorded incognito browser-agent refusal journey as explicitly UI-only evidence."""
import argparse,json,shutil,time
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime
from audit import ROOT,save,sanitise_state
from rules import ACCEPT,REJECT,candidates,ui_rules,result

def main(domain,source,country):
    site=next(s for s in json.loads((ROOT/'data/sites.json').read_text(encoding='utf-8')) if s['domain']==domain)
    states={stage:sanitise_state(json.loads((source/(stage+'.json')).read_text(encoding='utf-8'))) for stage in ('before','reject-1','reload')}
    action=json.loads((source/'action.json').read_text(encoding='utf-8'))
    action.setdefault('captured_at',action['clicked_at'])
    before,refused,reloaded=(states[k] for k in ('before','reject-1','reload'))
    for state in states.values():
        host=urlsplit(state['url']).hostname or ''
        if not (host==domain or host.endswith('.'+domain)):raise ValueError('Capture belongs to another domain.')
        if state.get('frame_count')!=len(state['frames']) or state.get('frame_errors') or state.get('blocked'):raise ValueError('UI capture is incomplete or blocked.')
        if not state['frames'] or len(state['frames'][0].get('text',''))<80:raise ValueError('UI page content is incomplete.')
        state['limited_capture']=True
        state['tracking']=result('unknown','Browser-agent UI observation has no complete network/HttpOnly-cookie capture.')
        shot=state.get('screenshot')
        if not shot or Path(shot).name!=shot or not (source/shot).is_file():raise ValueError('Each stage needs its recorded screenshot.')
    if action['label'] not in [c['text'] for c in candidates(before,REJECT)]:raise ValueError('Recorded action is not a recognised initial refusal control.')
    if not (before['captured_at']<action['clicked_at']<refused['captured_at']<action['reload_started_at']<reloaded['captured_at']):raise ValueError('Capture/action timestamps are out of order.')
    elapsed=lambda a,b:(datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds()
    if min(elapsed(action['clicked_at'],refused['captured_at']),elapsed(action['reload_started_at'],reloaded['captured_at']))<7:raise ValueError('Observe at least seven seconds after each action.')
    ease,prominence=ui_rules(before)
    complete=not candidates(refused,ACCEPT)
    if ease['status']=='pass':ease=result('pass' if complete else 'unknown','Recorded one-click refusal completed.' if complete else 'Refusal completion could not be verified.')
    persistence=result('unknown','Refusal did not complete.') if not complete else result('fail','Choice interface returned after reload.') if candidates(reloaded,ACCEPT) else result('pass','Recorded refusal survived reload.')
    viewport=before['frames'][0]['viewport']
    row={**site,'tested_at':before['captured_at'],'outcome':'observed','evidence':f'evidence/{domain}/before.json','steps':[{'action':'reject','label':action['label']}],
         'run':{'browser_mode':'browser agent, incognito; UI-only','locale':before['frames'][0]['language'],'viewport':f'{viewport["width"]}x{viewport["height"]} initial DOM; stage viewports in captures','egress_country':country,'wait_seconds':7,'accept_control_enabled':False,'version':'ui-import-1'},
         'checks':{'reject':ease,'prominence':prominence,'before':before['tracking'],'after':refused['tracking'],'persists':persistence}}
    folder=ROOT/'docs/evidence'/domain;previous=ROOT/'docs/results'/(domain+'.json');archive=ROOT/'private/archive'/str(time.time_ns())/domain
    for path in (folder,previous,archive):path.resolve().relative_to(ROOT.resolve())
    archive.mkdir(parents=True)
    if previous.exists():previous.rename(archive/'result.json')
    if folder.exists():folder.rename(archive/'evidence')
    folder.mkdir(parents=True)
    for stage,state in states.items():save(folder/(stage+'.json'),state);shutil.copyfile(source/state['screenshot'],folder/state['screenshot'])
    save(folder/'action.json',action);save(previous,row)
    print('Imported UI-only journey:',domain,{k:v['status'] for k,v in row['checks'].items()})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--domain',required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--country',default='unverified')
    a=p.parse_args();main(a.domain,a.source,a.country)
