"""Resumable Chrome/CDP consent audit. Run `python audit.py --help`."""
import argparse, asyncio, hashlib, json, os, re, shutil, socket, subprocess, tempfile, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
from rules import ACCEPT, REJECT, SETTINGS, BLOCK, candidates, result, tracking, ui_rules

ROOT=Path(__file__).parent
INSPECT=(ROOT/'inspect.js').read_text(encoding='utf-8')
def now():return datetime.now(timezone.utc).isoformat()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)
def safe_url(url):
    u=urlsplit(url)
    return f'{u.scheme}://{u.netloc}{u.path}' if u.scheme in ('http','https') else u.scheme+':'
def tracker_map():
    out={}
    for category,companies in json.loads((ROOT/'data/trackers.json').read_text(encoding='utf-8'))['categories'].items():
        if category not in ('Advertising','Analytics','FingerprintingInvasive','FingerprintingGeneral','Social'):continue
        for company in companies:
            for urls in company.values():
                for domains in urls.values():
                    if isinstance(domains,list):
                        for domain in domains:
                            if isinstance(domain,str):out.setdefault(domain,[]).append(category)
    return out

async def inspect(page):
    frames=[]; errors=[]
    for frame in page.frames:
        try:
            data=await asyncio.wait_for(frame.evaluate(INSPECT),8)
            if frame != page.main_frame:
                element=await frame.frame_element()
                box=await element.bounding_box()
                viewport=page.viewport_size or {'width':1365,'height':900}
                for c in data['controls']:
                    b=c['box']
                    c['inViewport']=bool(c['inViewport'] and box and box['x']+b['x']>=0 and box['y']+b['y']>=0 and box['x']+b['x']+b['width']<=viewport['width'] and box['y']+b['y']+b['height']<=viewport['height'])
            for c in data['controls']:c['frame']=len(frames)
            data['frame_url']=safe_url(frame.url)
            frames.append(data)
        except Exception as e:errors.append(type(e).__name__)
    return {'frames':frames,'frame_errors':errors,'url':safe_url(page.url)}

async def snapshot(page,context,requests,folder,stage,mapping):
    state=await inspect(page)
    cookies=await context.cookies()
    # Never publish cookie values, storage values, request bodies, query strings, or auth headers.
    clean=[{k:c[k] for k in ('name','domain','path','expires','httpOnly','secure','sameSite') if k in c} for c in cookies]
    storage=[]
    for frame in page.frames:
        try:storage.append(await frame.evaluate('() => ({origin:location.origin, localKeys:Object.keys(localStorage),sessionKeys:Object.keys(sessionStorage)})'))
        except Exception:pass
    verdict,signals,uncertain=tracking(clean,requests,mapping)
    if state['frame_errors'] and verdict['status']=='pass':verdict=result('unknown','Some frames could not be inspected.')
    main=state['frames'][0] if state['frames'] else {}
    if not state['frames'] or BLOCK.search(main.get('title','')) or BLOCK.search(main.get('text','')[:1200]):
        verdict=result('unknown','A block or incomplete page cannot establish absence of tracking.')
    state.update({'captured_at':now(),'cookies':clean,'storage_keys':storage,'requests':list(requests),'tracking':verdict,'signals':signals,'uncertain_signals':uncertain})
    try:
        await page.screenshot(path=str(folder/(stage+'.jpg')),type='jpeg',quality=65,full_page=False,timeout=15000,animations='disabled')
        state['screenshot']=stage+'.jpg'
    except Exception as e:state['screenshot_error']=type(e).__name__
    save(folder/(stage+'.json'),state)
    return state

async def click(page,control):
    # Find by the instrumented node id in the matching frame, including open shadow roots.
    for frame in page.frames:
        loc=frame.locator('[data-cookie-audit="'+control['id']+'"]')
        try:
            if await loc.count() and re.sub(r'\s+',' ',(await loc.first.inner_text(timeout=1000)).strip())==control['text']:
                await loc.first.click(timeout=5000); return True
        except Exception:continue
    return False

async def navigate(page,url,wait):
    response=await page.goto(url,wait_until='domcontentloaded',timeout=35000)
    await asyncio.sleep(wait)
    return response.status if response else None

async def audit_site(browser,site,args,mapping,metadata):
    folder=ROOT/'docs/evidence'/site['domain']
    if folder.exists():
        archive=ROOT/'private/archive'/str(time.time_ns())/site['domain']
        archive.parent.mkdir(parents=True,exist_ok=True);folder.rename(archive)
    folder.mkdir(parents=True,exist_ok=True)
    row={**site,'tested_at':now(),'run':metadata,'checks':{},'steps':[],'evidence':f'evidence/{site["domain"]}/before.json'}
    contexts=[]
    try:
        context=await browser.new_context(locale='nl-NL',timezone_id='Europe/Amsterdam',viewport={'width':1365,'height':900},accept_downloads=False)
        contexts.append(context)
        # Filter adult redirects before they load. Never use the user's logged-in context.
        adult=set(json.loads((ROOT/'data/adult-domains.json').read_text(encoding='utf-8')))
        async def guard(route):
            host=urlsplit(route.request.url).hostname or ''
            if any('.'.join(host.split('.')[i:]) in adult for i in range(len(host.split('.')))): await route.abort()
            else:await route.continue_()
        await context.route('**/*',guard)
        page=await context.new_page(); requests=[]
        context.on('request',lambda req: requests.append({'url':safe_url(req.url),'resource_type':req.resource_type,'method':req.method,'at':now()}))
        page.on('dialog',lambda d: d.dismiss())
        status=await navigate(page,'https://'+site['domain'],args.wait)
        before=await snapshot(page,context,requests,folder,'before',mapping)
        main=before['frames'][0] if before['frames'] else {}
        blocked=status in (401,403,429,451,503) or BLOCK.search(main.get('title','')) or BLOCK.search(main.get('text','')[:1200])
        if blocked or (len(main.get('text',''))<80 and not candidates(before,ACCEPT)):
            # Block screens can expose an egress IP. Keep redacted JSON only.
            (folder/'before.png').unlink(missing_ok=True)
            (folder/'before.jpg').unlink(missing_ok=True)
            before.pop('screenshot',None)
            for frame in before['frames']:
                frame['text']=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','[IP redacted]',frame['text'])
            save(folder/'before.json',before)
            row['outcome']='blocked' if blocked else 'incomplete'
            row['checks']={k:result('unknown',f'Page could not be assessed reliably (HTTP {status}).') for k in ('reject','prominence','before','after','persists')}
            return row
        row['checks']['reject'],row['checks']['prominence']=ui_rules(before)
        row['checks']['before']=before['tracking'] if not before['frame_errors'] else result('unknown','One or more frames could not be inspected.')
        state=before; refusal_clicked=False; accept_seen=bool(candidates(before,ACCEPT))
        for step in range(4):
            reject=candidates(state,REJECT)
            settings=candidates(state,SETTINGS)
            # Prefer a global refusal over a per-purpose toggle in the settings layer.
            reject.sort(key=lambda c:(bool(re.search(r'alles|alle |all\b',c['text'],re.I)),c['inViewport']),reverse=True)
            chosen=next(iter(reject or (settings if step==0 and accept_seen else [])),None)
            if not chosen:break
            requests.clear()
            if not await click(page,chosen):break
            row['steps'].append({'action':'reject' if reject else 'settings','label':chosen['text']})
            await asyncio.sleep(args.wait)
            state=await snapshot(page,context,requests,folder,'reject-'+str(step+1),mapping)
            if reject:
                refusal_clicked=True
                # A surviving choice interface is not evidence of successful rejection.
                if not candidates(state,ACCEPT):break
        final_main=state['frames'][0] if state['frames'] else {}
        complete=refusal_clicked and not candidates(state,ACCEPT) and bool(state['frames']) and not BLOCK.search(final_main.get('text','')[:1200]) and not BLOCK.search(final_main.get('title',''))
        if complete:
            row['checks']['after']=state['tracking']
            if len(row['steps'])>1 and accept_seen:row['checks']['reject']=result('fail',f'Refusal required {len(row["steps"])} clicks; acceptance was offered directly.')
            elif row['checks']['reject']['status']=='pass':row['checks']['reject']=result('pass','Refusal completed with one click and the choice interface disappeared.')
            requests.clear()
            await navigate(page,page.url,args.wait)
            reloaded=await snapshot(page,context,requests,folder,'reload',mapping)
            rm=reloaded['frames'][0] if reloaded['frames'] else {}
            if not rm or BLOCK.search(rm.get('text','')[:1200]) or BLOCK.search(rm.get('title','')):row['checks']['persists']=result('unknown','Reload was blocked or incomplete.')
            elif candidates(reloaded,ACCEPT):row['checks']['persists']=result('fail','Consent interface reappeared after refusing and reloading.')
            else:row['checks']['persists']=result('pass','Refusal survived a reload of the resulting page.')
            if reloaded['tracking']['status']!='pass':row['checks']['after']=reloaded['tracking']
        else:
            if row['checks']['reject']['status']=='pass':row['checks']['reject']=result('unknown','A refusal control exists, but completion could not be verified.')
            row['checks']['after']=result('unknown','A completed refusal journey was not observed.')
            row['checks']['persists']=result('unknown','A completed refusal journey was not observed.')
        # Isolated acceptance control, never reuse the rejected context.
        if accept_seen and not args.skip_accept:
            accepted=await browser.new_context(locale='nl-NL',timezone_id='Europe/Amsterdam',viewport={'width':1365,'height':900},accept_downloads=False)
            contexts.append(accepted); await accepted.route('**/*',guard)
            ap=await accepted.new_page(); ar=[]
            accepted.on('request',lambda req:ar.append({'url':safe_url(req.url),'resource_type':req.resource_type,'method':req.method,'at':now()}))
            await navigate(ap,'https://'+site['domain'],args.wait)
            ast=await inspect(ap); opts=candidates(ast,ACCEPT)
            ar.clear()
            if opts and await click(ap,opts[0]):
                await asyncio.sleep(args.wait)
                ac=await snapshot(ap,accepted,ar,folder,'accept-control',mapping)
                row['accept_control']={'completed':not bool(candidates(ac,ACCEPT)),'tracking':ac['tracking']}
        row['outcome']='observed'
        row['http_status']=status
        row['title']=main.get('title')
        return row
    except Exception as e:
        row['outcome']='error'; row['error']=type(e).__name__+': '+str(e).splitlines()[0][:220]
        for k in ('reject','prominence','before','after','persists'):row['checks'].setdefault(k,result('unknown','Capture did not complete. '+row['error']))
        # Partial visits cannot earn tracking passes.
        for k in ('before','after','persists'):
            if row['checks'][k]['status']=='pass':row['checks'][k]=result('unknown','Capture ended early.')
        return row
    finally:
        for context in contexts:
            try:await context.close()
            except Exception:pass

async def main(args):
    sites=json.loads(args.sites.read_text(encoding='utf-8'))
    if any(not re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}',s['domain']) for s in sites):raise ValueError('Input contains an invalid domain.')
    if args.domains:sites=[s for s in sites if s['domain'] in args.domains.split(',')]
    if args.limit:sites=sites[:args.limit]
    if not args.force:sites=[s for s in sites if not (ROOT/'docs/results'/f'{s["domain"]}.json').exists()]
    if not sites:print('No untested sites. Use --force to repeat.');return
    metadata={'started_at':now(),'browser_mode':'headless' if args.headless else 'stock Chrome offscreen','locale':'nl-NL','timezone':'Europe/Amsterdam','viewport':'1365x900','wait_seconds':args.wait,'workers':args.workers,'egress_country':args.country,'accept_control_enabled':not args.skip_accept,'version':'0.1.1'}
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=args.chrome,headless=args.headless,ignore_default_args=['--enable-automation'],args=['--window-position=-32000,-32000','--disable-blink-features=AutomationControlled'])
        try:
            metadata['chrome_version']=browser.version
            mapping=tracker_map(); queue=asyncio.Queue()
            for s in sites:queue.put_nowait(s)
            done=0; start=time.monotonic()
            async def worker():
                nonlocal done
                while not queue.empty():
                    site=queue.get_nowait()
                    try:
                        row=await asyncio.wait_for(audit_site(browser,site,args,mapping,metadata),180)
                    except TimeoutError:
                        row={**site,'tested_at':now(),'run':metadata,'outcome':'timeout','checks':{k:result('unknown','Site exceeded the 180 second capture budget.') for k in ('reject','prominence','before','after','persists')}}
                    save(ROOT/'docs/results'/f'{site["domain"]}.json',row)
                    done+=1; elapsed=time.monotonic()-start
                    print(json.dumps({'completed':done,'total':len(sites),'domain':site['domain'],'outcome':row['outcome'],'checks':{k:v['status'] for k,v in row['checks'].items()},'elapsed_s':round(elapsed)}),flush=True)
                    queue.task_done()
            await asyncio.gather(*(worker() for _ in range(args.workers)))
        finally:
            await browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chrome',default=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--sites',type=Path,default=ROOT/'data/sites.json',help='Alternative site manifest; no 1,000-site size cap.')
    parser.add_argument('--wait',type=float,default=7)
    parser.add_argument('--limit',type=int)
    parser.add_argument('--domains')
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--skip-accept',action='store_true',help='Omit isolated acceptance control, recorded in results')
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--country',default='unverified',help='Measured egress country, not browser language')
    args=parser.parse_args()
    if args.workers<1 or args.workers>16 or args.wait<3:parser.error('Use 1-16 workers and at least 3 seconds per observation window.')
    asyncio.run(main(args))
