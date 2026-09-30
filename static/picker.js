let pickerId=null, pickerBusy=false, picked=null, pickerRevision=0;
function pickerStatus(message,error=false){$('browser-message').textContent=message;$('browser-message').style.color=error?'var(--red)':'var(--green)';}
function setPickerBusy(value){pickerBusy=value;$('visual-browser').classList.toggle('busy',value);$('open-site').disabled=value;}
async function pickerRequest(path,method='POST',body){return api(path,{method,headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});}
function showShot(data){
 pickerId=data.id;pickerRevision=data.revision||0;$('browser-address').value=data.url;$('site-image').src=data.image;
 $('selection-box').hidden=true;
 if(data.selection){picked=data.selection;showSelection();}
 if(data.preview){$('match-preview').textContent=`${data.preview.count} matching elements\n`+data.preview.values.join('\n\n');}
}
async function pickerAction(body){
 if(pickerBusy||!pickerId)return null;
 setPickerBusy(true);pickerStatus('Updating site view…');
 try{const data=await pickerRequest('/api/picker/'+pickerId+'/action','POST',{...body,revision:pickerRevision});if(['navigate','back','click'].includes(body.kind)){picked=null;$('selection-details').hidden=true;$('selection-empty').hidden=false;}showShot(data);pickerStatus('Click content to select it, or switch to Browse mode.');return data;}
 catch(e){pickerStatus(e.message,true);return null;}
 finally{setPickerBusy(false);}
}
$('open-site').onclick=async()=>{
 const url=$('url').value.trim();if(!url){$('form-error').textContent='Enter a website URL first.';return;}
 if(pickerBusy)return;
 $('visual-browser').hidden=false;$('visual-browser').scrollIntoView({behavior:'smooth',block:'start'});
 setPickerBusy(true);pickerStatus('Opening the website in a browser…');
 try{
  if(pickerId){try{await pickerRequest('/api/picker/'+pickerId,'DELETE');}catch{}}
  pickerId=null;picked=null;$('site-image').removeAttribute('src');$('selection-details').hidden=true;$('selection-empty').hidden=false;
  const data=await pickerRequest('/api/picker','POST',{url});showShot(data);pickerStatus('Click a value to map it to your column.');
 }catch(e){pickerStatus(e.message,true);}
 finally{setPickerBusy(false);}
};
$('close-browser').onclick=async()=>{
 if(pickerBusy)return;
 if(pickerId){try{await pickerRequest('/api/picker/'+pickerId,'DELETE');}catch(e){pickerStatus(e.message,true);return;}}
 pickerId=null;picked=null;$('visual-browser').hidden=true;$('site-image').removeAttribute('src');
};
$('site-image').onclick=async e=>{
 const r=e.currentTarget.getBoundingClientRect();
 await pickerAction({kind:$('click-mode').value,x:(e.clientX-r.left)*1000/r.width,y:(e.clientY-r.top)*650/r.height});
};
$('scroll-up').onclick=()=>pickerAction({kind:'scroll',dy:-480});
$('scroll-down').onclick=()=>pickerAction({kind:'scroll',dy:480});
$('browser-back').onclick=()=>pickerAction({kind:'back'});
$('browser-refresh').onclick=()=>pickerAction({kind:'refresh'});
$('browser-go').onclick=()=>pickerAction({kind:'navigate',url:$('browser-address').value});
$('browser-address').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();$('browser-go').click();}};
$('send-text').onclick=()=>pickerAction({kind:'type',text:$('browser-text').value});
$('send-enter').onclick=()=>pickerAction({kind:'press',key:'Enter'});
$('pick-parent').onclick=()=>picked&&pickerAction({kind:'parent',selector:picked.selector});
function showSelection(){
 $('selection-empty').hidden=true;$('selection-details').hidden=false;
 $('picked-value').textContent=picked.text || picked.attributes.src || `<${picked.tag}>`;
 $('picked-name').value='';$('match-preview').textContent='';
 const choices=[['','Visible text'],...Object.keys(picked.attributes).filter(k=>!k.startsWith('on')).map(k=>[k,k==='src'?'Image URL (src)':k==='href'?'Link URL (href)':`Attribute: ${k}`])];
 $('picked-attribute').replaceChildren(...choices.map(([v,t])=>{const opt=document.createElement('option');opt.value=v;opt.textContent=t;return opt;}));
 if(picked.tag==='img' && picked.attributes.src)$('picked-attribute').value='src';
 $('picked-scope').value='exact';updateSelection();
 const r=picked.rect,box=$('selection-box');box.hidden=false;
 Object.assign(box.style,{left:r.x/10+'%',top:r.y/6.5+'%',width:r.width/10+'%',height:r.height/6.5+'%'});
}
function updateSelection(){
 if(!picked)return;
 const purpose=$('selection-purpose').value;
 $('field-options').hidden=purpose!=='field';
 const selected=purpose==='field'?picked:picked.link;
 $('save-selection').textContent=purpose==='field'?'Add column':purpose==='links'?'Save links & open one':'Save next-page link';
 $('save-selection').disabled=!selected;
 if(!selected){$('picked-selector').value='';$('match-preview').textContent='Select a link (or an element inside a link) for this action.';return;}
 $('picked-selector').value=$('picked-scope').value==='similar'?selected.similar_selector:selected.selector;
 $('match-preview').textContent='';
 const attr=$('picked-attribute').value;
 $('picked-value').textContent=purpose!=='field'?selected.url:attr?(picked.attributes[attr]||''):picked.text;
}
$('selection-purpose').onchange=()=>{
 $('picked-scope').value=$('selection-purpose').value==='links'?'similar':'exact';updateSelection();
};
$('picked-scope').onchange=updateSelection;
$('picked-attribute').onchange=updateSelection;
$('preview-selection').onclick=()=>pickerAction({kind:'preview',selector:$('picked-selector').value,attribute:$('selection-purpose').value==='field'?$('picked-attribute').value:'href'});
$('save-selection').onclick=async()=>{
 if(!picked||pickerBusy)return;
 const purpose=$('selection-purpose').value,selector=$('picked-selector').value.trim();
 if(!selector){pickerStatus('Select content first.',true);return;}
 if(purpose==='field'){
  const name=$('picked-name').value.trim();
  if(!name){pickerStatus('Enter a column name for this value.',true);$('picked-name').focus();return;}
  const names=[...$('fields').querySelectorAll('[data-key="name"]')].map(i=>i.value.trim());
  if(names.includes(name)||['source_url','parent_url'].includes(name)){pickerStatus('Choose a unique column name.',true);return;}
  if(names.length>=30){pickerStatus('Maximum 30 columns.',true);return;}
  addField(name,selector,$('picked-attribute').value,$('picked-all').checked);
  pickerStatus(`Added column “${name}”. Select another value or run the scraper below.`);
 }else if(purpose==='next'){
  $('next_selector').value=selector;pickerStatus('Next-page link saved. Now select a product link or your content.');
 }else{
  if(!picked.link)return;
  if($('levels').children.length>=5){pickerStatus('Maximum five link levels.',true);return;}
  const result=await pickerAction({kind:'navigate',url:picked.link.url});
  if(result){addLevel(selector);$('selection-purpose').value='field';picked=null;$('selection-details').hidden=true;$('selection-empty').hidden=false;pickerStatus('Link level saved. Select fields here, or select another link to go deeper.');}
 }
};
