let savedTemplates=[];
async function enterWorkspace(){
 clearTimeout(pollTimer);active=null;resultOffset=0;pickerId=null;picked=null;$('config').reset();$('fields').replaceChildren();$('levels').replaceChildren();$('tbody').replaceChildren();$('thead').replaceChildren();$('errors').replaceChildren();$('visual-browser').hidden=true;$('site-image').removeAttribute('src');$('table-wrap').hidden=true;$('empty').hidden=false;for(const id of ['csv','xlsx','stop','resume','delete-job'])$(id).disabled=true;for(const id of ['row-count','page-count','error-count'])$(id).textContent='0';$('status').textContent='Ready';$('progress').textContent='';$('run').disabled=false;
 if (window.showView) window.showView('results');
 if ($('browser-live-dot')) $('browser-live-dot').hidden = true;
 if ($('browser-active-badge')) $('browser-active-badge').hidden = true;
 if ($('results-count-pill')) $('results-count-pill').textContent = '0';
 appSettings=await api('/api/settings');await Promise.all([refreshHistory(),loadTemplates()]);
 const health=await fetch('/health/ready');$('worker-warning').hidden=health.ok;
}
async function loadTemplates(){
 savedTemplates=await api('/api/templates');const options=[new Option('Choose a saved scraper',''),...savedTemplates.map(t=>new Option(t.name,t.id))];$('saved-scrapers').replaceChildren(...options);
}
function fillConfig(c){
 for(const k of ['url','engine','next_selector','row_selector','wait_selector','max_pages','max_rows','delay_ms','settle_ms','timeout_ms'])if(c[k]!==undefined)$(k).value=c[k];
 $('same_origin').checked=c.same_origin;$('levels').replaceChildren();c.link_levels.forEach(addLevel);$('fields').replaceChildren();c.fields.forEach(f=>addField(f.name,f.selector,f.attribute,f.multiple));
}
$('save-template').onclick=async()=>{
 const name=$('template-name').value.trim();if(!name){$('template-message').textContent='Enter a scraper name.';return;}
 if(savedTemplates.some(t=>t.name===name)&&!confirm('Replace the saved configuration "'+name+'"?'))return;
 try{await api('/api/templates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,config:config()})});await loadTemplates();$('template-message').textContent='Configuration saved.';}
 catch(e){$('template-message').textContent=e.message;}
};
$('load-template').onclick=async()=>{
 const t=savedTemplates.find(t=>t.id===$('saved-scrapers').value);if(!t)return;
 if($('fields').children.length&&!confirm('Replace the current form with this saved scraper?'))return;
 if(pickerId){await $('close-browser').onclick();if(pickerId)return;}
 fillConfig(t.config);$('template-name').value=t.name;$('template-message').textContent='Configuration loaded. Open the site to review or run it below.';
};
$('new-scraper').onclick=async()=>{
 if($('fields').children.length&&!confirm('Clear the current unsaved configuration?'))return;
 if(pickerId){await $('close-browser').onclick();if(pickerId)return;}
 $('url').value='';$('fields').replaceChildren();$('levels').replaceChildren();$('next_selector').value='';$('row_selector').value='';$('template-name').value='';$('template-message').textContent='';
};
enterWorkspace();
