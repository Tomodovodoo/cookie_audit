() => {
  const all = [];
  const walk = root => { for (const e of root.querySelectorAll('*')) { all.push(e); if(e.shadowRoot) walk(e.shadowRoot); } };
  walk(document);
  const visible = e => {const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>2&&r.height>2&&s.visibility!=='hidden'&&s.display!=='none'&&+s.opacity>0.1;};
  const controls = [];
  for (const e of all) {
    if(!e.matches('button,a,input[type=button],input[type=submit],[role=button]') || !visible(e)) continue;
    const text=(e.innerText||e.getAttribute('aria-label')||e.value||'').trim().replace(/\s+/g,' ');
    if(!text || text.length>180) continue;
    let parent=e, context='';
    for(let i=0;i<7 && parent;i++,parent=parent.parentElement || parent.getRootNode().host){
      const t=(parent.innerText||'').trim();
      if(/cookie|tracking|privacy-instellingen|privacy settings|toestemming|consent/i.test(t) && t.length<18000){context=t.slice(0,6000);break;}
    }
    const s=getComputedStyle(e), r=e.getBoundingClientRect();
    let p=e, bg=s.backgroundColor;
    while((bg==='rgba(0, 0, 0, 0)'||bg==='transparent') && (p=p.parentElement)) bg=getComputedStyle(p).backgroundColor;
    const id='ca-'+controls.length; e.setAttribute('data-cookie-audit', id);
    controls.push({id,text,tag:e.tagName,context,box:{x:r.x,y:r.y,width:r.width,height:r.height},inViewport:r.top>=0&&r.left>=0&&r.bottom<=innerHeight&&r.right<=innerWidth,
      style:{color:s.color,background:s.backgroundColor,effectiveBackground:bg,fontSize:parseFloat(s.fontSize),fontWeight:s.fontWeight,borderWidth:parseFloat(s.borderWidth),borderColor:s.borderColor,padding:s.padding},disabled:!!e.disabled});
  }
  return {url:location.origin+location.pathname,title:document.title,text:(document.body?.innerText||'').slice(0,45000),controls,webdriver:navigator.webdriver,language:navigator.language,viewport:{width:innerWidth,height:innerHeight}};
}
