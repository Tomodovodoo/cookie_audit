() => new Promise(resolve => {
  const out={providers:[]};
  const granted = obj => Object.keys(obj||{}).filter(k=>obj[k]===true);
  if(window.Cookiebot?.consent){
    const c=window.Cookiebot.consent;
    out.providers.push({provider:'Cookiebot',hasResponse:window.Cookiebot.hasResponse===true,optionalGranted:['preferences','statistics','marketing'].filter(k=>c[k]===true)});
  }
  if(typeof window.__tcfapi!=='function'){resolve(out);return;}
  let listenerId,finished=false;
  const finish=()=>{if(finished)return;finished=true;clearTimeout(timer);if(listenerId!==undefined){try{window.__tcfapi('removeEventListener',2,()=>{},listenerId);}catch{}}resolve(out);};
  const timer=setTimeout(finish,800);
  try{window.__tcfapi('addEventListener',2,(d,ok)=>{
    if(!ok||!d)return;
    if(finished){if(d.listenerId!==undefined){try{window.__tcfapi('removeEventListener',2,()=>{},d.listenerId);}catch{}}return;}
    listenerId=d.listenerId;
    if(d.cmpStatus!=='loaded'||!['tcloaded','useractioncomplete'].includes(d.eventStatus))return;
    out.providers.push({provider:'IAB TCF',gdprApplies:d.gdprApplies,eventStatus:d.eventStatus,cmpStatus:d.cmpStatus,purposesGranted:granted(d.purpose?.consents),specialFeaturesGranted:granted(d.specialFeatureOptins),vendorsConsented:granted(d.vendor?.consents).length,legitimateInterestPurposes:granted(d.purpose?.legitimateInterests)});
    finish();
  });}catch{finish();}
})
