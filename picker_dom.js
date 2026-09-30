(args) => {
  const clean = s => s.replace(/\s+/g, ' ').trim();
  const esc = s => CSS.escape(s);
  const count = s => {try{return document.querySelectorAll(s).length;}catch{return 0;}};
  const classes = el => Array.from(el.classList).filter(c => !/^(active|selected|hover|focus|open)$/.test(c)).slice(0,3);
  function token(el) {
    const cls=classes(el);
    return el.localName + cls.map(c=>'.'+esc(c)).join('');
  }
  function exact(el) {
    if(el.id && count('#'+esc(el.id))===1) return '#'+esc(el.id);
    for(const attr of ['data-testid','itemprop','name']) {
      const v=el.getAttribute(attr);
      if(v){const s=el.localName+'['+attr+'='+JSON.stringify(v)+']';if(count(s)===1)return s;}
    }
    let path=token(el),cur=el;
    while(count(path)!==1 && cur.parentElement) {
      const parent=cur.parentElement;
      const siblings=Array.from(parent.children).filter(e=>e.localName===cur.localName);
      if(siblings.length>1) path=token(cur)+':nth-of-type('+(siblings.indexOf(cur)+1)+')'+(path.startsWith(token(cur))?path.slice(token(cur).length):'');
      cur=parent;path=token(cur)+' > '+path;
    }
    return path;
  }
  function similar(el) {
    if(classes(el).length) return token(el);
    let path=el.localName,parent=el.parentElement;
    for(let n=0;parent && n<4;n++,parent=parent.parentElement){
      path=token(parent)+' > '+path;
      if(classes(parent).length)return path;
      if(parent.localName==='body')break;
    }
    return el.localName;
  }
  let el;
  if(args.selector) el=document.querySelector(args.selector);
  else el=document.elementFromPoint(args.x,args.y);
  if(!el)throw Error('No element found. Refresh the view and try again.');
  if(args.parent)el=el.parentElement || el;
  if(el.localName==='iframe')throw Error('Content inside embedded frames is not supported in this picker. Open the frame URL directly.');
  const rect=el.getBoundingClientRect();
  const attrs=Object.fromEntries(Array.from(el.attributes).filter(a=>!['style','class','id'].includes(a.name)).map(a=>[a.name,a.value.slice(0,2000)]));
  for(const key of ['href','src'])if(el.getAttribute(key))attrs[key]=new URL(el.getAttribute(key),document.baseURI).href;
  const link=el.closest('a[href]');
  const selector=exact(el),group=similar(el);
  return {selector,similar_selector:group,match_count:count(group),tag:el.localName,text:clean(el.innerText || el.textContent || '').slice(0,2000),attributes:attrs,
    link:link?{url:link.href,selector:exact(link),similar_selector:similar(link),match_count:count(similar(link))}:null,
    rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height}};
}
