(function () {
  if (typeof YEAR_SUMMARY === 'undefined') return;
  const labs = YEAR_SUMMARY.labs;
  const monthsShort = YEAR_SUMMARY.monthsShort;
  const monthNums = Array.from({length: 12}, (_, i) => i + 1);
  const monthLabels = monthNums.map(m => monthsShort[m]);

  // Same per-lab colours as dashboard.js; retired labs get neutral greys.
  const LAB_COLOR = {
    1: '#0b3d91', 2: '#5b7fb5', 3: '#8a9bb0', 4: '#3f6e6a', 9: '#4a5a78',
    10: '#9c8457', 12: '#6f8f86', 13: '#a7b4c6', 14: '#7d6f8f',
  };
  const labColor = l => LAB_COLOR[l.id] || '#c3c9d3';

  // Yearly totals bar
  new Chart(document.getElementById('yearByLab'), {
    type: 'bar',
    data: {
      labels: labs.map(l => l.code),
      datasets: [{
        label: 'Durasi (jam) — total tahun',
        data: labs.map(l => Number(l.drs_total.toFixed(1))),
        backgroundColor: '#0b3d91',
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { title: items => labs[items[0].dataIndex].name } },
      },
      scales: { y: { beginAtZero: true } },
    },
  });

  // JP distribution donut
  const jpData = labs.map(l => l.jp_total);
  new Chart(document.getElementById('yearShare'), {
    type: 'doughnut',
    data: {
      labels: labs.map(l => l.code),
      datasets: [{
        data: jpData,
        backgroundColor: labs.map(labColor),
      }],
    },
    options: {
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const total = jpData.reduce((a,b)=>a+b,0) || 1;
              const pct = (ctx.parsed / total * 100).toFixed(1);
              return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
            },
          },
        },
      },
    },
  });

  // Monthly stacked bar (durasi per month stacked by lab)
  const stackedDatasets = labs.map((l, i) => ({
    label: l.code,
    data: monthNums.map(m => l.months[m] ? l.months[m].drs : 0),
    backgroundColor: labColor(l),
    stack: 'durasi',
  }));
  new Chart(document.getElementById('yearMonthly'), {
    type: 'bar',
    data: { labels: monthLabels, datasets: stackedDatasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
      },
      scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
    },
  });

  // Monthly trend line per lab
  const trendDatasets = labs.map((l, i) => ({
    label: l.code,
    data: monthNums.map(m => l.months[m] ? l.months[m].drs : 0),
    borderColor: labColor(l),
    backgroundColor: labColor(l) + '33',
    tension: 0.2,
    pointRadius: 3,
    fill: false,
    hidden: l.drs_total === 0,
  }));
  new Chart(document.getElementById('yearTrend'), {
    type: 'line',
    data: { labels: monthLabels, datasets: trendDatasets },
    options: {
      responsive: true,
      interaction: { mode: 'nearest', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
      },
      scales: { y: { beginAtZero: true } },
    },
  });

  // Year table: clickable cells navigate to monthly view
  document.querySelectorAll('#yearTable td[data-lab-id][data-month]').forEach(td => {
    td.addEventListener('click', () => {
      const y = td.dataset.year;
      const m = td.dataset.month;
      window.location.href = window.SPP_MONTH_PATH
        ? window.SPP_MONTH_PATH(y, m)
        : `/?year=${y}&month=${m}`;
    });
  });

  // Static-mode year picker
  const yearPicker = document.getElementById('yearPicker');
  if (yearPicker) {
    yearPicker.addEventListener('change', () => {
      const y = yearPicker.value;
      if (/^\d{4}$/.test(y)) location.href = `/year-${y}.html`;
    });
  }
})();
