const keys=['reject','prominence','before','after','persists'];
const glyph={pass:'✓',fail:'✕',unknown:'~'};
const $=id=>document.getElementById(id);
const buildVersion=new URL(document.currentScript.src).searchParams.get('v')||'manual';
const number=new Intl.NumberFormat('nl-NL');
const date=new Intl.DateTimeFormat('nl-NL',{dateStyle:'long',timeStyle:'short',timeZone:'Europe/Amsterdam'});
let data,nl,filtered=[],page=0;
const size=30;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function reasonText(reason){
 if(nl.reasons[reason])return nl.reasons[reason];
 let match=reason.match(/^Refusal required (\d+) clicks; acceptance was offered directly\.$/);
 if(match)return `Weigeren vergde ${match[1]} klikken. Accepteren kon direct.`;
 match=reason.match(/^Page could not be assessed reliably \(HTTP (\d+|None)\)\.$/);
 if(match)return `De pagina kon niet betrouwbaar worden beoordeeld.${match[1]==='None'?'':` HTTP status ${match[1]}.`}`;
 if(reason.startsWith('Capture did not complete.')){
  const code=reason.match(/net::(ERR_[A-Z_]+)/);
  return `De meting is niet voltooid.${code?` Browserfout: ${code[1]}.`:' Bekijk de foutgegevens in het meetbestand.'}`;
 }
 return 'Geen Nederlandse toelichting beschikbaar. Bekijk de meetgegevens.';
}

function rankText(r){
 return r.rank?'Nederlandse rang '+number.format(r.rank):r.global_rank?'Aanvulling · wereldrang '+number.format(r.global_rank):'Referentiewebsite';
}

function render(){
 if(!data||!nl)return;
 const query=$('search').value.toLocaleLowerCase('nl-NL'),filter=$('filter').value;
 filtered=data.rows.filter(r=>(r.domain+' '+r.name+' '+(r.company||'')).toLocaleLowerCase('nl-NL').includes(query)&&({all:true,fail:r.failures>0,tested:r.outcome!=='not_tested',unknown:r.outcome!=='not_tested'&&keys.some(k=>r.checks[k].status==='unknown'),pending:r.outcome==='not_tested'}[filter]));
 const groups={};
 for(const r of data.rows){const g=r.company||r.domain;groups[g]=(groups[g]||0)+r.failures;}
 const order=$('sort').value;
 filtered.sort((a,b)=>order==='rank'?(a.rank||999999)-(b.rank||999999):order==='name'?a.name.localeCompare(b.name,'nl'):order==='group'?(groups[b.company||b.domain]-groups[a.company||a.domain]||(a.company||a.domain).localeCompare(b.company||b.domain,'nl')||b.failures-a.failures):b.failures-a.failures||(a.rank||999999)-(b.rank||999999));
 page=Math.min(page,Math.max(0,Math.ceil(filtered.length/size)-1));
 $('count').textContent=`${number.format(filtered.length)} ${filtered.length===1?'website':'websites'}${order==='group'?' · Bedrijfsgroepen op totaal aantal rode kruisen':''}`;
 $('rows').innerHTML=filtered.slice(page*size,(page+1)*size).map(r=>`<tr><td class="site"><a href="https://${esc(r.domain)}" target="_blank" rel="noopener noreferrer">${esc(r.name)} ↗</a><small>${r.company?esc(r.company)+' · ':''}${esc(rankText(r))}</small><small>${esc(r.domain)} · ${esc(nl.outcomes[r.outcome]||'Onbekende bezoekstatus')}</small></td>${keys.map(k=>{
  const check=r.checks[k],reason=reasonText(check.reason);
  return `<td><span class="status ${check.status}" tabindex="0" title="${esc(reason)}" aria-label="${esc(nl.checks[k]+': '+nl.statuses[check.status]+'. '+reason)}">${glyph[check.status]}</span></td>`;
 }).join('')}<td><button class="evidence" data-domain="${esc(r.domain)}">${r.tested_at?'Bekijk bewijs':'Bekijk status'}</button></td></tr>`).join('')||'<tr><td colspan="7">Geen websites gevonden. Probeer een andere naam of filter.</td></tr>';
 $('page').textContent=`Pagina ${page+1} van ${Math.max(1,Math.ceil(filtered.length/size))}`;
 $('prev').disabled=page===0;
 $('next').disabled=(page+1)*size>=filtered.length;
}

function captureLabel(path){
 const name=path.split('/').pop(),step=name.match(/^reject-(\d+)\.json$/);
 return (nl.captures[name]||(step?'Na weigerstap '+step[1]:'Meetgegevens'))+' · JSON';
}

function runText(run){
 if(!run)return '';
 const viewport=run.viewport?.replace('initial DOM; stage viewports in captures','bij de eerste opname; schermformaten per stap in de meetgegevens');
 return [nl.browser_modes[run.browser_mode]||'Browsersessie',viewport?`Venster ${viewport}`:'',run.egress_country?`Internetlocatie ${run.egress_country}`:'',run.wait_seconds?`Minimaal ${run.wait_seconds} seconden per meetstap`:''].filter(Boolean).join(' · ');
}

function details(domain){
 const r=data.rows.find(r=>r.domain===domain);
 $('detail-body').innerHTML=`<h2 id="detail-title">${esc(r.name)}</h2><p>${esc(r.tested_at?'Gemeten op '+date.format(new Date(r.tested_at)):'Nog niet getest')}<br>${esc(runText(r.run))}</p>${keys.map(k=>`<div class="detail-check"><strong><span class="${r.checks[k].status}" role="img" aria-label="${esc(nl.statuses[r.checks[k].status])}">${glyph[r.checks[k].status]}</span> ${nl.checks[k]}</strong><p>${esc(reasonText(r.checks[k].reason))}</p></div>`).join('')}<p>Aangeklikte opties: ${esc(r.steps?.map(s=>s.label).join(' → ')||'Geen')}</p>${r.result_file?`<p><a href="${esc(r.result_file)}" target="_blank" rel="noopener">Meetresultaat en foutgegevens · JSON ↗</a></p>`:''}${r.company_source?`<p><a href="${esc(r.company_source)}" target="_blank" rel="noopener noreferrer">Bron voor de bedrijfsgroep ↗</a></p>`:''}${r.evidence?`<h3>Vastgelegde meetstappen</h3><p><a href="${esc(r.evidence)}" target="_blank" rel="noopener">Eerste opname · JSON ↗</a></p>${r.screenshot?`<img src="${esc(r.screenshot)}" alt="Eerste schermopname van ${esc(r.domain)}" loading="lazy">`:''}<ul>${r.capture_files?.filter(f=>f!==r.evidence).map(f=>`<li><a href="${esc(f)}" target="_blank" rel="noopener">${esc(captureLabel(f))}</a></li>`).join('')||''}</ul>`:''}`;
 $('details').showModal();
}

$('close').onclick=()=>$('details').close();
$('details').addEventListener('click',e=>{if(e.target===$('details'))$('details').close()});
$('rows').addEventListener('click',e=>{const b=e.target.closest('[data-domain]');if(b)details(b.dataset.domain)});
for(const id of ['search','filter','sort'])$(id).addEventListener(id==='search'?'input':'change',()=>{page=0;render()});
$('prev').onclick=()=>{page--;render()};
$('next').onclick=()=>{page++;render()};

Promise.all(['audit.json','nl.json'].map(file=>fetch(file+'?v='+encodeURIComponent(buildVersion),{cache:'no-store'}).then(r=>{
 if(!r.ok)throw Error('HTTP '+r.status);
 return r.json();
}))).then(([d,translations])=>{
 data=d;nl=translations;
 $('attempted').textContent=number.format(d.rows.filter(r=>r.outcome!=='not_tested').length);
 $('findings').textContent=number.format(d.rows.filter(r=>r.failures>0).length);
 $('observed').textContent=number.format(d.rows.filter(r=>r.outcome==='observed').length);
 const times=d.rows.map(r=>Date.parse(r.tested_at)).filter(Number.isFinite);
 $('updated').textContent=times.length?'Laatste meting: '+date.format(new Date(Math.max(...times)))+'.':'Nog geen metingen beschikbaar.';
 render();
}).catch(e=>{
 $('rows').innerHTML='<tr><td colspan="7">De resultaten konden niet worden geladen. Vernieuw de pagina of download het CSV bestand.</td></tr>';
 $('updated').textContent='Gegevens niet beschikbaar.'+(/^HTTP \d+$/.test(e.message)?' '+e.message:'');
});
