document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.querySelector(".sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    }
    // Book bot: search dataset and render results
    const botQuery = document.getElementById("bot-query");
    const botSearch = document.getElementById("bot-search");
    const botResults = document.getElementById("bot-results");

    function renderBotResults(data) {
        if (!botResults) return;
        botResults.innerHTML = "";
        if (!data || !data.results || data.results.length === 0) {
            botResults.innerHTML = '<div class="text-muted">No results.</div>';
            return;
        }
        data.results.forEach((r) => {
            const item = document.createElement('div');
            item.className = 'result-item';
            item.innerHTML = `
                <img src="${r.image}" alt="cover" onerror="this.src='/static/images/profiles/default.png'">
                <div style="flex:1">
                    <strong>${r.title}</strong>
                    <div class="text-secondary small">${r.author}</div>
                    <p class="mb-0 mt-1 small text-muted">${r.explanation}</p>
                </div>
            `;
            botResults.appendChild(item);
        });
    }

    async function performBotSearch() {
        if (!botQuery) return;
        const q = botQuery.value.trim();
        botResults && (botResults.innerHTML = '<div class="col-12 text-muted">Searching…</div>');
        try {
            const res = await fetch(`/api/book-bot?q=${encodeURIComponent(q)}`);
            if (!res.ok) {
                renderBotResults({ results: [] });
                return;
            }
            const data = await res.json();
            renderBotResults(data);
        } catch (e) {
            renderBotResults({ results: [] });
        }
    }

    if (botSearch) botSearch.addEventListener('click', performBotSearch);
    if (botQuery) botQuery.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); performBotSearch(); } });

    // Removed legacy book-bot toggle to avoid conflicts with EduBot

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll(".alert").forEach((alert) => {
        setTimeout(() => {
            bootstrap.Alert.getOrCreateInstance(alert).close();
        }, 4500);
    });

    const categoryChart = document.getElementById("categoryChart");
    if (categoryChart && window.Chart) {
        const labels = JSON.parse(categoryChart.dataset.labels || "[]");
        const values = JSON.parse(categoryChart.dataset.values || "[]");
        new Chart(categoryChart, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Copies",
                    data: values,
                    borderRadius: 8,
                    backgroundColor: ["#22d3ee", "#34d399", "#a78bfa", "#fb923c", "#f472b6", "#60a5fa"],
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: "#b6c2d5" }, grid: { color: "rgba(255,255,255,0.04)" } },
                    y: { ticks: { color: "#b6c2d5" }, grid: { color: "rgba(255,255,255,0.08)" } },
                },
            },
        });
    }

    // EduBot chat widget logic
    const eduFab = document.getElementById('edu-bot-fab');
    const eduPanel = document.getElementById('edu-bot-panel');
    const eduClose = document.getElementById('edu-bot-close');
    const eduClear = document.getElementById('edu-clear');
    const eduMessages = document.getElementById('edu-messages');
    const eduInput = document.getElementById('edu-input');
    const eduSend = document.getElementById('edu-send');

    function timeStamp() {
        const d = new Date();
        return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    const STORAGE_KEY = 'edu_messages_v1';

    function escapeHtml(str) {
        if (!str && str !== '') return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/\'/g, '&#39;');
    }

    function renderFromObj(obj) {
        if (!eduMessages) return;
        const el = document.createElement('div');
        el.className = 'msg ' + (obj.who === 'user' ? 'user' : 'bot');
        const contentHtml = obj.html ? obj.html : `<div class="content">${escapeHtml(obj.text)}</div>`;
        el.innerHTML = `${contentHtml}<span class="ts">${obj.ts || timeStamp()}</span>`;
        eduMessages.appendChild(el);
    }

    function saveMessage(obj) {
        try {
            const arr = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            arr.push(obj);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
        } catch (e) { /* ignore storage errors */ }
    }

    function getStoredMessages() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch (e) { return []; }
    }

    function loadMessages() {
        if (!eduMessages) return;
        eduMessages.innerHTML = '';
        const arr = getStoredMessages();
        arr.forEach(renderFromObj);
        eduMessages.scrollTop = eduMessages.scrollHeight;
    }

    function clearMessages() {
        try { localStorage.removeItem(STORAGE_KEY); } catch(e) {}
        if (eduMessages) eduMessages.innerHTML = '';
    }

    function addMessage(text, who='bot') {
        if (!eduMessages) return;
        const obj = { who, text: text || '', html: null, ts: timeStamp() };
        saveMessage(obj);
        renderFromObj(obj);
        eduMessages.scrollTop = eduMessages.scrollHeight;
    }
    function createTypingElement() {
        const el = document.createElement('div');
        el.className = 'msg bot typing';
        el.innerHTML = `<div class="content"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div><span class="ts">${timeStamp()}</span>`;
        return el;
    }

    function createBotMessageHTML({title, authors, description, image, serial_number, shelf_location, order_position, available_copies}){
        const authorText = authors ? authors.join(', ') : '';
        const desc = description ? (description.length>320 ? description.slice(0,320)+'...' : description) : '';
        let html = '<div style="display:flex;gap:10px;align-items:flex-start">';
        if (image) html += `<img class="book-cover" src="${image}" alt="cover" onerror="this.style.display=\'none\'">`;
        html += `<div><strong>${title || ''}</strong>`;
        if (authorText) html += `<div class="text-secondary small">${authorText}</div>`;
        if (serial_number) html += `<div class="small text-muted">Serial: <strong>#${serial_number}</strong></div>`;
        if (shelf_location || order_position) html += `<div class="text-muted small">${shelf_location ? 'Shelf: ' + shelf_location : ''}${shelf_location && order_position ? ' • ' : ''}${order_position ? 'Order: ' + order_position : ''}</div>`;
        if (available_copies !== undefined) html += `<div class="text-muted small">Available: ${available_copies}</div>`;
        if (desc) html += `<p class="mb-0 mt-1 small text-muted">${desc}</p>`;
        html += '</div>';
        html += '</div>';
        return html;
    }
    async function createCoverFromGoogle(title, author) {
        try {
            const q = encodeURIComponent((title||'') + ' ' + (author||''));
            const res = await fetch(`https://www.googleapis.com/books/v1/volumes?q=${q}&maxResults=1`);
            if (!res.ok) return null;
            const data = await res.json();
            if (data.totalItems && data.items && data.items.length>0) {
                const v = data.items[0].volumeInfo || {};
                return (v.imageLinks && (v.imageLinks.thumbnail || v.imageLinks.smallThumbnail)) || null;
            }
        } catch (e) { }
        return null;
    }

    async function fetchBookData(query) {
        if (!query) return null;
        // First try server-side DB search (serial, title, author, category)
        try {
            const res = await fetch(`/api/book-info?q=${encodeURIComponent(query)}`);
            if (res.ok) {
                const data = await res.json();
                if (data && data.results && data.results.length>0) {
                    const r = data.results[0];
                    const image = await createCoverFromGoogle(r.title, r.author) || null;
                    return {
                        title: r.title,
                        authors: r.author ? [r.author] : (r.authors || []),
                        description: r.description || r.explanation || '',
                        image: image,
                        serial_number: r.serial_number,
                        shelf_location: r.shelf_location,
                        order_position: r.order_position,
                        available_copies: r.available_copies,
                    };
                }
            }
        } catch (e) {
            // ignore and fallback to previous behavior
        }
        // fallback: try Google Books + CSV as before
        try {
            const gRes = await fetch(`https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(query)}&maxResults=1`);
            if (gRes.ok) {
                const gData = await gRes.json();
                if (gData.totalItems && gData.items && gData.items.length>0) {
                    const v = gData.items[0].volumeInfo || {};
                    const image = (v.imageLinks && (v.imageLinks.thumbnail || v.imageLinks.smallThumbnail)) || null;
                    const title = v.title || '';
                    const authors = v.authors || [];
                    const description = v.description || v.subtitle || '';
                    return { title, authors, description, image };
                }
            }
        } catch (e) {}
        try {
            const res = await fetch(`/api/book-bot?q=${encodeURIComponent(query)}`);
            if (!res.ok) return null;
            const data = await res.json();
            if (data && data.results && data.results.length>0) {
                const r = data.results[0];
                return { title: r.title, authors: [r.author], description: r.explanation, image: r.image || null };
            }
        } catch (e) {
            return null;
        }
        return null;
    }

    async function sendChat(text) {
        if (!text || text.trim().length === 0) return;
        addMessage(text, 'user');
        if (eduInput) { eduInput.value = ''; eduInput.style.height = 'auto'; }

        const typingEl = createTypingElement();
        eduMessages.appendChild(typingEl);
        eduMessages.scrollTop = eduMessages.scrollHeight;

        try {
            const info = await fetchBookData(text);
            // remove typing
            typingEl.remove();
            if (info) {
                const html = createBotMessageHTML(info);
                const obj = { who: 'bot', text: info.description || info.title || '', html: html, ts: timeStamp() };
                saveMessage(obj);
                renderFromObj(obj);
                eduMessages.scrollTop = eduMessages.scrollHeight;
                return;
            }
            addMessage('Sorry, I could not find matching books. Try different keywords.', 'bot');
        } catch (e) {
            try { typingEl.remove(); } catch (er) {}
            addMessage('Network error. Please try again.', 'bot');
        }
    }

    // Trap wheel and touch scrolling inside the messages container to prevent page scroll
    function trapScroll(container) {
        if (!container) return;
        container.addEventListener('wheel', function(e) {
            const delta = e.deltaY;
            const canScrollUp = container.scrollTop > 0;
            const canScrollDown = container.scrollTop + container.clientHeight < container.scrollHeight - 1;
            if ((delta < 0 && canScrollUp) || (delta > 0 && canScrollDown)) {
                e.stopPropagation();
                e.preventDefault();
                container.scrollTop += delta;
            }
            // otherwise allow event to bubble so page can scroll when at edges
        }, { passive: false });

        // Touch handling for mobile browsers
        let startY = 0;
        container.addEventListener('touchstart', (e) => { startY = e.touches[0].clientY; }, { passive: true });
        container.addEventListener('touchmove', function(e) {
            const y = e.touches[0].clientY;
            const dy = startY - y;
            const canScrollUp = container.scrollTop > 0;
            const canScrollDown = container.scrollTop + container.clientHeight < container.scrollHeight - 1;
            if ((dy > 0 && canScrollDown) || (dy < 0 && canScrollUp)) {
                e.stopPropagation();
                e.preventDefault();
                container.scrollTop += dy;
                startY = y;
            }
        }, { passive: false });
    }
    trapScroll(eduMessages);

    // Load stored messages at startup
    loadMessages();

    // wire clear button
    if (eduClear) {
        eduClear.addEventListener('click', () => {
            if (!confirm('Clear all chat messages?')) return;
            clearMessages();
        });
    }

    // FAB toggle
    if (eduFab && eduPanel) {
        eduFab.addEventListener('click', () => {
            eduPanel.classList.toggle('open');
            eduPanel.setAttribute('aria-hidden', eduPanel.classList.contains('open') ? 'false' : 'true');
            if (eduPanel.classList.contains('open')) {
                setTimeout(() => { eduInput && eduInput.focus(); }, 160);
            }
        });
    }
    if (eduClose && eduPanel) eduClose.addEventListener('click', () => { eduPanel.classList.remove('open'); eduPanel.setAttribute('aria-hidden','true'); });

    // Close when clicking outside the panel (but not when clicking the FAB)
    document.addEventListener('click', (e) => {
        if (!eduPanel || !eduFab) return;
        const target = e.target;
        if (eduPanel.classList.contains('open')) {
            if (!eduPanel.contains(target) && !eduFab.contains(target)) {
                eduPanel.classList.remove('open');
                eduPanel.setAttribute('aria-hidden', 'true');
            }
        }
    });

    // Close with ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && eduPanel && eduPanel.classList.contains('open')) {
            eduPanel.classList.remove('open');
            eduPanel.setAttribute('aria-hidden', 'true');
            if (eduFab) eduFab.focus();
        }
    });

    if (eduSend && eduInput) {
        eduSend.addEventListener('click', () => { sendChat(eduInput.value); });
        eduInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(eduInput.value); }
            // autosize
            setTimeout(() => { eduInput.style.height = 'auto'; eduInput.style.height = Math.min(120, eduInput.scrollHeight) + 'px'; }, 0);
        });
    }

    // quick actions
    document.querySelectorAll('.edu-quick').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const q = btn.dataset.q || btn.innerText || '';
            if (eduInput) eduInput.value = q;
            sendChat(q);
        });
    });

    // --- Catalog dynamic search + category navigation + cover fetch ---
    const catalogSearch = document.getElementById('catalog-search');
    const catalogClear = document.getElementById('catalog-clear');
    const categoryNav = document.getElementById('category-nav');

    function normalize(s) { return (s||'').toString().toLowerCase(); }

    function filterCatalog() {
        const q = normalize(catalogSearch?.value || '');
        const activeCat = categoryNav?.querySelector('.category-btn.active')?.dataset?.cat || '__all';
        document.querySelectorAll('.book-card').forEach(card => {
            const title = normalize(card.dataset.title);
            const author = normalize(card.dataset.author);
            const cat = card.dataset.category || '';
            let visible = true;
            if (activeCat && activeCat !== '__all' && activeCat !== cat) visible = false;
            if (q) {
                visible = visible && (title.includes(q) || author.includes(q) || (cat && cat.toLowerCase().includes(q)));
            }
            card.closest('.col').style.display = visible ? '' : 'none';
        });
    }

    catalogSearch?.addEventListener('input', () => { filterCatalog(); });
    catalogClear?.addEventListener('click', () => { if (catalogSearch) { catalogSearch.value=''; filterCatalog(); } });

    categoryNav?.addEventListener('click', (e) => {
        const btn = e.target.closest('.category-btn');
        if (!btn) return;
        categoryNav.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // if it's the special all, clear search filter
        if (btn.dataset.cat === '__all') { if (catalogSearch) catalogSearch.value=''; }
        filterCatalog();
    });

    // Google Books cover fetch for cards without src
    async function fetchCoverForCard(imgEl) {
        try {
            const title = imgEl.dataset.title || '';
            const author = imgEl.dataset.author || '';
            if (!title) return;
            const q = encodeURIComponent(title + ' ' + author);
            const res = await fetch(`https://www.googleapis.com/books/v1/volumes?q=${q}&maxResults=1`);
            if (!res.ok) return;
            const data = await res.json();
            if (data.totalItems && data.items && data.items.length>0) {
                const v = data.items[0].volumeInfo || {};
                const image = (v.imageLinks && (v.imageLinks.thumbnail || v.imageLinks.smallThumbnail)) || null;
                if (image) imgEl.src = image.replace(/^http:/,'https:');
                else imgEl.src = '/static/images/profiles/default.png';
            } else {
                imgEl.src = '/static/images/profiles/default.png';
            }
        } catch (e) { imgEl.src = '/static/images/profiles/default.png'; }
    }

        // Delegate handler for Return Book buttons on the borrowings page
        document.addEventListener('click', async function(evt){
            const btn = evt.target.closest && evt.target.closest('.return-borrow-btn');
            if (!btn) return;
            evt.preventDefault();
            const borrowId = btn.dataset.borrowId;
            const bookTitle = btn.dataset.bookTitle || '';
            const serial = btn.dataset.serialNumber || '';
            const title = (window.__i18n && window.__i18n.t) ? window.__i18n.t('button_return_book') : 'Return Book';
            const confirmText = (window.__i18n && window.__i18n.t) ? window.__i18n.t('confirm_are_you_sure') : 'Are you sure?';
            const serialLabel = (window.__i18n && window.__i18n.t) ? window.__i18n.t('serial_label') : 'Serial';
            const body = bookTitle ? (confirmText + '\n' + bookTitle + (serial ? '\n' + serialLabel + ': ' + serial : '')) : (confirmText + (serial ? '\n' + serialLabel + ': ' + serial : ''));
            const conf = await window.showGlobalModal({ title, body, showInput:false, confirmText: (window.__i18n && window.__i18n.t) ? window.__i18n.t('button_confirm') : 'Confirm', cancelText: (window.__i18n && window.__i18n.t) ? window.__i18n.t('button_cancel') : 'Cancel' });
            if (!conf || !conf.confirmed) return;
            try{
                const res = await fetch('/api/return-borrowing', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ borrow_id: parseInt(borrowId) }) });
                const data = await res.json();
                if (res.ok && data && data.ok){
                    const row = btn.closest('tr');
                    if (row){
                        const badge = row.querySelector('.status-badge');
                        if (badge){ badge.textContent = (window.__i18n && window.__i18n.t) ? window.__i18n.t('returned') : 'Returned'; badge.classList.remove('borrowed'); badge.classList.add('returned'); }
                        btn.remove();
                    }
                    await window.showGlobalModal({ title, body: data.message || '', showInput:false, confirmText: (window.__i18n && window.__i18n.t) ? window.__i18n.t('button_close') : 'Close' });
                } else {
                    await window.showGlobalModal({ title: (window.__i18n && window.__i18n.t) ? window.__i18n.t('network_error') : 'Error', body: (data && (data.message || data.error)) || '', showInput:false, confirmText: (window.__i18n && window.__i18n.t) ? window.__i18n.t('button_close') : 'Close' });
                }
            }catch(e){
                await window.showGlobalModal({ title: (window.__i18n && window.__i18n.t) ? window.__i18n.t('network_error') : 'Network error', body:'', showInput:false, confirmText: (window.__i18n && window.__i18n.t) ? window.__i18n.t('button_close') : 'Close' });
            }
        });
    document.querySelectorAll('.book-thumb').forEach(img => {
        if (!img.src || img.src.trim()==='') fetchCoverForCard(img);
        img.addEventListener('error', () => { img.src = '/static/images/profiles/default.png'; });
    });

    // initial filter on page load
    filterCatalog();

    // seed welcome
    setTimeout(() => {
        addMessage('Hello! I am EduBot AI — ask me about books, dataset, or exams. Try "Material Help".', 'bot');
    }, 600);

    // Theme toggle handling (global)
    // Site theme control: reads/writes html[data-theme] = 'light'|'dark'
    function getSiteTheme() { return localStorage.getItem('siteTheme') || 'dark'; }
    function applySiteTheme(theme) {
      if (!theme) theme = 'dark';
      document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : 'dark');
      const icon = document.getElementById('site-theme-icon');
      if (icon) icon.className = theme === 'light' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
      localStorage.setItem('siteTheme', theme === 'light' ? 'light' : 'dark');
    }
    document.getElementById('site-theme-toggle')?.addEventListener('click', () => {
      const current = getSiteTheme();
      applySiteTheme(current === 'light' ? 'dark' : 'light');
    });
    document.addEventListener('DOMContentLoaded', () => applySiteTheme(getSiteTheme()));
});
