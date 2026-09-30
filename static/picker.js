let pickerId=null, pickerBusy=false, picked=null, pickerRevision=0, listingUrl='';

function pickerStatus(message, error=false) {
  $('browser-message').textContent = message;
  $('browser-message').style.color = error ? 'var(--red)' : 'var(--text2)';
  const dot = $('browser-status-dot');
  if (dot) dot.style.background = error ? 'var(--red)' : 'var(--green)';
}

function setPickerBusy(value) {
  pickerBusy = value;
  $('visual-browser').classList.toggle('busy', value);
  $('open-site').disabled = value;
  const dot = $('browser-status-dot');
  if (dot && value) dot.style.background = 'var(--amber)';
}

async function pickerRequest(path, method='POST', body) {
  return api(path, {
    method,
    headers: {'Content-Type': 'application/json'},
    ...(body ? {body: JSON.stringify(body)} : {})
  });
}

function showShot(data) {
  pickerId = data.id;
  pickerRevision = data.revision || 0;
  $('browser-address').value = data.url;
  $('site-image').src = data.image;
  $('selection-box').hidden = true;
  if ($('browser-live-dot')) $('browser-live-dot').hidden = false;
  if ($('browser-active-badge')) $('browser-active-badge').hidden = false;
  if (data.selection) { picked = data.selection; showSelection(); }
  if (data.preview) {
    $('match-preview').textContent = `${data.preview.count} matching elements\n` + data.preview.values.join('\n\n');
  }
}

async function pickerAction(body) {
  if (pickerBusy || !pickerId) return null;
  setPickerBusy(true);
  pickerStatus('Updating site view…');
  try {
    const data = await pickerRequest('/api/picker/' + pickerId + '/action', 'POST', {...body, revision: pickerRevision});
    if (['navigate', 'back', 'click'].includes(body.kind)) {
      picked = null;
      $('selection-details').hidden = true;
      $('selection-empty').hidden = false;
    }
    showShot(data);
    pickerStatus('Click content to select it, or switch to Browse mode.');
    return data;
  } catch(e) {
    pickerStatus(e.message, true);
    return null;
  } finally {
    setPickerBusy(false);
  }
}

$('open-site').onclick = async () => {
  const url = $('url').value.trim();
  if (!url) { $('form-error').textContent = 'Enter a website URL first.'; return; }
  if (pickerBusy) return;
  listingUrl = url;
  if ($('nested-breadcrumb')) $('nested-breadcrumb').hidden = true;
  if (window.showView) window.showView('browser');
  else $('visual-browser').hidden = false;
  $('visual-browser').scrollIntoView({behavior: 'smooth', block: 'start'});
  setPickerBusy(true);
  pickerStatus('Opening website in browser…');
  try {
    if (pickerId) { try { await pickerRequest('/api/picker/' + pickerId, 'DELETE'); } catch{} }
    pickerId = null; picked = null;
    $('site-image').removeAttribute('src');
    $('selection-details').hidden = true;
    $('selection-empty').hidden = false;
    const data = await pickerRequest('/api/picker', 'POST', {url});
    showShot(data);
    pickerStatus('Click a value to map it to your column, or click a product link to follow nested pages.');
  } catch(e) {
    pickerStatus(e.message, true);
  } finally {
    setPickerBusy(false);
  }
};

$('close-browser').onclick = async () => {
  if (pickerBusy) return;
  if (pickerId) {
    try { await pickerRequest('/api/picker/' + pickerId, 'DELETE'); }
    catch(e) { pickerStatus(e.message, true); return; }
  }
  pickerId = null; picked = null;
  $('visual-browser').hidden = true;
  $('site-image').removeAttribute('src');
  if ($('browser-live-dot')) $('browser-live-dot').hidden = true;
  if ($('browser-active-badge')) $('browser-active-badge').hidden = true;
  if ($('nested-breadcrumb')) $('nested-breadcrumb').hidden = true;
  if (window.showView) window.showView('results');
};

$('site-image').onclick = async e => {
  const r = e.currentTarget.getBoundingClientRect();
  await pickerAction({
    kind: $('click-mode').value,
    x: (e.clientX - r.left) * 1000 / r.width,
    y: (e.clientY - r.top) * 650 / r.height
  });
};

// Mode switcher buttons
const btnModeSelect = $('btn-mode-select');
const btnModeClick = $('btn-mode-click');
function setClickMode(mode) {
  $('click-mode').value = mode;
  if (btnModeSelect) btnModeSelect.classList.toggle('active', mode === 'select');
  if (btnModeClick) btnModeClick.classList.toggle('active', mode === 'click');
  pickerStatus(mode === 'select' ? 'Click content to select data.' : 'Browse mode active. Click links or type text.');
}
if (btnModeSelect) btnModeSelect.onclick = () => setClickMode('select');
if (btnModeClick) btnModeClick.onclick = () => setClickMode('click');

$('scroll-up').onclick = () => pickerAction({kind: 'scroll', dy: -480});
$('scroll-down').onclick = () => pickerAction({kind: 'scroll', dy: 480});
$('browser-back').onclick = () => pickerAction({kind: 'back'});
$('browser-refresh').onclick = () => pickerAction({kind: 'refresh'});
$('browser-go').onclick = () => pickerAction({kind: 'navigate', url: $('browser-address').value});
$('browser-address').onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); $('browser-go').click(); } };
$('send-text').onclick = () => pickerAction({kind: 'type', text: $('browser-text').value});
$('send-enter').onclick = () => pickerAction({kind: 'press', key: 'Enter'});
$('pick-parent').onclick = () => picked && pickerAction({kind: 'parent', selector: picked.selector});

// Nested breadcrumb back button
if ($('btn-back-to-root')) {
  $('btn-back-to-root').onclick = async () => {
    if (listingUrl) {
      await pickerAction({kind: 'navigate', url: listingUrl});
      if ($('nested-breadcrumb')) $('nested-breadcrumb').hidden = true;
      pickerStatus('Returned to listing page.');
    }
  };
}

// Purpose pill buttons
function setPurpose(p) {
  $('selection-purpose').value = p;
  $('picked-scope').value = p === 'links' ? 'similar' : 'exact';
  ['field', 'links', 'next'].forEach(k => {
    const pill = $('pill-' + k);
    if (pill) pill.classList.toggle('active', k === p);
  });
  updateSelection();
}
if ($('pill-field')) $('pill-field').onclick = () => setPurpose('field');
if ($('pill-links')) $('pill-links').onclick = () => setPurpose('links');
if ($('pill-next')) $('pill-next').onclick = () => setPurpose('next');

function showSelection() {
  $('selection-empty').hidden = true;
  $('selection-details').hidden = false;
  $('picked-value').textContent = picked.text || picked.attributes.src || `<${picked.tag}>`;
  if ($('selected-tag-badge')) $('selected-tag-badge').textContent = `<${picked.tag}>`;
  $('picked-name').value = '';
  $('match-preview').textContent = '';

  // Auto-detect repeating card container if on list and row_selector is empty
  if (picked.card && !$('row_selector').value.trim() && !$('levels').children.length) {
    $('row_selector').value = picked.card.selector;
    pickerStatus(`Auto-detected card container: “${picked.card.selector}” (${picked.card.count} items). Each card will be a separate row!`);
  }

  // Configure link pills
  if ($('pill-links')) {
    $('pill-links').hidden = !picked.link;
  }

  const choices = [
    ['', 'Visible text'],
    ...Object.keys(picked.attributes).filter(k => !k.startsWith('on')).map(k => [k, k === 'src' ? 'Image URL (src)' : k === 'href' ? 'Link URL (href)' : `Attribute: ${k}`])
  ];
  $('picked-attribute').replaceChildren(...choices.map(([v, t]) => {
    const opt = document.createElement('option');
    opt.value = v; opt.textContent = t;
    return opt;
  }));
  if (picked.tag === 'img' && picked.attributes.src) $('picked-attribute').value = 'src';
  
  // Render child element chips if container has children
  const childWrap = $('child-elements-wrap');
  const childChips = $('child-chips');
  if (childWrap && childChips) {
    if (picked.children && picked.children.length > 0) {
      childWrap.hidden = false;
      childChips.replaceChildren(...picked.children.map(c => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'child-chip-btn';
        btn.textContent = `<${c.tag}> ${c.text || c.selector}`;
        btn.title = `Click to select <${c.tag}>`;
        btn.onclick = () => pickerAction({kind: 'select', selector: c.selector});
        return btn;
      }));
    } else {
      childWrap.hidden = true;
      childChips.replaceChildren();
    }
  }

  // Uncheck picked-all by default so multiple products aren't concatenated into one cell
  $('picked-all').checked = false;
  $('picked-scope').value = 'exact';
  setPurpose('field');

  const r = picked.rect, box = $('selection-box');
  box.hidden = false;
  Object.assign(box.style, {
    left: r.x / 10 + '%',
    top: r.y / 6.5 + '%',
    width: r.width / 10 + '%',
    height: r.height / 6.5 + '%'
  });
}

function updateSelection() {
  if (!picked) return;
  const purpose = $('selection-purpose').value;
  $('field-options').hidden = purpose !== 'field';
  if ($('nested-link-info')) $('nested-link-info').hidden = purpose !== 'links';
  
  ['field', 'links', 'next'].forEach(k => {
    const pill = $('pill-' + k);
    if (pill) pill.classList.toggle('active', k === purpose);
  });

  const selected = purpose === 'field' ? picked : picked.link;
  $('save-selection').textContent = purpose === 'field' ? 'Add column' : purpose === 'links' ? '🔗 Save link level & open detail page' : 'Save next-page link';
  $('save-selection').disabled = !selected;
  if (!selected) {
    $('picked-selector').value = '';
    $('match-preview').textContent = 'Select a link (or an element inside a link) for this action.';
    return;
  }
  $('picked-selector').value = $('picked-scope').value === 'similar' ? selected.similar_selector : selected.selector;
  $('match-preview').textContent = '';
  const attr = $('picked-attribute').value;
  $('picked-value').textContent = purpose !== 'field' ? selected.url : attr ? (picked.attributes[attr] || '') : picked.text;
}

$('selection-purpose').onchange = () => {
  $('picked-scope').value = $('selection-purpose').value === 'links' ? 'similar' : 'exact';
  updateSelection();
};
$('picked-scope').onchange = updateSelection;
$('picked-attribute').onchange = updateSelection;
$('preview-selection').onclick = () => pickerAction({
  kind: 'preview',
  selector: $('picked-selector').value,
  attribute: $('selection-purpose').value === 'field' ? $('picked-attribute').value : 'href'
});

$('save-selection').onclick = async () => {
  if (!picked || pickerBusy) return;
  const purpose = $('selection-purpose').value, selector = $('picked-selector').value.trim();
  if (!selector) { pickerStatus('Select content first.', true); return; }
  if (purpose === 'field') {
    const name = $('picked-name').value.trim();
    if (!name) { pickerStatus('Enter a column name for this value.', true); $('picked-name').focus(); return; }
    const names = [...$('fields').querySelectorAll('[data-key="name"]')].map(i => i.value.trim());
    if (names.includes(name) || ['source_url', 'parent_url'].includes(name)) { pickerStatus('Choose a unique column name.', true); return; }
    if (names.length >= 30) { pickerStatus('Maximum 30 columns.', true); return; }
    addField(name, selector, $('picked-attribute').value, $('picked-all').checked);
    pickerStatus(`Added column “${name}”. Select another value or run scraper below.`);
  } else if (purpose === 'next') {
    $('next_selector').value = selector;
    pickerStatus('Next-page link saved. Now select a product link or your content.');
  } else {
    if (!picked.link) return;
    if ($('levels').children.length >= 5) { pickerStatus('Maximum five link levels.', true); return; }
    if (!listingUrl) listingUrl = $('browser-address').value;
    const destUrl = picked.link.url;
    addLevel(selector);
    const result = await pickerAction({kind: 'navigate', url: destUrl});
    if (result) {
      if ($('nested-breadcrumb')) {
        $('nested-breadcrumb').hidden = false;
        $('crumb-level-badge').textContent = `Detail Page (Level ${$('levels').children.length})`;
      }
      setPurpose('field');
      picked = null;
      $('selection-details').hidden = true;
      $('selection-empty').hidden = false;
      pickerStatus('Now on Product Detail Page. Click any data here (Title, Price, Description, Specs) to add columns. They will be extracted for every product!');
    }
  }
};
