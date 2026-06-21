(function () {
  if (typeof SUMMARY === 'undefined') return;
  const labs = SUMMARY.labs;
  const days = SUMMARY.days;

  // ---- Hover photo preview ----
  const photos = (typeof PHOTOS_MAP === 'object' && PHOTOS_MAP) ? PHOTOS_MAP : {};
  const photoBase = typeof PHOTO_BASE === 'string' ? PHOTO_BASE : '/uploads/photos/';
  let tip = document.querySelector('.photo-tip');
  if (!tip) {
    tip = document.createElement('div');
    tip.className = 'photo-tip';
    document.body.appendChild(tip);
  }
  function hideTip() { tip.style.display = 'none'; }
  function showTip(td) {
    const labId = td.dataset.labId;
    const day = td.dataset.day;
    if (!labId || !day) return;
    const list = (photos[labId] && photos[labId][day]) || [];
    if (!list.length) return;
    const fr = td.getAttribute('title') || '';
    tip.innerHTML =
      `<div class="photo-tip-head">${fr}</div>` +
      list.map(p => `
        <figure class="photo-tip-item">
          <img src="${photoBase}${encodeURIComponent(p.filename)}" loading="lazy" alt="">
          ${p.caption ? `<figcaption>${p.caption.replace(/[<>]/g,'')}</figcaption>` : ''}
        </figure>`).join('');
    const rect = td.getBoundingClientRect();
    tip.style.display = 'block';
    const tipW = tip.offsetWidth || 320;
    let left = rect.right + 8 + window.scrollX;
    if (left + tipW > window.scrollX + window.innerWidth - 8) {
      left = rect.left + window.scrollX - tipW - 8;
    }
    tip.style.left = left + 'px';
    tip.style.top = (rect.top + window.scrollY) + 'px';
  }
  document.querySelectorAll('td.activity-cell[data-lab-id]').forEach(td => {
    td.addEventListener('mouseenter', () => showTip(td));
    td.addEventListener('mouseleave', hideTip);
  });
  window.addEventListener('scroll', hideTip, { passive: true });

  // ---- Click-to-zoom cell modal ----
  let currentPhotos = [];
  let lbIndex = 0;
  const modalEl   = document.getElementById('cellModal');
  const cellModal = modalEl ? new bootstrap.Modal(modalEl) : null;

  function statCard(label, value, sub) {
    return `
      <div class="col-sm-4">
        <div class="stat-card">
          <div class="stat-label">${label}</div>
          <div class="stat-value">${value}</div>
          ${sub ? `<div class="stat-sub">${sub}</div>` : ''}
        </div>
      </div>`;
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function openCellModal(td) {
    if (!cellModal) return;
    hideTip();
    const labId = td.dataset.labId;
    const day = td.dataset.day;
    const lab = SUMMARY.labs.find(l => String(l.id) === String(labId));
    if (!lab) return;
    const cell = lab.days[day];
    const photoList = (photos[labId] && photos[labId][day]) || [];
    if (!cell.drs && !photoList.length) return;

    const date = `${day} ${SUMMARY.monthName} ${SUMMARY.year}`;
    document.getElementById('cellModalTitle').textContent = `${lab.name}`;
    document.getElementById('cellModalSub').textContent = `Tanggal ${date}`;
    document.getElementById('cellModalStats').innerHTML =
      statCard('Frekuensi (FR)', cell.fr, 'sesi/kelas hari ini') +
      statCard('Jumlah Pengguna (JLH)', cell.jlh, 'taruna/peserta') +
      statCard('Durasi (DRS)', cell.drs + ' jam', 'penggunaan sarana');

    const ket = document.getElementById('cellModalKeterangan');
    if (lab.keterangan) {
      ket.innerHTML = `<b>Keterangan:</b> ${escapeHtml(lab.keterangan)}`;
      ket.classList.remove('d-none');
    } else {
      ket.classList.add('d-none');
    }

    const grid = document.getElementById('cellModalPhotos');
    const noPhotos = document.getElementById('cellModalNoPhotos');
    const hint = document.getElementById('cellModalHint');
    if (photoList.length) {
      grid.innerHTML = photoList.map((p, i) => `
        <a href="#" class="photo-tile" data-index="${i}">
          <img src="${photoBase}${encodeURIComponent(p.filename)}" loading="lazy" alt="">
          ${p.caption ? `<span class="photo-tile-cap">${escapeHtml(p.caption)}</span>` : ''}
        </a>`).join('');
      hint.textContent = `${photoList.length} foto — klik untuk perbesar`;
      noPhotos.classList.add('d-none');
      currentPhotos = photoList;
      grid.querySelectorAll('.photo-tile').forEach(a => {
        a.addEventListener('click', e => {
          e.preventDefault();
          openLightbox(Number(a.dataset.index));
        });
      });
    } else {
      grid.innerHTML = '';
      noPhotos.classList.remove('d-none');
      hint.textContent = '';
      currentPhotos = [];
    }
    cellModal.show();
  }

  document.querySelectorAll('td.activity-cell[role="button"]').forEach(td => {
    td.addEventListener('click', () => openCellModal(td));
    td.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openCellModal(td);
      }
    });
  });

  // ---- Lightbox (fullscreen photo viewer) ----
  const lb = document.getElementById('lightbox');
  const lbImg = document.getElementById('lightboxImg');
  const lbCap = document.getElementById('lightboxCaption');

  function openLightbox(i) {
    if (!lb) return;
    lbIndex = i;
    renderLightbox();
    lb.classList.add('show');
    lb.setAttribute('aria-hidden', 'false');
  }
  function closeLightbox() {
    if (!lb) return;
    lb.classList.remove('show');
    lb.setAttribute('aria-hidden', 'true');
  }
  function renderLightbox() {
    const p = currentPhotos[lbIndex];
    if (!p) return;
    lbImg.src = photoBase + encodeURIComponent(p.filename);
    lbCap.textContent = `${p.caption || ''} ${currentPhotos.length > 1 ? `(${lbIndex+1}/${currentPhotos.length})` : ''}`.trim();
  }
  function shift(delta) {
    if (!currentPhotos.length) return;
    lbIndex = (lbIndex + delta + currentPhotos.length) % currentPhotos.length;
    renderLightbox();
  }
  if (lb) {
    lb.querySelector('.lightbox-close').addEventListener('click', closeLightbox);
    lb.querySelector('.lightbox-prev').addEventListener('click', () => shift(-1));
    lb.querySelector('.lightbox-next').addEventListener('click', () => shift(+1));
    lb.addEventListener('click', e => { if (e.target === lb) closeLightbox(); });
    document.addEventListener('keydown', e => {
      if (!lb.classList.contains('show')) return;
      if (e.key === 'Escape') closeLightbox();
      else if (e.key === 'ArrowLeft') shift(-1);
      else if (e.key === 'ArrowRight') shift(+1);
    });
  }

  // ---- Bootstrap tooltips on lab names ----
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // ---- Static-mode period picker ----
  const periodPicker = document.getElementById('periodPicker');
  if (periodPicker) {
    periodPicker.addEventListener('change', () => {
      const v = periodPicker.value;  // "YYYY-MM"
      if (/^\d{4}-\d{2}$/.test(v)) location.href = `/${v}.html`;
    });
  }
  const palette = [
    '#0b3d91', '#1f77b4', '#2ca02c', '#ff7f0e', '#d62728',
    '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22',
    '#7f7f7f', '#aec7e8', '#ffbb78',
  ];

  // Durasi per lab (bar)
  new Chart(document.getElementById('chartByLab'), {
    type: 'bar',
    data: {
      labels: labs.map(l => l.code),
      datasets: [{
        label: 'Durasi (jam)',
        data: labs.map(l => Number(l.drs_total.toFixed(1))),
        backgroundColor: '#0b3d91',
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: {
          title: items => labs[items[0].dataIndex].name,
        }},
      },
      scales: { y: { beginAtZero: true } },
    },
  });

  // Pie distribusi pengguna
  const jpData = labs.map(l => l.jp_total);
  new Chart(document.getElementById('chartShare'), {
    type: 'doughnut',
    data: {
      labels: labs.map(l => l.code),
      datasets: [{
        data: jpData,
        backgroundColor: labs.map((_, i) => palette[i % palette.length]),
      }],
    },
    options: {
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } },
        tooltip: { callbacks: { label: ctx => {
          const total = jpData.reduce((a,b)=>a+b,0) || 1;
          const pct = (ctx.parsed / total * 100).toFixed(1);
          return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
        }}},
      },
    },
  });

  // Durasi harian — stacked bars (lebih jelas daripada stacked area karena
  // tiap lab punya segment tegas, tidak tertimpa warna lab lain).
  const daily = Array.from({length: days}, (_, i) => i + 1);
  const dailyDatasets = labs.map((l, i) => ({
    label: l.code,
    data: daily.map(d => l.days[d] ? l.days[d].drs : 0),
    backgroundColor: palette[i % palette.length],
    borderColor: 'rgba(255,255,255,0.85)',
    borderWidth: 0.5,
    stack: 'durasi',
    hidden: l.drs_total === 0,  // lab tanpa aktivitas disembunyikan
  }));
  new Chart(document.getElementById('chartDaily'), {
    type: 'bar',
    data: { labels: daily, datasets: dailyDatasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, font: { size: 10 }, padding: 8 },
        },
        tooltip: {
          callbacks: {
            title: items => `Tanggal ${items[0].label}`,
            label:  ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)} jam`,
            footer: items => {
              const total = items.reduce((sum, it) => sum + it.parsed.y, 0);
              return `Total hari: ${total.toFixed(1)} jam`;
            },
          },
        },
      },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { stacked: true, beginAtZero: true, ticks: { font: { size: 10 } },
             title: { display: true, text: 'Durasi (jam)', font: { size: 11 } } },
      },
    },
  });
})();
