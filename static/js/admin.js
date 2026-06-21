(function () {
  if (typeof PERIOD === 'undefined') return;

  const debounce = (fn, ms) => {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  };

  function rowTotals(tr) {
    let frTotal = 0, jpTotal = 0, drsTotal = 0;
    tr.querySelectorAll('input.cell-input').forEach(inp => {
      const v = parseFloat(inp.value) || 0;
      if (inp.dataset.kind === 'fr') frTotal += v;
      if (inp.dataset.kind === 'jlh') jpTotal += v;
      if (inp.dataset.kind === 'drs') drsTotal += v;
    });
    tr.querySelector('[data-total="fr"]').textContent = frTotal.toFixed(0);
    tr.querySelector('[data-total="jp"]').textContent = jpTotal.toFixed(0);
    tr.querySelector('[data-total="drs"]').textContent = drsTotal.toFixed(1);
  }

  async function saveEntry(tr, day) {
    const labId = tr.dataset.labId;
    const cells = Array.from(tr.querySelectorAll(`input.cell-input[data-day="${day}"]`));
    const payload = { lab_id: labId, year: PERIOD.year, month: PERIOD.month, day: Number(day) };
    cells.forEach(c => payload[c.dataset.kind] = c.value || 0);

    // Client-side guardrail: clearing a cell that previously held data requires confirmation.
    const origs = cells.map(c => parseFloat(c.dataset.original || '0') || 0);
    const news  = cells.map(c => parseFloat(c.value || '0') || 0);
    const hadData    = origs.some(v => v > 0);
    const willBeZero = news.every(v => v === 0);
    if (hadData && willBeZero) {
      const ok = window.confirm(
        `Hapus catatan tanggal ${day}?\n\n` +
        `Nilai sebelumnya: FR=${origs[0]}, JLH=${origs[1]}, DRS=${origs[2]}.\n\n` +
        `OK = hapus baris.\nBatal = kembalikan nilai semula.`
      );
      if (!ok) {
        cells.forEach((c, i) => { c.value = origs[i] || ''; });
        rowTotals(tr);
        return;
      }
      payload.confirm_delete = true;
    }

    try {
      const r = await fetch('/admin/entry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (r.status === 409) {
        const j = await r.json();
        const prev = j.previous || {};
        window.alert(
          `Server menolak penghapusan: ${j.message || 'konfirmasi diperlukan'}\n\n` +
          `Nilai sebelumnya: FR=${prev.fr ?? '?'}, JLH=${prev.jlh ?? '?'}, DRS=${prev.drs ?? '?'}.\n` +
          `Nilai dikembalikan.`
        );
        cells.forEach((c, i) => { c.value = origs[i] || ''; });
        rowTotals(tr);
        return;
      }
      if (!r.ok) throw new Error();
      cells.forEach(c => {
        c.dataset.original = c.value || '0';
        c.classList.add('cell-saved');
        setTimeout(() => c.classList.remove('cell-saved'), 700);
      });
    } catch {
      cells.forEach(c => c.classList.add('cell-error'));
    }
  }

  async function saveKeterangan(tr) {
    const labId = tr.dataset.labId;
    const note = tr.querySelector('input.ket-input').value;
    await fetch('/admin/keterangan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lab_id: labId, year: PERIOD.year, month: PERIOD.month, note }),
    });
  }

  // ---- Photo form: live activity check ----
  const photoForm   = document.getElementById('photoForm');
  const photoDate   = document.getElementById('photoDate');
  const photoLab    = document.getElementById('photoLab');
  const photoHint   = document.getElementById('photoHint');
  const photoSubmit = document.getElementById('photoSubmit');

  async function checkActivity() {
    if (!photoForm) return;
    photoHint.textContent = '';
    photoSubmit.disabled = false;
    const labId = photoLab.value;
    const date = photoDate.value;
    if (!labId || !date) return;  // Umum or incomplete -> always allow
    try {
      const r = await fetch(`/api/activity-check?lab_id=${labId}&date=${date}`);
      const j = await r.json();
      if (!j.ok) return;
      if (j.has_activity) {
        photoHint.className = 'small ms-2 text-success';
        photoHint.textContent = `Aktivitas tercatat: FR ${j.fr} / JLH ${j.jlh} / DRS ${j.drs} jam.`;
      } else {
        photoHint.className = 'small ms-2 text-danger';
        photoHint.textContent = `Tidak ada aktivitas tercatat pada ${date} untuk lab ini. Catat data utilisasi dulu, atau pilih "Umum / tidak spesifik".`;
        photoSubmit.disabled = true;
      }
    } catch { /* network ignored */ }
  }
  if (photoLab) photoLab.addEventListener('change', checkActivity);
  if (photoDate) photoDate.addEventListener('change', checkActivity);

  const photoFile = document.getElementById('photoFile');
  if (photoForm && photoFile) {
    const MAX_BYTES = 2 * 1024 * 1024;
    const ALLOWED = ['png', 'jpg', 'jpeg', 'webp'];
    photoFile.addEventListener('change', () => {
      photoHint.textContent = '';
      photoSubmit.disabled = false;
      const f = photoFile.files[0];
      if (!f) return;
      const ext = (f.name.split('.').pop() || '').toLowerCase();
      if (!ALLOWED.includes(ext)) {
        photoHint.className = 'small ms-2 text-danger';
        photoHint.textContent = `Format .${ext} tidak diterima. Gunakan PNG, JPG, JPEG, atau WebP.`;
        photoSubmit.disabled = true;
        return;
      }
      if (f.size > MAX_BYTES) {
        const mb = (f.size / (1024 * 1024)).toFixed(2);
        photoHint.className = 'small ms-2 text-danger';
        photoHint.textContent = `Ukuran foto ${mb} MB melebihi batas 2 MB.`;
        photoSubmit.disabled = true;
        return;
      }
      const kb = (f.size / 1024).toFixed(1);
      photoHint.className = 'small ms-2 text-success';
      photoHint.textContent = `Foto OK (${kb} KB, .${ext}).`;
    });
  }

  const tbl = document.getElementById('editTable');
  if (!tbl) return;

  tbl.querySelectorAll('tr[data-lab-id]').forEach(tr => {
    tr.querySelectorAll('input.cell-input').forEach(inp => {
      inp.dataset.original = inp.value || '0';
      const day = inp.dataset.day;
      const debounced = debounce(() => saveEntry(tr, day), 600);
      inp.addEventListener('input', () => {
        rowTotals(tr);
        debounced();
      });
    });
    const ketDeb = debounce(() => saveKeterangan(tr), 700);
    tr.querySelector('input.ket-input').addEventListener('input', ketDeb);
  });

  // ---- Import form: reveal overwrite confirm input only when checkbox is set ----
  const owCheck = document.getElementById('ow');
  const owConfirm = document.getElementById('owConfirm');
  const importForm = document.getElementById('importForm');
  if (owCheck && owConfirm && importForm) {
    owCheck.addEventListener('change', () => {
      owConfirm.classList.toggle('d-none', !owCheck.checked);
      if (!owCheck.checked) owConfirm.value = '';
    });
    importForm.addEventListener('submit', (e) => {
      if (owCheck.checked && owConfirm.value.trim().toUpperCase() !== 'OVERWRITE') {
        e.preventDefault();
        owConfirm.classList.remove('d-none');
        owConfirm.focus();
        window.alert("Untuk mode 'Timpa data', ketik OVERWRITE pada kolom konfirmasi.");
        return;
      }
      if (owCheck.checked) {
        if (!window.confirm("Anda akan MENIMPA data periode tersebut. Snapshot tetap dibuat sebelum import. Lanjutkan?")) {
          e.preventDefault();
        }
      }
    });
  }
})();
