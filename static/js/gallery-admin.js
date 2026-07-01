// Admin-only: wire the Edit buttons in the gallery to a shared Bootstrap modal.
(function () {
  const modalEl = document.getElementById('editPhotoModal');
  if (!modalEl) return;

  // Lazy-construct the Bootstrap Modal so a script-order regression surfaces
  // as a clear console error instead of a silent IIFE crash that wipes out
  // every click handler below it.
  let _modal = null;
  function getModal() {
    if (_modal) return _modal;
    if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
      console.error('[gallery-admin] bootstrap.Modal not loaded — Edit button cannot open the dialog.');
      return null;
    }
    _modal = new bootstrap.Modal(modalEl);
    return _modal;
  }

  const form      = document.getElementById('editPhotoForm');
  const preview   = document.getElementById('editPhotoPreview');
  const fileLabel = document.getElementById('editPhotoFilename');
  const dateInp   = document.getElementById('editPhotoDate');
  const labSel    = document.getElementById('editPhotoLab');
  const capInp    = document.getElementById('editPhotoCaption');
  const fileInp   = document.getElementById('editPhotoFile');
  const dropzone  = document.getElementById('editPhotoDropzone');
  const hint      = document.getElementById('editPhotoHint');
  const submit    = document.getElementById('editPhotoSubmit');

  if (window.SPPDropzone) SPPDropzone.enable(dropzone, fileInp);

  const MAX_BYTES = 2 * 1024 * 1024;
  const ALLOWED   = ['png', 'jpg', 'jpeg', 'webp'];
  const origPreview = { src: '', filename: '' };

  function setHint(text, kind) {
    hint.textContent = text || '';
    hint.className = 'small mt-1 ' + (kind ? 'text-' + kind : '');
  }

  fileInp.addEventListener('change', () => {
    setHint('');
    submit.disabled = false;
    const f = fileInp.files[0];
    if (!f) {
      preview.src = origPreview.src;
      fileLabel.textContent = origPreview.filename;
      return;
    }
    const ext = (f.name.split('.').pop() || '').toLowerCase();
    if (!ALLOWED.includes(ext)) {
      setHint(`Format .${ext} tidak diterima. Gunakan PNG, JPG, JPEG, atau WebP.`, 'danger');
      submit.disabled = true;
      return;
    }
    if (f.size > MAX_BYTES) {
      const mb = (f.size / (1024 * 1024)).toFixed(2);
      setHint(`Ukuran foto ${mb} MB melebihi batas 2 MB.`, 'danger');
      submit.disabled = true;
      return;
    }
    const url = URL.createObjectURL(f);
    preview.src = url;
    fileLabel.textContent = `Penggantian: ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
    setHint('Foto baru siap diunggah.', 'success');
  });

  async function checkActivity() {
    const labId = labSel.value;
    const date  = dateInp.value;
    if (!labId || !date) {
      submit.disabled = false;
      return;
    }
    try {
      const r = await fetch(`/api/activity-check?lab_id=${labId}&date=${date}`);
      const j = await r.json();
      if (!j.ok) return;
      if (!j.has_activity) {
        setHint(
          `Tidak ada aktivitas tercatat pada ${date} untuk lab ini. ` +
          `Catat data utilisasi dulu, atau pilih "Umum / tidak spesifik".`,
          'danger',
        );
        submit.disabled = true;
      } else {
        // Don't overwrite a file-validation success/error message.
        if (!hint.textContent || hint.classList.contains('text-success')) {
          setHint(`Aktivitas tercatat: FR ${j.fr} / JLH ${j.jlh} / DRS ${j.drs} jam.`, 'success');
        }
        submit.disabled = false;
      }
    } catch { /* network ignored */ }
  }
  labSel.addEventListener('change', checkActivity);
  dateInp.addEventListener('change', checkActivity);

  document.querySelectorAll('.js-edit-photo').forEach(btn => {
    btn.addEventListener('click', () => {
      const d = btn.dataset;
      form.action = `/admin/photo/${d.id}/edit`;
      dateInp.value = d.eventDate || '';
      labSel.value  = d.labId || '';
      capInp.value  = d.caption || '';
      fileInp.value = '';
      origPreview.src = `/uploads/photos/${d.filename}`;
      origPreview.filename = `Saat ini: ${d.filename}`;
      preview.src = origPreview.src;
      fileLabel.textContent = origPreview.filename;
      setHint('');
      submit.disabled = false;
      const m = getModal();
      if (m) m.show();
    });
  });
})();
