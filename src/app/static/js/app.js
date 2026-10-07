/**
 * app.js - Main UI controller for Athena Document Extractor.
 */
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);

  /* ── State ─────────────────────────────────────────────────────────── */
  const MAX_BYTES = 10 * 1024 * 1024; // 10 MB
  const OK_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];

  let selectedFile = null;
  let selectedFiles = [];
  let activeCropEntry = null;
  let maxBatchFiles = 5;
  let currentJson = null;
  let currentReqId = null;
  let running = false;
  let registeredDocs = [];

  /* ── Toast Utility ─────────────────────────────────────────────────── */
  let toastTimer;
  function showToast(msg) {
    const el = $('toast');
    if (!el) return;
    $('toast-text').textContent = msg;
    el.classList.replace('hidden', 'flex');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.replace('flex', 'hidden'), 2600);
  }

  /* ── Theme Switcher ────────────────────────────────────────────────── */
  function initTheme() {
    const root = document.documentElement;
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    const syncThemeIcons = () => {
      const dark = root.classList.contains('dark');
      $('icon-sun').classList.toggle('hidden', !dark);
      $('icon-moon').classList.toggle('hidden', dark);
    };

    syncThemeIcons();

    $('theme-toggle').addEventListener('click', () => {
      const isDark = root.classList.toggle('dark');
      localStorage.theme = isDark ? 'dark' : 'light';
      syncThemeIcons();
    });
  }

  /* ── Tabs Management ───────────────────────────────────────────────── */
  const tabs = [];
  const ACTIVE_TAB = ['border-blue-700', 'text-blue-700', 'dark:border-blue-500', 'dark:text-blue-500'];
  const IDLE_TAB = ['border-transparent', 'text-gray-500', 'dark:text-gray-400'];

  function initTabs() {
    tabs.push(
      { btn: $('tab-json'), pane: $('pane-json') },
      { btn: $('tab-trace'), pane: $('pane-trace') }
    );

    tabs.forEach((t, i) => {
      t.btn.addEventListener('click', () => selectTab(i));
      t.btn.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        const next = (i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
        selectTab(next);
        tabs[next].btn.focus();
      });
    });

    selectTab(0);
  }

  function selectTab(i) {
    tabs.forEach((t, idx) => {
      const on = idx === i;
      t.pane.classList.toggle('hidden', !on);
      t.btn.setAttribute('aria-selected', String(on));
      t.btn.tabIndex = on ? 0 : -1;
      t.btn.classList.remove(...ACTIVE_TAB, ...IDLE_TAB);
      t.btn.classList.add(...(on ? ACTIVE_TAB : IDLE_TAB));
    });
  }

  /* ── JSON Syntax Highlighting ──────────────────────────────────────── */
  function highlightJson(obj) {
    if (typeof obj === 'string') {
      try {
        obj = JSON.parse(obj);
      } catch {
        return escapeHtml(obj);
      }
    }
    const json = JSON.stringify(obj, null, 2)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    return json.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (m) => {
        let cls = 'tok-num';
        if (/^"/.test(m)) cls = /:$/.test(m) ? 'tok-key' : 'tok-str';
        else if (/true|false/.test(m)) cls = 'tok-bool';
        else if (/null/.test(m)) cls = 'tok-null';
        return `<span class="${cls}">${m}</span>`;
      }
    );
  }

  function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
  }

  function toTitleCase(str) {
    if (!str) return '';
    const acronyms = {
      ocr: 'OCR',
      llm: 'LLM',
      pdf: 'PDF',
      ktp: 'KTP',
      npwp: 'NPWP',
      id: 'ID',
      json: 'JSON',
      api: 'API',
      ui: 'UI',
      dpi: 'DPI',
      rgb: 'RGB',
      cv: 'CV',
      ai: 'AI',
      cpu: 'CPU',
      gpu: 'GPU'
    };

    return String(str)
      .replace(/[_-]+/g, ' ')
      .trim()
      .split(/\s+/)
      .map((word) => {
        const lower = word.toLowerCase();
        if (acronyms[lower]) return acronyms[lower];
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
      })
      .join(' ');
  }

  function formatShortId(idStr) {
    if (!idStr || idStr === '-') return '-';
    if (typeof idStr === 'string' && idStr.includes('-')) {
      const parts = idStr.split('-');
      return parts[parts.length - 1];
    }
    return typeof idStr === 'string' && idStr.length > 12 ? idStr.slice(-12) : idStr;
  }

  function setCost(cost) {
    const el = $('total-cost');
    if (!cost) {
      el.textContent = 'Unavailable';
      el.title = 'No cost estimate was returned.';
      return;
    }

    const complete = cost.complete === true;
    const amount = complete ? cost.estimate_cost : cost.known_cost;
    const value = Number(amount);
    if (amount == null || !Number.isFinite(value) || value < 0 || (!complete && value === 0)) {
      el.textContent = 'Unavailable';
      el.title = 'Some usage or pricing information is unavailable.';
      return;
    }

    const currency = cost.currency === 'USD' ? '$' : `${cost.currency || 'USD'} `;
    el.textContent = `${complete ? '' : '≥'}${currency}${value === 0 ? '0.00' : amount}`;
    el.title = complete ? 'Estimated request cost.' : 'Known cost only; the total could be higher.';
  }

  /* ── Status Badge ──────────────────────────────────────────────────── */
  const STATUS = {
    idle: ['Waiting for a document', 'bg-gray-400', 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'],
    running: ['Extracting', 'bg-blue-500 animate-pulse', 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'],
    done: ['Completed', 'bg-green-500', 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'],
    partial: ['Partially completed', 'bg-amber-500', 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300'],
    failed: ['Failed', 'bg-red-500', 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300']
  };

  function setStatus(key) {
    const [text, dot, badge] = STATUS[key] || STATUS.idle;
    $('status-text').textContent = text;
    $('status-dot').className = `h-1.5 w-1.5 rounded-full ${dot}`;
    $('status-badge').className = `mt-1 inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium ${badge}`;
  }

  /* ── File Management & Dropzone ─────────────────────────────────────── */
  const formatBytes = (n) =>
    n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1048576).toFixed(1)} MB`;

  function showError(msg) {
    const el = $('file-error');
    el.textContent = msg;
    el.classList.toggle('hidden', !msg);
    $('dropzone').classList.toggle('border-red-400', Boolean(msg));
    $('dropzone').classList.toggle('dark:border-red-500', Boolean(msg));
  }

  let selectedFileThumbUrl = null;
  let batchThumbUrls = [];

  function clearSelectedFileThumb() {
    if (selectedFileThumbUrl) {
      URL.revokeObjectURL(selectedFileThumbUrl);
      selectedFileThumbUrl = null;
    }
  }

  function clearBatchThumbnails() {
    batchThumbUrls.forEach((url) => URL.revokeObjectURL(url));
    batchThumbUrls = [];
  }

  function chipMeta() {
    if (!selectedFile) return '-';
    const isPdf = selectedFile.type === 'application/pdf';
    const base = `${formatBytes(selectedFile.size)} · ${isPdf ? 'PDF' : selectedFile.type.replace('image/', '').toUpperCase()}`;
    return selectedFiles[0].crop ? `${base} · Cropped` : base;
  }

  function refreshChip() {
    if (!selectedFile) {
      $('file-chip').classList.replace('flex', 'hidden');
      return;
    }

    $('file-name').textContent = selectedFile.name;
    $('file-meta').textContent = chipMeta();
    const isImage = selectedFile.type.startsWith('image/');
    $('btn-crop').classList.toggle('hidden', !isImage);
    $('btn-crop').classList.toggle('inline-flex', isImage);

    const applied = selectedFiles[0].crop;
    $('btn-crop').setAttribute('aria-label', `Crop ${selectedFile.name}`);

    let thumbSrc = null;
    if (applied && applied.thumb) {
      thumbSrc = applied.thumb;
    } else if (isImage) {
      if (!selectedFileThumbUrl) {
        selectedFileThumbUrl = URL.createObjectURL(selectedFile);
      }
      thumbSrc = selectedFileThumbUrl;
    }

    if (thumbSrc) {
      $('file-thumb').src = thumbSrc;
      $('file-thumb').classList.remove('hidden');
      $('file-icon').classList.add('hidden');
    } else {
      $('file-thumb').classList.add('hidden');
      $('file-icon').classList.remove('hidden');
    }
  }

  function openCrop(entry) {
    if (running || !entry || !entry.file.type.startsWith('image/') || !window.AthenaCropper) return;
    activeCropEntry = entry;
    window.AthenaCropper.applied = entry.crop || null;
    window.AthenaCropper.open(entry.file);
  }

  function renderSelectedFiles() {
    const batchList = $('batch-files');
    clearBatchThumbnails();
    batchList.replaceChildren();
    selectedFile = selectedFiles.length === 1 ? selectedFiles[0].file : null;
    $('file-chip').classList.toggle('hidden', !selectedFile);
    $('file-chip').classList.toggle('flex', Boolean(selectedFile));
    batchList.classList.toggle('hidden', selectedFiles.length < 2);
    $('doc-type-field').classList.toggle('hidden', selectedFiles.length > 1);

    if (selectedFile) {
      if (window.AthenaCropper) window.AthenaCropper.applied = selectedFiles[0].crop || null;
      $('doc-type').value = selectedFiles[0].documentType;
      $('doc-type').dispatchEvent(new Event('change'));
      refreshChip();
      return;
    }
    clearSelectedFileThumb();
    selectedFiles.forEach((entry, index) => {
      const row = document.createElement('div');
      row.className = 'flex min-w-0 items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-600 dark:bg-gray-700';
      const preview = document.createElement('span');
      preview.className = 'inline-flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded bg-blue-50 text-blue-700 dark:bg-gray-600 dark:text-blue-300';
      if (entry.file.type.startsWith('image/')) {
        const image = document.createElement('img');
        if (entry.crop && entry.crop.thumb) {
          image.src = entry.crop.thumb;
        } else {
          const url = URL.createObjectURL(entry.file);
          batchThumbUrls.push(url);
          image.src = url;
        }
        image.alt = '';
        image.className = 'h-full w-full object-cover';
        preview.appendChild(image);
      } else {
        preview.innerHTML = '<svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>';
      }
      const details = document.createElement('div');
      details.className = 'min-w-0 flex-1';
      const name = document.createElement('p');
      name.className = 'truncate text-sm font-medium text-gray-900 dark:text-white';
      name.textContent = `${index + 1}. ${entry.file.name}`;
      name.title = entry.file.name;
      const meta = document.createElement('p');
      meta.className = 'mt-1 text-xs text-gray-500 dark:text-gray-400';
      meta.textContent = `${formatBytes(entry.file.size)} · ${entry.file.type === 'application/pdf' ? 'PDF' : entry.file.type.replace('image/', '').toUpperCase()}${entry.crop ? ' · Cropped' : ''}`;
      const select = document.createElement('select');
      select.className = 'mt-2 min-w-0 w-full max-w-full rounded-lg border border-gray-300 bg-gray-50 p-1.5 text-xs text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white';
      select.setAttribute('aria-label', `Document type for ${entry.file.name}`);
      Array.from($('doc-type').options).forEach((option) => {
        select.add(new Option(option.textContent, option.value));
      });
      select.value = entry.documentType;
      select.addEventListener('change', () => { entry.documentType = select.value; });
      if (entry.file.type.startsWith('image/')) {
        const cropButton = document.createElement('button');
        cropButton.type = 'button';
        cropButton.className = 'mt-2 inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-500 dark:text-gray-200 dark:hover:bg-gray-600';
        cropButton.innerHTML = '<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M6 3v12a3 3 0 0 0 3 3h12M3 6h12a3 3 0 0 1 3 3v12"/></svg><span>Crop</span>';
        cropButton.setAttribute('aria-label', `Crop ${entry.file.name}`);
        cropButton.addEventListener('click', () => openCrop(entry));
        details.append(name, meta, select, cropButton);
      } else {
        details.append(name, meta, select);
      }
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'flex h-11 w-8 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-gray-600 dark:hover:text-white';
      remove.innerHTML = '<svg class="h-4 w-4" fill="none" viewBox="0 0 14 14" aria-hidden="true"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"/></svg>';
      remove.setAttribute('aria-label', `Remove ${entry.file.name}`);
      remove.addEventListener('click', () => {
        if (running) return;
        selectedFiles.splice(index, 1);
        renderSelectedFiles();
      });
      row.append(preview, details, remove);
      batchList.appendChild(row);
    });
  }

  function setFiles(files) {
    if (running) return;
    const incoming = Array.from(files || []);
    if (!incoming.length) return;
    if (selectedFiles.length + incoming.length > maxBatchFiles) {
      showError(`Select at most ${maxBatchFiles} files per batch.`);
      return;
    }
    if (incoming.some((file) => !OK_TYPES.includes(file.type) || file.size > MAX_BYTES)) {
      showError('Use PDF, PNG or JPG files up to 10 MB each.');
      return;
    }
    showError('');
    clearSelectedFileThumb();
    if (!selectedFiles.length && window.AthenaCropper) window.AthenaCropper.reset();
    selectedFiles.push(...incoming.map((file) => ({ file, documentType: $('doc-type').value, crop: null })));
    renderSelectedFiles();
    if (selectedFile && selectedFile.type.startsWith('image/') && window.AthenaCropper) {
      openCrop(selectedFiles[0]);
    }
  }

  function initDropzone() {
    const dz = $('dropzone');
    $('doc-file').addEventListener('change', (e) => {
      setFiles(e.target.files);
      e.target.value = '';
    });

    ['dragenter', 'dragover'].forEach((ev) =>
      dz.addEventListener(ev, (e) => {
        e.preventDefault();
        dz.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-gray-600');
      })
    );

    ['dragleave', 'drop'].forEach((ev) =>
      dz.addEventListener(ev, (e) => {
        e.preventDefault();
        dz.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-gray-600');
      })
    );

    dz.addEventListener('drop', (e) => setFiles(e.dataTransfer.files));

    $('file-remove').addEventListener('click', () => {
      if (running) return;
      clearSelectedFileThumb();
      selectedFiles = [];
      selectedFile = null;
      activeCropEntry = null;
      if (window.AthenaCropper) window.AthenaCropper.reset();
      $('doc-file').value = '';
      renderSelectedFiles();
    });

    $('btn-crop').addEventListener('click', () => {
      if (selectedFile) openCrop(selectedFiles[0]);
    });
  }

  /* ── Trace Pipeline Stage Rendering ────────────────────────────────── */
  const TRACE_ICONS = {
    ok: '<svg class="h-3 w-3 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 011.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z" clip-rule="evenodd"/></svg>',
    failed: '<svg class="h-3 w-3 text-red-600 dark:text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>',
    skipped: '<svg class="h-3 w-3 text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path d="M5 10a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1z"/></svg>'
  };

  function renderTrace(traceObj) {
    const list = $('trace-list');
    list.innerHTML = '';

    if (!traceObj) {
      $('trace-count').textContent = '0';
      $('trace-count').classList.add('hidden');
      $('trace-empty').classList.remove('hidden');
      $('trace-wrap').classList.add('hidden');
      return;
    }

    const stages = Array.isArray(traceObj.stages) ? traceObj.stages : [];
    if (!stages.length) {
      $('trace-count').textContent = '0';
      $('trace-count').classList.add('hidden');
      $('trace-empty').classList.remove('hidden');
      $('trace-wrap').classList.add('hidden');
      return;
    }

    $('trace-empty').classList.add('hidden');
    $('trace-wrap').classList.remove('hidden');
    $('trace-count').textContent = String(stages.length);
    $('trace-count').classList.remove('hidden');
    if ($('trace-pipeline-name')) {
      $('trace-pipeline-name').textContent = traceObj.engine ? toTitleCase(traceObj.engine) : 'Athena Pipeline';
    }
    if ($('trace-total-stages')) {
      $('trace-total-stages').textContent = `${stages.length} recorded stage${stages.length > 1 ? 's' : ''}`;
    }

    let slowestStage = null;

    stages.forEach((st, idx) => {
      const isFailed = st.status === 'failed' || (st.details && st.details.error);
      const isSkipped = st.status === 'skipped';
      const iconKey = isFailed ? 'failed' : isSkipped ? 'skipped' : 'ok';
      const duration = st.duration_ms || (st.details && st.details.execution_time_ms) || 0;

      if (!slowestStage || duration > (slowestStage.duration_ms || 0)) {
        slowestStage = { name: st.name, duration_ms: duration };
      }

      const li = document.createElement('li');
      li.className = 'mb-4 ms-6 last:mb-0';

      const iconBg = isFailed
        ? 'bg-red-100 dark:bg-red-900'
        : isSkipped
        ? 'bg-gray-100 dark:bg-gray-700'
        : 'bg-green-100 dark:bg-green-900';

      const stageTitle = toTitleCase(st.name || 'Stage');

      const stageNote = isSkipped
        ? 'Skipped'
        : isFailed
        ? 'Failed during execution'
        : (st.details && st.details.ocr_engine)
        ? `OCR (${toTitleCase(st.details.ocr_engine)})`
        : (st.details && st.details.model)
        ? `LLM (${st.details.model})`
        : 'Completed successfully';

      li.innerHTML = `
        <span class="absolute -start-3 flex h-6 w-6 items-center justify-center rounded-full ring-4 ring-white dark:ring-gray-800 ${iconBg}">
          ${TRACE_ICONS[iconKey]}
        </span>
        <div class="rounded-lg border ${isFailed ? 'border-red-300 dark:border-red-800' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800">
          <button type="button" class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left focus:outline-none focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900" aria-expanded="false">
            <span class="min-w-0">
              <span class="block text-sm font-medium text-gray-900 dark:text-white">${idx + 1}. ${escapeHtml(stageTitle)}</span>
              <span class="mt-0.5 block truncate text-xs text-gray-500 dark:text-gray-400">${escapeHtml(stageNote)}</span>
            </span>
            <span class="flex shrink-0 items-center gap-3">
              <span class="font-mono text-xs text-gray-500 dark:text-gray-400">${duration ? `${duration.toFixed(0)} ms` : '-'}</span>
              <svg class="h-3 w-3 text-gray-400 transition-transform" fill="none" viewBox="0 0 10 6"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 4 4 4-4"/></svg>
            </span>
          </button>
          <div class="step-detail border-t border-gray-200 px-4 py-3 dark:border-gray-700">
            <pre class="scroll-thin json-viewer overflow-auto rounded bg-gray-50 p-3 font-mono text-xs leading-5 dark:bg-gray-900">${highlightJson(st.details || st)}</pre>
          </div>
        </div>`;

      const btn = li.querySelector('button');
      const detail = li.querySelector('.step-detail');
      const chev = li.querySelector('svg');

      btn.addEventListener('click', () => {
        const open = detail.classList.toggle('open');
        btn.setAttribute('aria-expanded', String(open));
        chev.classList.toggle('rotate-180', open);
      });

      list.appendChild(li);
    });

    if (slowestStage && slowestStage.duration_ms) {
      $('trace-slowest').textContent = `${toTitleCase(slowestStage.name)} (${slowestStage.duration_ms.toFixed(0)} ms)`;
    } else if (slowestStage && slowestStage.name) {
      $('trace-slowest').textContent = toTitleCase(slowestStage.name);
    } else {
      $('trace-slowest').textContent = '-';
    }
  }

  function renderBatchResults(payload, withTrace) {
    const list = $('batch-results');
    list.replaceChildren();
    list.classList.remove('hidden');
    list.classList.add('flex');
    const showItem = (item, index) => {
      currentJson = item;
      $('json-output').innerHTML = highlightJson(item);
      if (withTrace) {
        $('trace-empty-title').textContent = index === -1 ? 'Select a file to view its trace' : 'No trace for this file';
        $('trace-empty-detail').textContent = index === -1 ? 'Choose a file above.' : 'This file has no recorded stages.';
        renderTrace(item.trace || null);
      }
      Array.from(list.children).forEach((button) => {
        button.setAttribute('aria-pressed', String(button.dataset.index === String(index)));
      });
      selectTab(0);
    };
    const addButton = (label, item, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.index = String(index);
      button.className = 'rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700';
      button.textContent = label;
      button.setAttribute('aria-pressed', String(index === -1));
      button.addEventListener('click', () => showItem(item, index));
      list.appendChild(button);
    };
    addButton('All files', payload, -1);
    payload.results.forEach((item, index) => {
      addButton(`${index + 1}. ${item.filename}${item.success ? '' : ' · Failed'}`, item, index);
    });
    if (withTrace) {
      $('trace-empty-title').textContent = 'Select a file to view its trace';
      $('trace-empty-detail').textContent = 'Choose a file above.';
      renderTrace(null);
    }
  }

  async function prepareUpload(entry) {
    if (!entry.crop) return { file: entry.file, documentType: entry.documentType };
    const blob = await new Promise((resolve) => entry.crop.canvas.toBlob(resolve, 'image/jpeg', 0.95));
    if (!blob) return { file: entry.file, documentType: entry.documentType };
    return {
      file: entry.file,
      fileBlob: blob,
      filename: `cropped_${entry.file.name.replace(/\.[^/.]+$/, '.jpg')}`,
      documentType: entry.documentType
    };
  }

  /* ── Execution Orchestration ───────────────────────────────────────── */
  async function runExtraction() {
    if (running) return;
    if (!selectedFiles.length) {
      showError('Please select or drop document files first.');
      $('dropzone').scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }

    running = true;
    $('btn-extract').disabled = true;
    $('btn-run-icon').classList.add('hidden');
    $('btn-spinner').classList.remove('hidden');
    $('btn-label').textContent = 'Extracting…';
    $('copy-json').disabled = true;
    $('download-json').disabled = true;
    $('copy-id').disabled = true;
    $('total-cost').textContent = '-';
    $('total-cost').title = '';

    const docType = $('doc-type').value;
    const withTrace = $('opt-trace').checked;
    const batchMode = selectedFiles.length > 1;
    $('pages-label').textContent = batchMode ? 'Files' : 'Pages';
    $('cost-label').textContent = batchMode ? 'Batch estimated cost' : 'Estimated cost';

    setStatus('running');
    $('live-region').textContent = 'Extraction started.';

    // Reset panes
    $('json-output').classList.add('hidden');
    $('json-empty').classList.remove('hidden');
    $('trace-list').innerHTML = '';
    $('trace-empty-title').textContent = 'Nothing to trace yet';
    $('trace-empty-detail').textContent = 'Each pipeline stage and its duration will appear here once an extraction is run.';
    $('batch-results').classList.remove('flex');
    $('batch-results').classList.add('hidden');
    $('tab-trace').parentElement.classList.toggle('hidden', !withTrace);

    if (withTrace) {
      $('trace-empty').classList.add('hidden');
      $('trace-wrap').classList.remove('hidden');
      $('trace-count').classList.remove('hidden');
      $('trace-count').textContent = '0';
      selectTab(batchMode ? 0 : 1);
    } else {
      $('trace-wrap').classList.add('hidden');
      $('trace-empty').classList.remove('hidden');
      selectTab(0);
    }

    const started = performance.now();
    const ticker = setInterval(() => {
      $('latency').textContent = `${Math.round(performance.now() - started)} ms`;
    }, 60);

    try {
      const uploadDocuments = await Promise.all(selectedFiles.map(prepareUpload));
      const result = batchMode
        ? await window.AthenaAPI.extractBatch({ documents: uploadDocuments, trace: withTrace, keepTrace: withTrace })
        : await window.AthenaAPI.extractDocument({
          documentType: docType,
          fileBlob: uploadDocuments[0].fileBlob || uploadDocuments[0].file,
          filename: uploadDocuments[0].filename || uploadDocuments[0].file.name,
          trace: withTrace,
          keepTrace: withTrace
        });

      clearInterval(ticker);
      const totalMs = Math.round(performance.now() - started);
      $('latency').textContent = `${totalMs} ms`;

      const payload = result.data || {};
      const hasBatchResults = batchMode && Array.isArray(payload.results);
      setCost(payload.cost);
      currentReqId = payload.request_id || '-';
      $('request-id').textContent = formatShortId(currentReqId);
      $('request-id').title = currentReqId !== '-' ? `Full Request ID: ${currentReqId}` : '';

      currentJson = batchMode ? payload : (payload.data || payload);

      if (hasBatchResults && payload.succeeded > 0 && payload.failed > 0) {
        setStatus('partial');
        $('pages').textContent = String(payload.total_files);
        $('live-region').textContent = `${payload.succeeded} files completed; ${payload.failed} failed.`;
      } else if (result.ok) {
        setStatus('done');
        $('pages').textContent = batchMode ? String(payload.total_files) : (payload.pages ? String(payload.pages) : '1');
        $('live-region').textContent = batchMode ? `${payload.succeeded} files completed.` : `Extraction completed successfully in ${totalMs} ms.`;
      } else {
        setStatus('failed');
        $('pages').textContent = hasBatchResults ? String(payload.total_files) : '-';
        $('live-region').textContent = hasBatchResults ? `${payload.failed} files failed.` : `Extraction failed: ${payload.detail || payload.error || 'Unknown error'}`;
      }

      $('json-output').innerHTML = highlightJson(payload);
      $('json-output').classList.remove('hidden');
      $('json-empty').classList.add('hidden');

      if (hasBatchResults) {
        renderBatchResults(payload, withTrace);
      } else if (withTrace && payload.trace) {
        renderTrace(payload.trace);
      } else if (withTrace && !payload.trace) {
        $('trace-empty').classList.remove('hidden');
        $('trace-wrap').classList.add('hidden');
      }

      $('copy-json').disabled = false;
      $('download-json').disabled = false;
      $('copy-id').disabled = !payload.request_id;
      if (batchMode || !withTrace || result.ok) selectTab(0);
    } catch (err) {
      clearInterval(ticker);
      const totalMs = Math.round(performance.now() - started);
      $('latency').textContent = `${totalMs} ms`;
      setStatus('failed');

      $('json-output').innerHTML = `<span class="text-red-500 font-mono">${escapeHtml(err.message)}</span>`;
      $('json-output').classList.remove('hidden');
      $('json-empty').classList.add('hidden');
      showToast(`Extraction request failed: ${err.message}`);
    } finally {
      $('btn-extract').disabled = false;
      $('btn-run-icon').classList.remove('hidden');
      $('btn-spinner').classList.add('hidden');
      $('btn-label').textContent = 'Run Extraction';
      running = false;
    }
  }

  /* ── Document Type Select Population ───────────────────────────────── */
  async function loadDocumentTypes() {
    const select = $('doc-type');
    const descEl = $('doc-type-desc');
    try {
      registeredDocs = await window.AthenaAPI.fetchDocumentTypes();
      const selectedType = selectedFiles.length === 1 ? selectedFiles[0].documentType : select.value;
      select.innerHTML = '';

      registeredDocs.forEach((doc, idx) => {
        const opt = document.createElement('option');
        opt.value = doc.slug;
        opt.textContent = doc.name || doc.slug;
        if (idx === 0) opt.selected = true;
        select.appendChild(opt);
      });

      if (registeredDocs.some((doc) => doc.slug === selectedType)) select.value = selectedType;

      const updateDesc = () => {
        const found = registeredDocs.find((d) => d.slug === select.value);
        if (found && found.description && descEl) {
          descEl.textContent = found.description;
        }
      };

      select.addEventListener('change', () => {
        updateDesc();
        if (selectedFiles.length === 1) selectedFiles[0].documentType = select.value;
      });
      updateDesc();
      if (selectedFiles.length) renderSelectedFiles();
    } catch (err) {
      console.error('Failed to load document types:', err);
    }
  }

  /* ── Backend Health Monitor ────────────────────────────────────────── */
  async function loadHealth() {
    const engineDesc = $('engine-desc');

    const health = await window.AthenaAPI.checkHealth();
    if (health && health.status === 'healthy') {
      if (Number.isInteger(health.max_batch_files) && health.max_batch_files > 0) {
        maxBatchFiles = health.max_batch_files;
        $('upload-limit').textContent = `PDF, PNG or JPG · up to 10 MB each · ${maxBatchFiles} files per batch`;
      }
      const engineType = health.active_engine || 'hybrid_engine';
      const engine = toTitleCase(engineType);
      const provider = toTitleCase(
        health.llm_vision_provider || health.llm_text_provider || health.llm_provider || 'local'
      );
      let detail;
      if (engineType === 'visual_engine') {
        detail = provider;
      } else if (engineType === 'string_engine') {
        detail = toTitleCase(health.ocr_backend || 'RapidOCR');
      } else {
        const ocr = toTitleCase(health.ocr_backend || 'RapidOCR');
        detail = `${ocr} + ${provider}`;
      }
      if (engineDesc) {
        engineDesc.textContent = `${engine} (${detail})`;
      }
    } else {
      if (engineDesc) {
        engineDesc.textContent = 'Offline (Cannot connect to Athena API)';
      }
    }
  }

  /* ── Clipboard & Download ──────────────────────────────────────────── */
  async function copyToClipboard(text, successMsg) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    showToast(successMsg);
  }

  function initActions() {
    $('btn-extract').addEventListener('click', runExtraction);

    $('opt-trace').addEventListener('change', (e) => {
      $('tab-trace').parentElement.classList.toggle('hidden', !e.target.checked);
      if (!e.target.checked) selectTab(0);
    });

    $('copy-json').addEventListener('click', () => {
      if (currentJson) {
        copyToClipboard(JSON.stringify(currentJson, null, 2), 'JSON output copied');
      }
    });

    $('copy-id').addEventListener('click', () => {
      if (currentReqId && currentReqId !== '-') {
        copyToClipboard(currentReqId, 'Request ID copied');
      }
    });

    $('download-json').addEventListener('click', () => {
      if (!currentJson) return;
      const blob = new Blob([JSON.stringify(currentJson, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `extraction-${(currentJson && currentJson.request_id) || currentReqId || 'result'}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      showToast('JSON file downloaded');
    });

    $('btn-reset').addEventListener('click', () => {
      if (running) return;
      clearSelectedFileThumb();
      clearBatchThumbnails();
      selectedFiles = [];
      selectedFile = null;
      activeCropEntry = null;
      currentJson = null;
      currentReqId = null;
      if (window.AthenaCropper) window.AthenaCropper.reset();
      $('doc-file').value = '';
      $('file-chip').classList.replace('flex', 'hidden');
      $('batch-files').replaceChildren();
      $('batch-files').classList.add('hidden');
      $('doc-type-field').classList.remove('hidden');
      $('batch-results').replaceChildren();
      $('batch-results').classList.remove('flex');
      $('batch-results').classList.add('hidden');
      $('pages-label').textContent = 'Pages';
      $('cost-label').textContent = 'Estimated cost';
      showError('');
      $('request-id').textContent = '-';
      $('latency').textContent = '-';
      $('pages').textContent = '-';
      $('total-cost').textContent = '-';
      $('total-cost').title = '';
      $('json-output').classList.add('hidden');
      $('json-empty').classList.remove('hidden');
      $('trace-wrap').classList.add('hidden');
      $('trace-empty').classList.remove('hidden');
      $('trace-list').innerHTML = '';
      $('trace-empty-title').textContent = 'Nothing to trace yet';
      $('trace-empty-detail').textContent = 'Each pipeline stage and its duration will appear here once an extraction is run.';
      $('trace-count').classList.add('hidden');
      if ($('trace-slowest')) $('trace-slowest').textContent = '-';
      if ($('trace-total-stages')) $('trace-total-stages').textContent = 'Pipeline execution stages';
      $('copy-json').disabled = true;
      $('download-json').disabled = true;
      $('copy-id').disabled = true;
      setStatus('idle');
      selectTab(0);
    });
  }

  /* ── Bootstrap ─────────────────────────────────────────────────────── */
  function init() {
    initTheme();
    initTabs();
    initDropzone();
    initActions();
    setStatus('idle');

    if (window.AthenaCropper) {
      window.AthenaCropper.init({
        onCropChanged: (appliedCrop, error) => {
          if (error) {
            showError(error);
            return;
          }
          if (!activeCropEntry || !selectedFiles.includes(activeCropEntry)) return;
          activeCropEntry.crop = appliedCrop;
          renderSelectedFiles();
          if (appliedCrop) showToast('Cropped');
        },
        toast: showToast
      });
    }

    loadDocumentTypes();
    loadHealth();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
