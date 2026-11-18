(function () {
  if (typeof SUMMARY === 'undefined') return;
  const labs = SUMMARY.labs;
  const days = SUMMARY.days;
  const fmt = (v, dec = 0) => Number(v).toLocaleString('id-ID',
    { minimumFractionDigits: dec, maximumFractionDigits: dec });

  // ---- Hover photo preview ----
  const photos = (typeof PHOTOS_MAP === 'object' && PHOTOS_MAP) ? PHOTOS_MAP : {};
  const details = (typeof DETAILS_MAP === 'object' && DETAILS_MAP) ? DETAILS_MAP : {};
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
    const photoList  = (photos[labId]  && photos[labId][day])  || [];
    const detailList = (details[labId] && details[labId][day]) || [];
    if (!cell.drs && !photoList.length && !detailList.length) return;

    const date = `${day} ${SUMMARY.monthName} ${SUMMARY.year}`;
    document.getElementById('cellModalTitle').textContent = `${lab.name}`;
    document.getElementById('cellModalSub').textContent = `Tanggal ${date}`;
    document.getElementById('cellModalStats').innerHTML =
      statCard('Frekuensi (FR)', fmt(cell.fr), 'sesi/kelas hari ini') +
      statCard('Jumlah Pengguna (JLH)', fmt(cell.jlh), 'taruna/peserta') +
      statCard('Durasi (DRS)', fmt(cell.drs, 1) + ' jam', 'penggunaan sarana');

    const ket = document.getElementById('cellModalKeterangan');
    if (lab.keterangan) {
      ket.innerHTML = `<b>Keterangan:</b> ${escapeHtml(lab.keterangan)}`;
      ket.classList.remove('d-none');
    } else {
      ket.classList.add('d-none');
    }

    const detailWrap = document.getElementById('cellModalDetailWrap');
    const detailList_el = document.getElementById('cellModalDetailList');
    if (detailWrap && detailList_el) {
      if (detailList.length) {
        detailList_el.innerHTML = detailList.map(d => {
          const who = escapeHtml(d.users || '—');
          const jab = escapeHtml(d.jabatan || '—');
          const what = escapeHtml(d.activity || '—');
          return (
            `<li class="detail-row">` +
              `<div><span class="detail-label">Pengguna:</span> <span class="detail-value">${who}</span></div>` +
              `<div><span class="detail-label">Jabatan:</span> <span class="detail-value">${jab}</span></div>` +
              `<div><span class="detail-label">Kegiatan:</span> <span class="detail-value">${what}</span></div>` +
            `</li>`
          );
        }).join('');
        detailWrap.classList.remove('d-none');
      } else {
        detailWrap.classList.add('d-none');
        detailList_el.innerHTML = '';
      }
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
  // One muted colour per lab id, same in every chart. No red (red = libur).
  const LAB_COLOR = {
    1: '#0b3d91', 2: '#5b7fb5', 3: '#8a9bb0', 4: '#3f6e6a', 9: '#4a5a78',
    10: '#9c8457', 12: '#6f8f86', 13: '#a7b4c6', 14: '#7d6f8f',
  };
  const labColor = l => LAB_COLOR[l.id] || '#9aa5b4';
  Chart.defaults.font.family = "'DM Sans', system-ui, sans-serif";
  Chart.defaults.color = '#5b6474';

  // Ranked horizontal bars; labs with zero value are dropped.
  function rankedBar(id, key, unit, dec) {
    const rows = labs.filter(l => l[key] > 0).sort((a, b) => b[key] - a[key]);
    const total = rows.reduce((s, l) => s + l[key], 0) || 1;
    new Chart(document.getElementById(id), {
      type: 'bar',
      data: {
        labels: rows.map(l => l.code),
        datasets: [{ data: rows.map(l => l[key]), backgroundColor: rows.map(labColor), borderRadius: 2 }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: {
            title: items => rows[items[0].dataIndex].name,
            label: ctx => `${fmt(ctx.parsed.x, dec)} ${unit} (${fmt(ctx.parsed.x / total * 100, 1)}%)`,
          }},
        },
        scales: {
          x: { beginAtZero: true, ticks: { callback: v => fmt(v) } },
          y: { grid: { display: false } },
        },
      },
    });
  }
  rankedBar('chartByLab', 'drs_total', 'jam', 1);
  rankedBar('chartShare', 'jp_total', 'orang', 0);

  // Durasi harian — stacked bars (lebih jelas daripada stacked area karena
  // tiap lab punya segment tegas, tidak tertimpa warna lab lain).
  const daily = Array.from({length: days}, (_, i) => i + 1);
  const dailyDatasets = labs.filter(l => l.drs_total > 0).map(l => ({
    label: l.code,
    data: daily.map(d => l.days[d] ? l.days[d].drs : 0),
    backgroundColor: labColor(l),
    borderColor: '#ffffff',
    borderWidth: 0.5,
    stack: 'durasi',
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
            label:  ctx => `${ctx.dataset.label}: ${fmt(ctx.parsed.y, 1)} jam`,
            footer: items => {
              const total = items.reduce((sum, it) => sum + it.parsed.y, 0);
              return `Total hari: ${fmt(total, 1)} jam`;
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
