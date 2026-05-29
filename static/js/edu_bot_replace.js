document.addEventListener('DOMContentLoaded', () => {
    try {
        if (window.__eduBotInitialized) { console.log('EduBot: already initialized'); return; }

        // Ensure root exists; if not, create a container to attach bot UI
        let root = document.getElementById('edu-bot-root');
        if (!root) {
            root = document.createElement('div');
            root.id = 'edu-bot-root';
            document.body.appendChild(root);
        }

        // Build clean FAB and panel markup to avoid previous listeners/overlays
        root.innerHTML = `
          <button id="edu-bot-fab" class="edu-bot-fab" aria-label="EduBot'u aç">
            <span class="fab-icon"><i class="fa-solid fa-robot"></i></span>
            <span class="online-dot" aria-hidden="true"></span>
          </button>
          <div id="edu-bot-panel" class="edu-bot-panel" aria-hidden="true" role="dialog" aria-label="EduBot chat window">
            <div class="edu-header">
              <div style="display:flex;align-items:center;gap:12px;">
                <div class="edu-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="edu-meta">
                  <div class="edu-title">EduBot AI <span class="edu-online">ÇEVRİMİÇİ</span></div>
                  <div class="edu-sub">Kitaplar, veri seti veya sınavlarla ilgili sorular sorabilirsiniz</div>
                </div>
              </div>
              <div class="edu-header-actions">
                <button id="edu-return" class="edu-return btn btn-sm" aria-label="Kitabı iade et" title="Kitabı iade et"><i class="fa-solid fa-rotate-left"></i></button>
                <button id="edu-delete" class="edu-delete btn btn-sm" aria-label="Konuşmayı sil"><i class="fa-solid fa-trash-can"></i></button>
                <button id="edu-bot-close" class="edu-close btn btn-sm" aria-label="Kapat"><i class="fa-solid fa-xmark"></i></button>
              </div>
            </div>
            <div id="edu-bot-body" class="edu-body">
              <div id="edu-messages" class="edu-messages" role="log" aria-live="polite"></div>
              <div class="edu-quick-actions">
                <button class="edu-quick btn" data-q="Materyal Yardımı">Materyal Yardımı</button>
                <button class="edu-quick btn" data-q="Veri Seti Yardımı">Veri Seti Yardımı</button>
                <button class="edu-quick btn" data-q="Sınav Yardımı">Sınav Yardımı</button>
              </div>
              <div class="edu-input-row">
                <textarea id="edu-input" class="edu-input" rows="1" placeholder="Mesaj yazın... (Enter ile gönder)"></textarea>
                <button id="edu-send" class="edu-send btn" aria-label="Send"><i class="fa-solid fa-paper-plane"></i></button>
              </div>
            </div>
          </div>
        `;

        // grab fresh elements
        const fab = document.getElementById('edu-bot-fab');
        const panel = document.getElementById('edu-bot-panel');
        const messagesEl = document.getElementById('edu-messages');
        const inputEl = document.getElementById('edu-input');
        const sendBtn = document.getElementById('edu-send');
        const returnBtn = document.getElementById('edu-return');
        const deleteBtn = document.getElementById('edu-delete');
        const closeBtn = document.getElementById('edu-bot-close');

        // apply translations to newly created elements (if i18n loaded)
        if (window.__i18n && typeof window.__i18n.apply === 'function') window.__i18n.apply();

    function ts(){ const d=new Date(); return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}); }
    function escapeHtml(s){ if(!s && s!=='') return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
    function getScope(){ return (document.body.dataset.userRole||'Student').toLowerCase()==='admin' ? 'admin' : 'student'; }
    const STORAGE_KEY = () => `edu_messages_${getScope()}_v1`;

    function render(obj){ if(!messagesEl) return; const el=document.createElement('div'); el.className='msg '+(obj.who==='user'?'user':'bot'); const content = obj.html ? obj.html : `<div class="content">${escapeHtml(obj.text)}</div>`; el.innerHTML = content + `<span class="ts">${obj.ts||ts()}</span>`; messagesEl.appendChild(el); messagesEl.scrollTop = messagesEl.scrollHeight; }

    function saveLocal(obj){ try{ const arr=JSON.parse(localStorage.getItem(STORAGE_KEY())||'[]'); arr.push(obj); localStorage.setItem(STORAGE_KEY(),JSON.stringify(arr)); }catch(e){} }
    async function saveServer(obj){ try{ await fetch('/api/chat/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scope:getScope(),sender: obj.who==='user'?'user':'bot',message: obj.text})}); }catch(e){} }
    function addMessage(text, who='bot'){ const obj={who,text,ts:ts(),html:null}; saveLocal(obj); saveServer(obj); render(obj); }

    function loadLocal(){ try{ const arr=JSON.parse(localStorage.getItem(STORAGE_KEY())||'[]'); arr.forEach(render); messagesEl.scrollTop = messagesEl.scrollHeight; }catch(e){} }

    async function loadServerThenLocal(){ try{ const res=await fetch('/api/chat/history?scope='+getScope()); if(res.ok){ const data = await res.json(); messagesEl.innerHTML=''; if(data.rows && data.rows.length){ data.rows.forEach(r=>{ render({ who: r.sender==='bot'?'bot':'user', text: r.message, ts: r.created_at }); }); } loadLocal(); } else { loadLocal(); } }catch(e){ loadLocal(); } }

    function clearAll(){ try{ localStorage.removeItem(STORAGE_KEY()); }catch(e){} messagesEl.innerHTML=''; }

    async function deleteConversation(){ if(!confirm('Bu konuşmayı silmek istiyor musunuz?')) return; try{ await fetch('/api/chat/delete',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'scope='+encodeURIComponent(getScope())}); clearAll(); deleteBtn.classList.add('btn-danger'); setTimeout(()=>deleteBtn.classList.remove('btn-danger'),700); }catch(e){} }

    async function doReturnBook(){
      // use modal for input (Turkish)
      const title = 'Kitap iadesi';
      const placeholder = 'Seri no, başlık veya öğrenci kimliği girin';
      const resModal = await window.showGlobalModal({ title, body: '', placeholder, showInput:true, confirmText: 'Onayla', cancelText: 'İptal' });
      if (!resModal || !resModal.confirmed) return;
      const ident = resModal.value;
      if (!ident) return;
      render({ who:'user', text: ident, ts:ts() });
      addMessage('İade işleniyor...', 'bot');
      try{
        const res = await fetch('/api/return-book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({identifier: ident})});
        const data = await res.json();
          if (res.ok && data.ok){ addMessage(data.message || 'Kitap başarıyla iade edildi.', 'bot'); }
        else if (data && data.error){ addMessage(data.message || ('Hata: ' + data.error), 'bot'); }
        else { addMessage('Sunucudan beklenmeyen yanıt alındı.', 'bot'); }
      }catch(e){ addMessage((window.__i18n && window.__i18n.t)? window.__i18n.t('network_error') : 'Network error while returning book.', 'bot'); }
    }

    async function doSearch(q){ if(!q) return; render({ who:'user', text:q, ts:ts() }); try{ const scope=getScope(); const endpoint = scope==='admin'?'/api/chatbook-admin':'/api/chatbook'; const res = await fetch(endpoint + '?q=' + encodeURIComponent(q)); if(!res.ok){ addMessage('Network error. Try again.','bot'); return; } const data = await res.json(); if(data && data.results && data.results.length){ for(const r of data.results){ const html = `
            <div style="display:flex;gap:10px;align-items:flex-start">
              ${r.image_url?`<img class=\"book-cover\" src=\"${escapeHtml(r.image_url)}\" onerror=\"this.style.display=\\'none\\'\">`:''}
              <div>
                <strong>${escapeHtml(r.title||'')}</strong>
                ${r.serial_number?`<div class=\"small text-muted\">Serial: <strong>#${escapeHtml(String(r.serial_number))}</strong></div>`:''}
                ${r.category?`<div class=\"text-muted small\">Category: ${escapeHtml(r.category)}</div>`:''}
                ${(r.shelf_location||r.order_position)?`<div class=\"text-muted small\">${r.shelf_location? 'Shelf: '+escapeHtml(r.shelf_location):''}${r.shelf_location && r.order_position? ' • ' : ''}${r.order_position? 'Order: '+escapeHtml(String(r.order_position)):''}</div>`:''}
                ${r.available_copies!==undefined?`<div class=\"text-muted small\">Available Copies: ${escapeHtml(String(r.available_copies))}</div>`:''}
                ${r.description?`<p class="mb-0 mt-1 small text-muted">${escapeHtml(r.description)}</p>`:''}
                ${r.borrow_id?`<div style="margin-top:8px;"><button class="edu-return-result btn btn-sm btn-success" data-borrow-id="${escapeHtml(String(r.borrow_id))}">Return</button></div>`:''}
              </div>
            </div>`;
                    addMessage('', 'bot'); // placeholder
                    const last = messagesEl.lastElementChild; if(last){ last.innerHTML = html + `<span class="ts">${ts()}</span>`; saveLocal({who:'bot',text:r.description||r.title||'',ts:ts(),html:html}); saveServer({who:'bot',text:r.description||r.title||'',ts:ts(),html:html}); }
                }
                return;
            }
            addMessage('Üzgünüm, eşleşen kitap bulunamadı.','bot');
        }catch(e){ addMessage('Network error. Please try again.','bot'); }
    }

    // toggle helpers: ensure single listener and proper styles
    function openPanel(){
      try{
        panel.classList.add('open');
        panel.style.visibility = 'visible'; panel.style.opacity = '1'; panel.style.transform = 'translateY(0)'; panel.style.pointerEvents = 'auto';
        panel.setAttribute('aria-hidden','false');
        console.log('Chat opened');
        loadServerThenLocal();
      }catch(e){ console.error('openPanel error', e); }
    }
    function closePanel(){
      try{
        panel.classList.remove('open');
        panel.style.opacity = '0'; panel.style.transform = 'translateY(12px)'; panel.style.pointerEvents = 'none';
        panel.setAttribute('aria-hidden','true');
        // hide after transition
        setTimeout(()=>{ if (!panel.classList.contains('open')) panel.style.visibility = 'hidden'; }, 260);
        console.log('Chat closed');
      }catch(e){ console.error('closePanel error', e); }
    }

    // make sure panel is initially hidden but present
    panel.style.transition = 'opacity 0.24s ease, transform 0.24s ease';
    panel.style.visibility = 'hidden'; panel.style.opacity = '0'; panel.style.transform = 'translateY(12px)'; panel.style.pointerEvents = 'none';

    // attach single click handler to freshly created fab
    if (fab) {
      fab.addEventListener('click', (ev) => {
        console.log('Button clicked');
        ev.stopPropagation();
        if (panel.classList.contains('open')) { closePanel(); }
        else { openPanel(); }
      }, { once: false });
    }

    // other bindings
    sendBtn && sendBtn.addEventListener('click', ()=>{ doSearch(inputEl.value); inputEl.value=''; });
    inputEl && inputEl.addEventListener('keydown',(e)=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); doSearch(inputEl.value); inputEl.value=''; } setTimeout(()=>{ inputEl.style.height='auto'; inputEl.style.height=Math.min(120,inputEl.scrollHeight)+'px'; },0); });
    deleteBtn && deleteBtn.addEventListener('click', deleteConversation);
    returnBtn && returnBtn.addEventListener('click', doReturnBook);
    closeBtn && closeBtn.addEventListener('click', ()=>{ closePanel(); });

    // delegate return button clicks for result items inside messages
    messagesEl.addEventListener('click', async (e) => {
      const btn = e.target.closest && e.target.closest('.edu-return-result');
      if (!btn) return;
      const bid = btn.dataset.borrowId;
      if (!bid) return;
      if (!confirm('Bu ödünç kitabı iade etmek istiyor musunuz?')) return;
      try{
        const res = await fetch('/api/return-borrowing', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ borrow_id: parseInt(bid) }) });
        const data = await res.json();
        if (res.ok && data.ok){
          addMessage('İade başarılı.', 'bot');
          btn.disabled = true; btn.textContent = 'İade edildi';
        } else if (data && data.error){
          addMessage(data.message || data.error, 'bot');
        } else {
          addMessage('Sunucudan beklenmeyen yanıt alındı.', 'bot');
        }
      }catch(e){ addMessage('Network error while returning book.', 'bot'); }
    });

    document.querySelectorAll('.edu-quick').forEach(b=> b.addEventListener('click', ()=>{ const q=b.dataset.q||b.innerText||''; inputEl.value=q; doSearch(q); }));

    // initial seed message
    setTimeout(()=>{ addMessage('Merhaba! Ben EduBot — kitaplar, veri setleri veya sınavlarla ilgili sorular sorabilirsiniz.', 'bot'); }, 600);

      // mark initialized
      window.__eduBotInitialized = true;
      console.log('EduBot initialized');
    } catch (err) {
      console.error('EduBot initialization failed', err);
    }
  });
