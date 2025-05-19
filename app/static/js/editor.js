(function(){
  const mdArea = document.getElementById('editor-markdown');
  const preview = document.getElementById('editor-preview');
  const toolbar = document.getElementById('editor-toolbar');
  const saveBtn = document.getElementById('save-markdown');
  const STORAGE_KEY = `expo_editor_content_${window.USER_UUID}`;
  let isPreview = false;
  const toggleBtn = document.getElementById('toggle-preview-btn');
  const importInput = document.getElementById('import-input');
  const titleDisplay = document.getElementById('layout-name-display');
  const EDIT_LAYOUT = window.EDIT_LAYOUT || null;
  // If in preview-only mode, hide editing controls and show preview
  if (window.VIEW_MODE) {
    // Hide editor and toolbar
    mdArea.style.display = 'none';
    document.getElementById('editor-toolbar').style.display = 'none';
    document.getElementById('editor-sidebar').style.display = 'none';
    document.getElementById('save-markdown').style.display = 'none';
    document.getElementById('cancel-link').style.display = 'none';
    toggleBtn.style.display = 'none';
    // Hide title editing
    document.getElementById('layout-name-edit-btn').style.display = 'none';
    document.getElementById('layout-name-input').style.display = 'none';
    // Show preview panel
    preview.style.display = 'block';
    // Load content into preview
    if (EDIT_LAYOUT) {
      mdArea.value = EDIT_LAYOUT.content;
      titleDisplay.textContent = EDIT_LAYOUT.name;
    }
    updatePreview();
    // No further event bindings
    return;
  }

  // Load content: existing or draft
  if (EDIT_LAYOUT) {
    mdArea.value = EDIT_LAYOUT.content;
    titleDisplay.textContent = EDIT_LAYOUT.name;
  } else {
    mdArea.value = localStorage.getItem(STORAGE_KEY) || '';
  }

  // sanitize user input
  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function collapseImages() {
    const imgs = Array.from(preview.querySelectorAll('img'));
    imgs.forEach(img => {
      if (img.closest('.carousel')) return;
      const details = document.createElement('details');
      details.className = 'img-collapse';
      const summary = document.createElement('summary');
      summary.textContent = '[Image]';
      const imgClone = img.cloneNode(true);
      details.appendChild(summary);
      details.appendChild(imgClone);
      img.replaceWith(details);
    });
  }

  function updatePreview(){
    let md = escapeHtml(mdArea.value);
    let html = md
      .replace(/^(#{1,6})\s*(.+)$/gm, (m, hashes, title) => `<h${hashes.length}>${title}</h${hashes.length}>`)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1" style="max-width:100%;"/>')
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/\n/g, '<br/>');
    // Carousel shortcode with optional delay, max_width, max_height
    html = html.replace(/\[carousel(?:\s+delay="([\d.]+)")?(?:\s+max_width="([^"]+)")?(?:\s+max_height="([^"]+)")?\]([\s\S]*?)\[\/carousel\]/g,
      (m, delay, maxW, maxH, inner) => {
        const interval = parseFloat(delay) || 3;  // default 3s
        // generate slide wrappers with optional styles
        const slides = inner.trim().split(/<br\/?\>/)
          .filter(s => s.trim())
          .map(item => {
            let style = '';
            if (maxW) style += `max-width:${maxW};`;
            else style += `max-width:80%;`;
            if (maxH) style += `max-height:${maxH};`;
            else style += `max-height:400px;`;
            return `<div class=\"slide\" style=\"${style}\">${item}</div>`;
          }).join('');
        return `<div class=\"carousel\" data-delay=\"${interval}\"><div class=\"slides\">${slides}</div></div>`;
      });
    preview.innerHTML = html;
    collapseImages();
    preview.querySelectorAll('.carousel').forEach(initCarousel);
    addToggleURLs();
  }

  function addToggleURLs() {
    // for links
    preview.querySelectorAll('a').forEach(a => {
      if (a.nextSibling && a.nextSibling.classList && a.nextSibling.classList.contains('toggle-url')) return;
      const url = a.href;
      const info = document.createElement('div');
      info.className = 'toggle-url';
      info.textContent = url;
      info.style.display = 'none';
      info.style.fontSize = '0.8em';
      info.style.color = '#6b7280';
      info.style.marginTop = '4px';
      a.after(info);
      a.addEventListener('click', e => {
        e.preventDefault();
        info.style.display = info.style.display === 'none' ? 'block' : 'none';
      });
    });
    // for images
    preview.querySelectorAll('img').forEach(img => {
      if (img.nextSibling && img.nextSibling.classList && img.nextSibling.classList.contains('toggle-url')) return;
      const src = img.src;
      const info = document.createElement('div');
      info.className = 'toggle-url';
      info.textContent = src;
      info.style.display = 'none';
      info.style.fontSize = '0.8em';
      info.style.color = '#6b7280';
      info.style.marginTop = '4px';
      img.after(info);
      img.addEventListener('click', e => {
        info.style.display = info.style.display === 'none' ? 'block' : 'none';
      });
    });
  }

  function insertAround(before, after){
    const start = mdArea.selectionStart;
    const end = mdArea.selectionEnd;
    const text = mdArea.value;
    mdArea.value = text.slice(0, start) + before + text.slice(start, end) + after + text.slice(end);
    mdArea.focus();
    mdArea.setSelectionRange(start + before.length, end + before.length);
    updatePreview();
    localStorage.setItem(STORAGE_KEY, mdArea.value);
  }

  // carousel behavior
  function initCarousel(carousel) {
    if (carousel._initialized) return;
    const slides = carousel.querySelector('.slides');
    const total = slides.children.length;
    let idx = 0;
    function show(i) { slides.style.transform = `translateX(-${i*100}%)`; }
    show(idx);
    // Auto-play with delay
    const delay = parseFloat(carousel.dataset.delay) || 3;
    carousel._timer = setInterval(() => { idx = (idx + 1) % total; show(idx); }, delay * 1000);
    carousel._initialized = true;
  }

  // history for undo/redo
  const undoStack = [];
  const redoStack = [];
  function pushHistory() {
    undoStack.push(mdArea.value);
    if (undoStack.length > 50) undoStack.shift();
  }
  // override input to track history
  mdArea.addEventListener('input', () => {
    pushHistory();
    updatePreview();
    localStorage.setItem(STORAGE_KEY, mdArea.value);
  });

  // In the markdown textarea, handle paste of images
  mdArea.addEventListener('paste', async (e) => {
    if (e.clipboardData) {
      for (const item of e.clipboardData.items) {
        if (item.type.indexOf('image') !== -1) {
          e.preventDefault();
          const blob = item.getAsFile();
          const form = new FormData();
          form.append('file', blob, 'pasted_image.png');
          try {
            const res = await fetch('/editor/upload_image', { method: 'POST', body: form });
            const data = await res.json();
            const url = data.url;
            const pos = mdArea.selectionStart;
            const text = mdArea.value;
            const placeholder = `![Pasted Image](${url})`;
            mdArea.value = text.slice(0, pos) + placeholder + text.slice(pos);
            updatePreview();
            localStorage.setItem(STORAGE_KEY, mdArea.value);
          } catch (err) {
            console.error('Image paste upload failed', err);
          }
          break;
        }
      }
    }
  });

  // Handle dragover to style drop zone
  mdArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    mdArea.classList.add('dragover');
  });
  mdArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    mdArea.classList.remove('dragover');
  });
  // Handle drop of images
  mdArea.addEventListener('drop', async (e) => {
    e.preventDefault();
    mdArea.classList.remove('dragover');
    if (e.dataTransfer && e.dataTransfer.files.length) {
      for (const file of e.dataTransfer.files) {
        if (file.type.startsWith('image/')) {
          const form = new FormData();
          form.append('file', file);
          try {
            const res = await fetch('/editor/upload_image', { method: 'POST', body: form });
            const data = await res.json();
            if (data.success) {
              const url = data.url;
              const pos = mdArea.selectionStart;
              const text = mdArea.value;
              const placeholder = `![Dropped Image](${url})`;
              mdArea.value = text.slice(0, pos) + placeholder + text.slice(pos);
              updatePreview();
              localStorage.setItem(STORAGE_KEY, mdArea.value);
            }
          } catch (err) {
            console.error('Image drop upload failed', err);
          }
          break;
        }
      }
    }
  });

  toolbar.addEventListener('click', e => {
    if(e.target.dataset.action){
      const act = e.target.dataset.action;
      if(act==='undo') {
        if(undoStack.length){
          redoStack.push(mdArea.value);
          mdArea.value = undoStack.pop();
          updatePreview();
        }
        return;
      }
      if(act==='redo') {
        if(redoStack.length){
          undoStack.push(mdArea.value);
          mdArea.value = redoStack.pop();
          updatePreview();
        }
        return;
      }
      if(act==='align-left') { insertAround('<div style="text-align:left;">','</div>'); return; }
      if(act==='align-center') { insertAround('<div style="text-align:center;">','</div>'); return; }
      if(act==='align-right') { insertAround('<div style="text-align:right;">','</div>'); return; }
      if(act==='bold') insertAround('**','**');
      if(act==='italic') insertAround('*','*');
      if(act==='heading'){
        const pos = mdArea.selectionStart;
        const text = mdArea.value;
        mdArea.value = text.slice(0,pos)+'# '+text.slice(pos);
        updatePreview();
        localStorage.setItem(STORAGE_KEY, mdArea.value);
      }
      if(act==='link'){
        const url = prompt('Enter URL:'); if(!url) return;
        insertAround('[',`](${url})`);
      }
      if(act==='image'){
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = async () => {
          const file = input.files[0];
          const form = new FormData();
          form.append('file', file);
          try {
            const res = await fetch('/editor/upload_image', { method: 'POST', body: form });
            const data = await res.json();
            const url = data.url;
            insertAround(`![${file.name}](${url})`, '');
          } catch (err) {
            console.error('Image upload failed', err);
          }
        };
        input.click();
        return;
      }
      if(act==='carousel'){
        // Prompt user for slide delay in seconds
        let delay = prompt('Задержка между слайдами (в секундах):', '3');
        if (delay === null) return;
        delay = parseFloat(delay) || 3;
        const start = mdArea.selectionStart;
        const end = mdArea.selectionEnd;
        const sel = mdArea.value.slice(start, end) || '![alt](url)';
        const carouselBlock = `[carousel delay="${delay}"]\n${sel}\n[/carousel]\n`;
        mdArea.value = mdArea.value.slice(0, start) + carouselBlock + mdArea.value.slice(end);
        updatePreview();
        localStorage.setItem(STORAGE_KEY, mdArea.value);
        return;
      }
      if(act==='export'){
        const data = { content: mdArea.value };
        const blob = new Blob([JSON.stringify(data, null,2)], {type:'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'layout.json'; a.click();
        URL.revokeObjectURL(url);
      }
      if(act==='import'){
        importInput.click();
      }
      if(act==='preview-newtab'){
        const w = window.open();
        w.document.write(`<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Preview</title><link rel=\"stylesheet\" href=\"/static/css/editor.css\"></head><body>${preview.innerHTML}</body></html>`);
        w.document.close();
      }
    }
  });

  // sidebar controls
  const fontFamilyInput = document.getElementById('font-family');
  const fontSizeInput = document.getElementById('font-size');
  const lineHeightInput = document.getElementById('line-height');
  // Animation controls inputs
  const animTypeInput = document.getElementById('anim-type');
  const animTimingInput = document.getElementById('anim-timing');
  const animDurationInput = document.getElementById('anim-duration');
  [fontFamilyInput, fontSizeInput, lineHeightInput].forEach(el => {
    el.addEventListener('change', () => {
      const ff = fontFamilyInput.value;
      mdArea.style.fontFamily = ff;
      preview.style.fontFamily = ff;
      mdArea.style.fontSize = fontSizeInput.value + 'px';
      preview.style.fontSize = fontSizeInput.value + 'px';
      mdArea.style.lineHeight = lineHeightInput.value;
      preview.style.lineHeight = lineHeightInput.value;
      localStorage.setItem(STORAGE_KEY, mdArea.value);
      updatePreview();
    });
  });

  function applyAnimation(){
    const type = animTypeInput.value;
    preview.classList.remove('fade-in','slide-in');
    if(type){
      preview.classList.add(type);
      preview.style.setProperty('--anim-duration', animDurationInput.value+'s');
      preview.style.animationTimingFunction = animTimingInput.value;
    } else {
      preview.style.removeProperty('--anim-duration');
      preview.style.removeProperty('animation-timing-function');
    }
  }
  [animTypeInput, animTimingInput, animDurationInput].forEach(el=>el.addEventListener('change', applyAnimation));
  applyAnimation();

  importInput.addEventListener('change', e => {
    const file = e.target.files[0]; if(!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const obj = JSON.parse(reader.result);
        mdArea.value = obj.content || '';
        updatePreview();
        localStorage.setItem(STORAGE_KEY, mdArea.value);
        showToast('Импорт выполнен', 'success');
      } catch {
        showToast('Ошибка импорта', '');
      }
    };
    reader.readAsText(file);
  });

  // drag & drop image into editor
  mdArea.addEventListener('dragover', e => { e.preventDefault(); });
  mdArea.addEventListener('drop', e => {
    e.preventDefault();
    Array.from(e.dataTransfer.files).forEach(file => {
      if(!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = ()=>{
        const data = reader.result;
        const before = `![${file.name}](${data})`;
        const pos = mdArea.selectionStart;
        mdArea.value = mdArea.value.slice(0,pos)+before+mdArea.value.slice(pos);
        updatePreview();
        localStorage.setItem(STORAGE_KEY, mdArea.value);
      };
      reader.readAsDataURL(file);
    });
  });

  // bind image click expand
  document.addEventListener('click', e => {
    if(e.target.tagName==='IMG' && preview.contains(e.target)){
      e.target.classList.toggle('expanded');
    }
  });

  // toggle preview panel
  toggleBtn.addEventListener('click', () => {
    isPreview = !isPreview;
    if(isPreview){
      preview.style.display = 'block';
      mdArea.style.display = 'none';
      toggleBtn.textContent = 'Редактор';
    } else {
      preview.style.display = 'none';
      mdArea.style.display = 'block';
      toggleBtn.textContent = 'Превью';
    }
    updatePreview();
  });

  // Inline title editing
  const editBtn = document.getElementById('layout-name-edit-btn');
  const titleInput = document.getElementById('layout-name-input');

  function enterTitleEdit() {
    titleInput.value = titleDisplay.textContent;
    titleDisplay.style.display = 'none';
    editBtn.style.display = 'none';
    titleInput.style.display = 'inline-block';
    titleInput.focus();
  }
  titleDisplay.addEventListener('click', enterTitleEdit);
  editBtn.addEventListener('click', enterTitleEdit);
  titleInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') titleInput.blur();
  });
  titleInput.addEventListener('blur', () => {
    const newName = titleInput.value.trim() || 'Без названия';
    titleDisplay.textContent = newName;
    titleInput.style.display = 'none';
    titleDisplay.style.display = 'inline';
    editBtn.style.display = 'inline';
  });

  saveBtn.addEventListener('click', ()=>{
    const content = mdArea.value;
    const mode = 'md';
    const payload = {
      id: EDIT_LAYOUT ? EDIT_LAYOUT.id : undefined,
      content,
      mode,
      name: titleDisplay.textContent,
      animType: animTypeInput.value,
      animTiming: animTimingInput.value,
      animDuration: animDurationInput.value,
      settings: {
        fontFamily: fontFamilyInput.value,
        fontSize: fontSizeInput.value,
        lineHeight: lineHeightInput.value
      }
    };
    fetch('/editor/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showToast('Сохранено макет: ' + data.name, 'success');
        localStorage.removeItem(STORAGE_KEY);
        // Redirect to dashboard to view saved layouts
        window.location.href = '/dashboard';
      } else {
        const err = data.error === 'Duplicate name' ? 'Макет с таким именем уже существует' : 'Ошибка сохранения';
        showToast(err, '');
      }
    })
    .catch(err => {
      console.error(err);
      showToast('Ошибка сохранения', '');
    });
  });

  // confirm cancel
  const cancelLink = document.getElementById('cancel-link');
  cancelLink.addEventListener('click', e => {
    if(mdArea.value.trim()){
      if(!confirm('У вас есть несохранённые изменения. Выйти без сохранения?')) e.preventDefault();
    }
  });

  window.addEventListener('beforeunload', e => {
    if(mdArea.value !== localStorage.getItem(STORAGE_KEY)){
      e.preventDefault();
      e.returnValue = '';
    }
  });
})();