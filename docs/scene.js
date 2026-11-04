/* Decorative signal paths join the original images at their rendered coordinates. */
(() => {
 const page=document.querySelector('.audit-page');
 const network=document.getElementById('signal-network');
 const sky=document.getElementById('satellite-art');
 const ground=document.getElementById('ground-art');
 if(!page||!network||!sky||!ground)return;
 const ns='http://www.w3.org/2000/svg';
 const routes=[
  [.07,-.12,.18,.04], [.19,.04,-.10,.14], [.30,.14,.03,.30],
  [-.08,.31,.13,-.07], [.44,-.06,.32,.45], [.62,.40,-.12,.23],
  [.98,1.12,.88,.97], [.86,.95,1.14,.82], [1.12,.75,.94,1.09],
  [.74,1.08,.70,.88], [.58,.82,1.05,.63], [.92,.55,.78,1.16]
 ];
 function element(tag,attrs){
  const node=document.createElementNS(ns,tag);
  for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);
  return node;
 }
 function draw(){
  const box=page.getBoundingClientRect(),a=sky.getBoundingClientRect(),b=ground.getBoundingClientRect();
  if(!box.width||!a.height||!b.height)return;
  const point=(rect,x,y)=>({x:rect.left-box.left+rect.width*x,y:rect.top-box.top+rect.height*y});
  const origins=[point(b,.657,.57),point(b,.686,.62)];
  const satellites=[point(a,.172,.677),point(a,.728,.263)];
  network.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);
  const layer=element('g',{fill:'none',stroke:'#24b8f3','stroke-linecap':'round'});
  routes.forEach((route,i)=>{
   const start=origins[i===4||i===9?1:0],end=satellites[i<6?0:1];
   const points=[start,...route.map((x,j)=>({x:x*box.width,y:start.y+(end.y-start.y)*[.16,.37,.60,.80][j]})),end];
   let d=`M ${start.x} ${start.y}`;
   for(let j=1;j<points.length;j++){
    const prev=points[j-1],next=points[j],dy=(next.y-prev.y)*.48;
    d+=` C ${prev.x} ${prev.y+dy} ${next.x} ${next.y-dy} ${next.x} ${next.y}`;
   }
   layer.append(element('path',{d,'stroke-width':i%3===0?1.8:1.1,opacity:i%3===0?.85:.48,'vector-effect':'non-scaling-stroke'}));
  });
  for(const p of satellites){
   layer.append(element('circle',{cx:p.x,cy:p.y,r:12,fill:'#24b8f3',stroke:'none',opacity:.14}));
   layer.append(element('circle',{cx:p.x,cy:p.y,r:4,fill:'#c5f5ff',stroke:'none'}));
  }
  // Small vector objects occupy the open margins, never the report surface.
  if(box.width>1000){
   const report=document.getElementById('results').getBoundingClientRect();
   const method=document.getElementById('methodology').getBoundingClientRect();
   const left=(report.left-box.left)/2,right=(report.right-box.left+box.width)/2;
   const objects=[
    {x:left,y:report.top-box.top+report.height*.28,rotate:-18,shape:'<path d="M 18 -22 A 27 27 0 1 0 27 6 Q 12 8 12 -5 Q -1 -4 2 -18 Z"/><circle cx="-10" cy="-8" r="3"/><circle cx="-6" cy="12" r="4"/><circle cx="12" cy="18" r="2"/><circle cx="22" cy="-17" r="2"/>'},
    {x:right,y:report.top-box.top+report.height*.62,rotate:12,shape:'<rect x="-24" y="-28" width="48" height="17" rx="3"/><rect x="-24" y="-5" width="48" height="17" rx="3"/><rect x="-24" y="18" width="48" height="17" rx="3"/><path d="M -14 -20 H 3 M -14 3 H 3 M -14 26 H 3"/><circle cx="15" cy="-20" r="2"/><circle cx="15" cy="3" r="2"/><circle cx="15" cy="26" r="2"/>'},
    {x:box.width*.80,y:method.top-box.top+method.height*.55,rotate:-12,shape:'<path d="M -24 -18 Q -24 25 22 25 Z M -2 11 L 16 -8 M 12 -11 L 20 -5 M -7 20 L -13 42 M 9 26 L 14 42 M -23 42 H 23"/><path d="M 24 -22 Q 37 -16 35 -3 M 29 -34 Q 53 -21 48 2" fill="none"/>'}
   ];
   for(const o of objects){
    const group=element('g',{class:'signal-object',transform:`translate(${o.x} ${o.y}) rotate(${o.rotate})`,fill:'#e7f1ec',stroke:'#27718e','stroke-width':1.5});
    group.innerHTML=o.shape;
    layer.append(group);
   }
  }
  network.replaceChildren(layer);
 }
 let queued=false;
 function schedule(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(()=>{queued=false;draw()});
 }
 const observer=new ResizeObserver(schedule);
 for(const node of [page,sky,ground])observer.observe(node);
 sky.addEventListener('load',schedule);
 ground.addEventListener('load',schedule);
 schedule();
})();
