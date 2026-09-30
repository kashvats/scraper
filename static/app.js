const $ = id => document.getElementById(id);
let active = null, pollTimer = null, resultOffset=0, appSettings={};
const terminal = s => !['queued','running'].includes(s);
function input(placeholder, value='') {const e=document.createElement('input');e.placeholder=placeholder;e.value=value;return e;}
function labeled(text, el) {const l=document.createElement('label');const s=document.createElement('span');s.textContent=text;l.append(s,el);return l;}
function addLevel(value='') {
 if($('levels').children.length>=5) return;
 const row=document.createElement('div');row.className='level';
 const title=document.createElement('span');title.className='level-lbl';title.textContent='Links';
 const el=input('e.g. .product-card a',value);el.required=true;
 const b=document.createElement('button');b.type='button';b.className='btn-icon';b.textContent='×';b.setAttribute('aria-label','Remove link level');b.onclick=()=>row.remove();row.append(title,el,b);$('levels').append(row);
}
function addField(name='',selector='',attribute='',multiple=false) {
 if($('fields').children.length>=30)return;
 const box=document.createElement('div');box.className='field';
 const top=document.createElement('div');top.className='field-top';
 const n=input('column_name',name),s=input('h1.title',selector),a=input('text',attribute);n.required=s.required=true;
 n.dataset.key='name';s.dataset.key='selector';a.dataset.key='attribute';
 const b=document.createElement('button');b.type='button';b.className='btn-icon';b.textContent='×';b.setAttribute('aria-label','Remove field');b.onclick=()=>box.remove();
 top.append(labeled('Column name',n),labeled('CSS selector',s),b);
 const bottom=document.createElement('div');bottom.className='field-bottom';
 const cb=document.createElement('input');cb.type='checkbox';cb.checked=multiple;cb.dataset.key='multiple';
 const label=labeled('All matches',cb);label.className='check';bottom.append(labeled('Attribute (optional)',a),label);box.append(top,bottom);$('fields').append(box);
}
$('add-level').onclick=()=>addLevel();$('add-field').onclick=()=>addField();
$('sample').onclick=()=>{
 $('url').value=appSettings.demo_url||'http://demo.harvest.test/catalog.html';$('levels').replaceChildren();$('fields').replaceChildren();$('next_selector').value='';$('row_selector').value='';$('wait_selector').value='';
 $('open-site').click();
};
function config() {
 const c={};for(const k of ['url','engine','next_selector','row_selector','wait_selector'])c[k]=$(k).value.trim();
 for(const k of ['max_pages','max_rows','delay_ms','settle_ms','timeout_ms'])c[k]=Number($(k).value);
 c.same_origin=$('same_origin').checked;c.link_levels=[...$('levels').querySelectorAll('input')].map(i=>i.value.trim());
 c.fields=[...$('fields').children].map(box=>Object.fromEntries([...box.querySelectorAll('input')].map(i=>[i.dataset.key,i.type==='checkbox'?i.checked:i.value.trim()])));return c;
}
async function api(path,opts={}) {
 const r=await fetch(path,{...opts});
 if(!r.ok){
  const d=await r.json().catch(()=>({detail:r.statusText}));
  const message=Array.isArray(d.detail)?d.detail.map(x=>`${x.loc?.slice(1).join('.')}: ${x.msg}`).join('; '):d.detail;
  throw Error(typeof message==='string'?message:'The request failed.');
 }
 return r.json();
}
$('config').onsubmit=async e=>{
 e.preventDefault();$('form-error').textContent='';if(!$('fields').children.length){$('form-error').textContent='Open the site and add at least one data column first.';return;}$('run').disabled=true;
 try {const r=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config())});active=r.id;resultOffset=0;clearTimeout(pollTimer);await poll();}
 catch(e){$('form-error').textContent=e.message;$('run').disabled=false;}
};
function cell(tag,text){const e=document.createElement(tag);e.textContent=text??'';e.title=text??'';return e;}
async function poll(){
 clearTimeout(pollTimer);if(!active)return;
 try{
 const job=await api('/api/jobs/'+active+'?offset='+resultOffset);
 const badge=$('status');badge.textContent=job.status.replaceAll('_',' ');
 badge.className='badge'+(job.status==='running'?' running':['failed','cancelled'].includes(job.status)?' failed':'');$('row-count').textContent=job.row_count;$('page-count').textContent=job.pages;$('error-count').textContent=job.errors.length;
 $('stop').disabled=terminal(job.status);$('resume').disabled=!['failed','cancelled'].includes(job.status);$('delete-job').disabled=!terminal(job.status);$('previous-results').disabled=resultOffset===0;$('next-results').disabled=resultOffset+200>=job.row_count;$('run').disabled=!terminal(job.status);$('csv').disabled=$('xlsx').disabled=!job.row_count;
 $('empty').hidden=!!job.row_count;$('table-wrap').hidden=!job.row_count;
 const headers=job.config.fields.map(f=>f.name).concat(['source_url','parent_url']);
 const tr=document.createElement('tr');headers.forEach(h=>tr.append(cell('th',h)));$('thead').replaceChildren(tr);
 $('tbody').replaceChildren(...job.rows.map(row=>{const tr=document.createElement('tr');headers.forEach(h=>tr.append(cell('td',row[h])));return tr;}));
 $('progress').textContent=terminal(job.status)?(job.status==='limited'?'Stopped at the configured page or row limit. ':'')+`Showing rows ${job.row_count?resultOffset+1:0}–${resultOffset+job.rows.length} of ${job.row_count}. Downloads include all rows.`:job.current_url||'Waiting for a browser…';
 $('errors').replaceChildren(...[...(job.failure?[{url:'Job',message:job.failure}]:[]),...job.errors].map(err=>{const p=document.createElement('p');p.textContent=err.url+' — '+err.message;return p;}));
 if(!terminal(job.status))pollTimer=setTimeout(poll,1200);else refreshHistory();
 }catch(e){$('form-error').textContent=e.message;$('run').disabled=false;}
}
$('stop').onclick=async()=>{try{await api('/api/jobs/'+active+'/cancel',{method:'POST'});$('progress').textContent='Stopping after the current browser operation…';}catch(e){$('form-error').textContent=e.message;}};
for(const fmt of ['csv','xlsx'])$(fmt).onclick=()=>{if(active)location.href='/api/jobs/'+active+'/export/'+fmt;};
async function refreshHistory(){try{const jobs=await api('/api/jobs');if(!jobs.length)return;$('history').replaceChildren(...jobs.map(j=>{const b=document.createElement('button');b.type='button';b.className='history-item';b.innerHTML=`<span>${new Date(j.created*1000).toLocaleString()}</span><span>${j.row_count} rows · ${j.status.replaceAll('_',' ')}</span>`;b.onclick=()=>{active=j.id;resultOffset=0;poll();};return b;}));}catch(e){$('history').textContent='Could not load job history.';}}


$('previous-results').onclick=()=>{resultOffset=Math.max(0,resultOffset-200);poll();};
$('next-results').onclick=()=>{resultOffset+=200;poll();};
$('resume').onclick=async()=>{try{await api('/api/jobs/'+active+'/resume',{method:'POST'});poll();}catch(e){$('form-error').textContent=e.message;}};
$('delete-job').onclick=async()=>{
 if(!active||!confirm('Delete this job and its collected results?'))return;
 try{await api('/api/jobs/'+active,{method:'DELETE'});active=null;clearTimeout(pollTimer);$('tbody').replaceChildren();$('table-wrap').hidden=true;$('empty').hidden=false;for(const id of ['csv','xlsx','resume','stop','delete-job'])$(id).disabled=true;for(const id of ['row-count','page-count','error-count'])$(id).textContent='0';$('errors').replaceChildren();$('status').textContent='Ready';$('progress').textContent='Job deleted.';refreshHistory();}catch(e){$('form-error').textContent=e.message;}
};
