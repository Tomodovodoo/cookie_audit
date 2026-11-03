"""Prepare completed evidence for publication; archive superseded capture files locally."""
import json,shutil
from pathlib import Path
from audit import ROOT,save,sanitise_state
def main():
    archived=0;count=0
    for result_path in (ROOT/'docs/results').glob('*.json'):
        row=json.loads(result_path.read_text(encoding='utf-8'))
        folder=ROOT/'docs/evidence'/row['domain']
        if not folder.exists():continue
        keep=set()
        for p in folder.glob('*.json'):
            state=sanitise_state(json.loads(p.read_text(encoding='utf-8')))
            if state.get('captured_at','')<row['tested_at']:continue
            if state.get('blocked'):state.pop('screenshot',None)
            for frame in state.get('frames',[]):
                for control in frame.get('controls',[]):control['context']=control.get('context','')[:400]
            state['context_excerpt_limit']=400
            save(p,state);keep.add(p.name)
            if state.get('screenshot'):keep.add(state['screenshot'])
            count+=1
        for p in list(folder.iterdir()):
            if p.is_file() and p.name not in keep:
                target=ROOT/'private/superseded'/row['domain']/p.name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.move(str(p),str(target));archived+=1
    print(f'Compacted {count} captures; archived {archived} superseded files outside the public tree.')
if __name__=='__main__':main()
