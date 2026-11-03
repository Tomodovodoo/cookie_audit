"""Conservative, inspectable observations. A pass is scoped to the measured visit."""
import re
from urllib.parse import urlsplit

ACCEPT = re.compile(r'^(alles |alle |alle cookies |all |cookies )?(accepteren|accepteer|accept|aanvaarden|akkoord|toestaan|agree|allow)( all| alles| alle cookies| cookies| and continue| en doorgaan)?$|^(ja,? ik (accepteer|ga akkoord)|accept all cookies|allow all cookies|alle cookies accepteren)$',re.I)
REJECT = re.compile(r'weigeren|weiger|reject|refuse|decline|deny|afwijzen|verwerpen|niet (accepteren|akkoord|toestaan)|zonder (te )?(accepteren|akkoord|toestemming)|alleen (strikt )?(noodzakelijk|essenti[eë]le|functionele|vereiste|standaard)|only (strictly )?(necessary|essential|required)|necessary (cookies )?only|do not (accept|consent)|geen toestemming|no,? thanks|nee,? (bedankt|liever niet)',re.I)
SETTINGS = re.compile(r'^(instellen|instellingen( beheren)?|voorkeuren|stel voorkeuren in|aanpassen|settings|preferences|manage cookies\+?|manage preferences|cookie[s -]*(instellingen|settings|preferences|voorkeuren)( bekijken)?|toestemmingsinstellingen|meer opties|meer informatie|zelf instellen)$',re.I)
SAVE = re.compile(r'^(opslaan|keuze opslaan|voorkeuren opslaan|selectie opslaan|save|save preferences|save settings|confirm choices|bevestigen|bevestig (mijn )?keuze)$',re.I)
MARKETING_COOKIE = re.compile(r'^(_fbp|_fbc|_gcl_au|_gcl_aw|IDE|_uetvid|_uetsid|cto_bundle|cto_bidid|anj|uuid2|_ttp|_scid|li_fat_id)$')
ANALYTICS_COOKIE = re.compile(r'^(_ga($|_)|_gid$|_gat|_pk_id|AMCV_|s_vi$|_clck$|_hjSessionUser_)')
BLOCK = re.compile(r'^(just a moment|access denied|attention required|403 forbidden|robot or human|security check)|IP address is blocked|temporarily blocked|verify you are human|checking your browser|unusual traffic|bevestig dat je (een mens|geen robot)|toegang geweigerd',re.I)

def result(status, reason): return {'status':status,'reason':reason}
def advertising_consent_remains(state):
    for receipt in state.get('consent_state',{}).get('providers',[]):
        if receipt.get('provider')=='Cookiebot' and receipt.get('hasResponse') and 'marketing' in receipt.get('optionalGranted',[]):return True
        if receipt.get('provider')=='IAB TCF' and receipt.get('gdprApplies') is True and receipt.get('eventStatus')=='useractioncomplete' and (set(receipt.get('purposesGranted',[]))&{'3','4'} or receipt.get('specialFeaturesGranted')):return True
    return False
def candidates(state, pattern):
    return [c for f in state.get('frames',[]) for c in f.get('controls',[]) if c.get('context') and not c.get('disabled') and pattern.search(c['text'])]
def rgb(text):
    parts=re.findall(r'[\d.]+',text or '')
    return [float(x) for x in parts[:3]] if len(parts)>=3 else [255,255,255]
def contrast(a,b):
    def lum(c):
        c=[v/255 for v in rgb(c)]; c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
        return sum(v*w for v,w in zip(c,[.2126,.7152,.0722]))
    x,y=sorted([lum(a),lum(b)]); return (y+.05)/(x+.05)
def ui_rules(state):
    a,r=candidates(state,ACCEPT),candidates(state,REJECT)
    unknown=result('unknown','No unambiguous accept/refuse pair found in a consent interface.')
    if not a:return unknown,unknown
    a=max(a,key=lambda c:c['inViewport'])
    if not r:
        if state.get('frame_errors'):return result('unknown','Refusal absence cannot be established while a frame is inaccessible.'),result('unknown','Incomplete frame inspection prevents a prominence verdict.')
        return result('fail','Accept is offered on the first layer; no direct refusal control was detected.'),result('fail','No refusal control detected alongside the first-layer accept control.')
    r=max(r,key=lambda c:c['inViewport'])
    ease=result('pass','Direct refusal control detected on the first layer; completion checked separately.')
    if a['inViewport'] and not r['inViewport']:return result('fail','Accept is visible; refusal requires scrolling.'),result('fail','Refusal is outside the initial viewport.')
    s,t=r['style'],a['style']
    plain = (s['background'] in ('transparent','rgba(0, 0, 0, 0)') and s['borderWidth']==0)
    accept_box = t['borderWidth']>0 or t['background'] not in ('transparent','rgba(0, 0, 0, 0)')
    text_sized = s['borderWidth']==0 and s['padding']=='0px' and r['box']['height']<a['box']['height']*.65
    if (plain and r['tag']=='A' or text_sized) and accept_box:return ease,result('fail','Refusal is styled as a small unboxed text link while acceptance is a full button.')
    if ('-' not in r['tag'] and contrast(s['color'],s['effectiveBackground'])<3) or s['fontSize']<t['fontSize']*.75:return ease,result('fail','Refusal has low text contrast or materially smaller text than acceptance.')
    if not a['inViewport'] or not r['inViewport']:return ease,result('unknown','The initial viewport does not contain both choices.')
    return ease,result('pass','Both choices are visible; no configured prominence disparity was found. Different colours alone are not a failure.')
def tracking(cookies, requests, tracker_map):
    evidence=[]; uncertain=[]
    for c in cookies:
        if MARKETING_COOKIE.search(c['name']) or (c['name']=='fr' and c['domain'].lstrip('.').endswith('facebook.com')): evidence.append({'kind':'marketing_cookie','name':c['name'],'domain':c['domain']})
        elif c['name'] in ('MUID','li_sugr','UserMatchHistory'):uncertain.append({'kind':'multipurpose_identifier','name':c['name'],'domain':c['domain']})
        elif ANALYTICS_COOKIE.search(c['name']): uncertain.append({'kind':'analytics_cookie','name':c['name'],'domain':c['domain']})
    for r in requests:
        host=urlsplit(r['url']).hostname or ''
        labels=[]
        for suffix in ['.'.join(host.split('.')[i:]) for i in range(len(host.split('.'))-1)]:
            labels.extend(tracker_map.get(suffix,[]))
        if labels and r.get('resource_type') not in ['stylesheet','font']:
            # Loading a library or contacting a blocklisted host alone is not proof of unlawful tracking.
            uncertain.append({'kind':'listed_endpoint','url':r['url'],'categories':sorted(set(labels))})
    if evidence:return result('fail','Known advertising identifier cookies were present without consent.'),evidence,uncertain
    if uncertain:return result('unknown','Analytics cookies or listed endpoints need purpose/consent-mode review.'),evidence,uncertain
    return result('pass','No configured tracking signals observed within this capture window; not a guarantee of absence.'),evidence,uncertain
