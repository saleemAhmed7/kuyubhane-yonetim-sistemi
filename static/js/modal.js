(function(){
  function showModal(opts){
    // opts: { title, body, placeholder, confirmText, cancelText, showInput }
    return new Promise((resolve)=>{
      const modal = document.getElementById('global-modal');
      const titleEl = document.getElementById('global-modal-title');
      const bodyEl = document.getElementById('global-modal-body');
      const inputWrap = document.getElementById('global-modal-input-wrap');
      const inputEl = document.getElementById('global-modal-input');
      const confirmBtn = document.getElementById('global-modal-confirm');
      const cancelBtn = document.getElementById('global-modal-cancel');

      titleEl.textContent = opts.title || '';
      bodyEl.textContent = opts.body || '';
      if (opts.showInput){ inputWrap.style.display='block'; inputEl.value = opts.value || ''; inputEl.placeholder = opts.placeholder || ''; } else { inputWrap.style.display='none'; }
      confirmBtn.textContent = opts.confirmText || 'Confirm';
      cancelBtn.textContent = opts.cancelText || 'Cancel';

      modal.style.display = 'block';
      setTimeout(()=> modal.classList.add('open'), 10);

      function cleanup(){
        modal.classList.remove('open');
        setTimeout(()=>{ modal.style.display='none'; }, 220);
        confirmBtn.removeEventListener('click', onConfirm);
        cancelBtn.removeEventListener('click', onCancel);
      }
      function onConfirm(){ cleanup(); resolve({confirmed:true, value: inputEl.value}); }
      function onCancel(){ cleanup(); resolve({confirmed:false}); }
      confirmBtn.addEventListener('click', onConfirm);
      cancelBtn.addEventListener('click', onCancel);
      if (opts.showInput) setTimeout(()=> inputEl.focus(),120);
    });
  }
  window.showGlobalModal = showModal;
})();

// Global Fetch Interceptor for graceful Session Expiration / Authorization errors
(function() {
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    try {
      const response = await originalFetch(...args);
      if (response.status === 401) {
        // Session Expired / Unauthorized
        const data = await response.clone().json().catch(() => ({}));
        const msg = data.message || "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın.";
        
        // Prevent showing duplicate modals simultaneously
        if (!window.__sessionModalShowing) {
          window.__sessionModalShowing = true;
          window.showGlobalModal({
            title: "Oturum Süresi Doldu",
            body: msg,
            showInput: false,
            confirmText: "Giriş Yap",
            cancelText: "İptal"
          }).then((res) => {
            window.__sessionModalShowing = false;
            if (res.confirmed) {
              window.location.href = "/login";
            }
          });
        }
      } else if (response.status === 403) {
        // Forbidden / Unauthorized Access
        const data = await response.clone().json().catch(() => ({}));
        const msg = data.message || "Bu işlem için yetkiniz bulunmamaktadır.";
        window.showGlobalModal({
          title: "Yetki Hatası",
          body: msg,
          showInput: false,
          confirmText: "Tamam",
          cancelText: "Kapat"
        });
      }
      return response;
    } catch (err) {
      return originalFetch(...args);
    }
  };
})();
