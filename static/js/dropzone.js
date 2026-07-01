// Reusable drag-and-drop wrapper for an existing <input type="file"> element.
// Usage: SPPDropzone.enable(zoneEl, fileInputEl);
// The zone element gets `.is-dragover` while a file is being dragged over it.
// On drop, the file is assigned to the input and a `change` event is fired so
// existing validation/preview logic keeps working unchanged.
window.SPPDropzone = (function () {
  function isFileDrag(e) {
    if (!e.dataTransfer) return false;
    const types = e.dataTransfer.types;
    if (!types) return false;
    for (let i = 0; i < types.length; i++) {
      if (types[i] === 'Files') return true;
    }
    return false;
  }

  function enable(zone, input) {
    if (!zone || !input) return;
    if (zone.dataset.dropzoneReady === '1') return;
    zone.dataset.dropzoneReady = '1';

    ['dragenter', 'dragover'].forEach(ev => {
      zone.addEventListener(ev, (e) => {
        if (!isFileDrag(e)) return;
        e.preventDefault();
        e.stopPropagation();
        zone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'dragend'].forEach(ev => {
      zone.addEventListener(ev, (e) => {
        if (e.target !== zone && !zone.contains(e.target)) return;
        zone.classList.remove('is-dragover');
      });
    });

    zone.addEventListener('drop', (e) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove('is-dragover');
      const files = e.dataTransfer.files;
      if (!files || !files.length) return;

      // Honor `multiple` and the `accept` filter — silently drop mismatches.
      const allowMultiple = input.multiple;
      const accept = (input.accept || '').toLowerCase();
      const acceptList = accept
        ? accept.split(',').map(s => s.trim()).filter(Boolean)
        : [];

      function matches(file) {
        if (!acceptList.length) return true;
        const name = (file.name || '').toLowerCase();
        const type = (file.type || '').toLowerCase();
        for (const rule of acceptList) {
          if (rule.startsWith('.') && name.endsWith(rule)) return true;
          if (rule.endsWith('/*') && type.startsWith(rule.slice(0, -1))) return true;
          if (rule === type) return true;
        }
        return false;
      }

      const dt = new DataTransfer();
      const limit = allowMultiple ? files.length : 1;
      for (let i = 0; i < files.length && dt.items.length < limit; i++) {
        if (matches(files[i])) dt.items.add(files[i]);
      }
      if (!dt.items.length) {
        zone.classList.add('is-reject');
        setTimeout(() => zone.classList.remove('is-reject'), 800);
        return;
      }
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    // Clicking anywhere inside the dropzone (outside the input itself) opens
    // the picker — makes the whole area feel clickable, not just the button.
    zone.addEventListener('click', (e) => {
      if (e.target === input) return;
      if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') return;
      input.click();
    });
  }

  return { enable };
})();
