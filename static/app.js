const $ = id => document.getElementById(id);
let active = null, pollTimer = null;
const terminal = s => !['queued','running'].includes(s);
function input(placeholder, value='') {const e=document.createElement('input');e.placeholder=placeholder;e.value=value;return e;}
function labeled(text, el) {const l=document.createElement('label');l.append(text,el);return l;}
function addLevel(value='') {
 if($('levels').children.length>=5) return;
 const row=document.createElement('div');row.className='level';
 const title=document.createElement('span');title.textContent='Follow links';
 const el=input('e.g. .product-card a',value);el.required=true;
 const b=document.createElement('button');b.type='button';b.className='remove';b.textContent='×';b.setAttribute('aria-label','Remove link level');b.onclick=()=>row.remove();row.append(title,el,b);$('levels').append(row);
}
function addField(name='',selector='',attribute='',multiple=false) {
 if($('fields').children.length>=30)return;
 const box=document.createElement('div');box.className='field';
 const top=document.createElement('div');top.className='field-top';
 const n=input('product_name',name),s=input('h1',selector),a=input('Text by default',attribute);n.required=s.required=true;
 n.dataset.key='name';s.dataset.key='selector';a.dataset.key='attribute';
 const b=document.createElement('button');b.type='button';b.className='remove';b.textContent='×';b.setAttribute('aria-label','Remove field');b.onclick=()=>box.remove();
 top.append(labeled('Column name',n),labeled('CSS selector',s),b);
 const bottom=document.createElement('div');bottom.className='field-bottom';
 const cb=document.createElement('input');cb.type='checkbox';cb.checked=multiple;cb.dataset.key='multiple';
 const label=labeled('All matches',cb);label.className='check';bottom.append(labeled('Attribute (optional)',a),label);box.append(top,bottom);$('fields').append(box);
}
$('add-level').onclick=()=>addLevel();$('add-field').onclick=()=>addField();
$('sample').onclick=()=>{
 $('url').value=location.origin+'/demo/catalog';$('levels').replaceChildren();$('fields').replaceChildren();$('next_selector').value='';$('row_selector').value='';$('wait_selector').value='';
 $('open-site').click();
};
function config() {
 const c={};for(const k of ['url','engine','next_selector','row_selector','wait_selector'])c[k]=$(k).value.trim();
 for(const k of ['max_pages','max_rows','delay_ms','settle_ms','timeout_ms'])c[k]=Number($(k).value);
 c.same_origin=$('same_origin').checked;c.link_levels=[...$('levels').querySelectorAll('input')].map(i=>i.value.trim());
 c.fields=[...$('fields').children].map(box=>Object.fromEntries([...box.querySelectorAll('input')].map(i=>[i.dataset.key,i.type==='checkbox'?i.checked:i.value.trim()])));return c;
}
async function api(path,opts={}) {const r=await fetch(path,opts);if(!r.ok){const d=await r.json().catch(()=>({detail:r.statusText}));throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));}return r.json();}
$('config').onsubmit=async e=>{
 e.preventDefault();$('form-error').textContent='';if(!$('fields').children.length){$('form-error').textContent='Open the site and add at least one data column first.';return;}$('run').disabled=true;
 try {const r=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config())});active=r.id;clearTimeout(pollTimer);await poll();}
 catch(e){$('form-error').textContent=e.message;$('run').disabled=false;}
};
function cell(tag,text){const e=document.createElement(tag);e.textContent=text??'';e.title=text??'';return e;}
async function poll(){
 clearTimeout(pollTimer);if(!active)return;
 try{
 const job=await api('/api/jobs/'+active);
 $('status').textContent=job.status.replaceAll('_',' ');$('row-count').textContent=job.row_count;$('page-count').textContent=job.pages;$('error-count').textContent=job.errors.length;
 $('stop').disabled=terminal(job.status);$('run').disabled=!terminal(job.status);$('csv').disabled=$('xlsx').disabled=!job.row_count;
 $('empty').hidden=!!job.row_count;$('table-wrap').hidden=!job.row_count;
 const headers=job.config.fields.map(f=>f.name).concat(['source_url','parent_url']);
 const tr=document.createElement('tr');headers.forEach(h=>tr.append(cell('th',h)));$('thead').replaceChildren(tr);
 $('tbody').replaceChildren(...job.rows.map(row=>{const tr=document.createElement('tr');headers.forEach(h=>tr.append(cell('td',row[h])));return tr;}));
 $('progress').textContent=terminal(job.status)?(job.status==='limited'?'Stopped at the configured page or row limit. ':'')+`Preview shows ${job.rows.length} of ${job.row_count} rows. Downloads include all collected rows.`:job.current_url||'Waiting for a browser…';
 $('errors').replaceChildren(...job.errors.map(err=>{const p=document.createElement('p');p.textContent=err.url+' — '+err.message;return p;}));
 if(!terminal(job.status))pollTimer=setTimeout(poll,1200);else refreshHistory();
 }catch(e){$('form-error').textContent=e.message;$('run').disabled=false;}
}
$('stop').onclick=async()=>{try{await api('/api/jobs/'+active+'/cancel',{method:'POST'});$('progress').textContent='Stopping after the current browser operation…';}catch(e){$('form-error').textContent=e.message;}};
for(const fmt of ['csv','xlsx'])$(fmt).onclick=()=>{if(active)location.href='/api/jobs/'+active+'/export/'+fmt;};
async function refreshHistory(){try{const jobs=await api('/api/jobs');if(!jobs.length)return;$('history').replaceChildren(...jobs.map(j=>{const b=document.createElement('button');b.type='button';b.textContent=`${j.id.slice(0,8)} · ${j.row_count} rows · ${j.status.replaceAll('_',' ')}`;b.onclick=()=>{active=j.id;poll();};return b;}));}catch(e){$('history').textContent='Could not load job history.';}}
refreshHistory();
