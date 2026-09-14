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

  /* ── Status Badge ──────────────────────────────────────────────────── */
  const STATUS = {
    idle: ['Waiting for a document', 'bg-gray-400', 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'],
    running: ['Extracting', 'bg-blue-500 animate-pulse', 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'],
    done: ['Completed', 'bg-green-500', 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'],
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

  function clearSelectedFileThumb() {
    if (selectedFileThumbUrl) {
      URL.revokeObjectURL(selectedFileThumbUrl);
      selectedFileThumbUrl = null;
    }
  }

  function chipMeta() {
    if (!selectedFile) return '-';
    const isPdf = selectedFile.type === 'application/pdf';
    const base = `${formatBytes(selectedFile.size)} · ${isPdf ? 'PDF' : selectedFile.type.replace('image/', '').toUpperCase()}`;
    const applied = window.AthenaCropper ? window.AthenaCropper.applied : null;
    return applied ? `${base} · cropped to ${applied.width}×${applied.height}` : base;
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

    const applied = window.AthenaCropper ? window.AthenaCropper.applied : null;
    $('btn-crop').textContent = applied ? 'Adjust crop' : 'Crop document';

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

  function setFile(file) {
    if (!file) return;
    if (!OK_TYPES.includes(file.type)) {
      showError('That file type is not supported. Use a PDF, PNG or JPG.');
      return;
    }
    if (file.size > MAX_BYTES) {
      showError('That file is over the 10 MB limit. Try a smaller one.');
      return;
    }
    showError('');
    clearSelectedFileThumb();
    selectedFile = file;
    if (window.AthenaCropper) window.AthenaCropper.reset();
    refreshChip();
    $('file-chip').classList.replace('hidden', 'flex');

    if (file.type.startsWith('image/') && window.AthenaCropper) {
      window.AthenaCropper.open(file);
    }
  }

  function initDropzone() {
    const dz = $('dropzone');
    $('doc-file').addEventListener('change', (e) => setFile(e.target.files[0]));

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

    dz.addEventListener('drop', (e) => setFile(e.dataTransfer.files[0]));

    $('file-remove').addEventListener('click', () => {
      clearSelectedFileThumb();
      selectedFile = null;
      if (window.AthenaCropper) window.AthenaCropper.reset();
      $('doc-file').value = '';
      $('file-chip').classList.replace('flex', 'hidden');
    });

    $('btn-crop').addEventListener('click', () => {
      if (selectedFile && selectedFile.type.startsWith('image/') && window.AthenaCropper) {
        window.AthenaCropper.open(selectedFile);
      }
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
      $('trace-empty').classList.remove('hidden');
      $('trace-wrap').classList.add('hidden');
      return;
    }

    const stages = Array.isArray(traceObj.stages) ? traceObj.stages : [];
    if (!stages.length) {
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

  /* ── Execution Orchestration ───────────────────────────────────────── */
  async function runExtraction() {
    if (running) return;
    if (!selectedFile) {
      showError('Please select or drop a document file first.');
      $('dropzone').scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }

    running = true;
    $('btn-extract').disabled = true;
    $('btn-spinner').classList.remove('hidden');
    $('btn-label').textContent = 'Extracting…';
    $('copy-json').disabled = true;
    $('download-json').disabled = true;
    $('copy-id').disabled = true;

    const docType = $('doc-type').value;
    const withTrace = $('opt-trace').checked;

    setStatus('running');
    $('live-region').textContent = 'Extraction started.';

    // Prepare upload payload (use cropped blob if crop applied)
    let uploadBlob = selectedFile;
    let uploadFilename = selectedFile.name;
    if (selectedFile.type.startsWith('image/') && window.AthenaCropper && window.AthenaCropper.applied) {
      const croppedBlob = await window.AthenaCropper.getBlob(0.95);
      if (croppedBlob) {
        uploadBlob = croppedBlob;
        uploadFilename = `cropped_${selectedFile.name.replace(/\.[^/.]+$/, '.jpg')}`;
      }
    }

    // Reset panes
    $('json-output').classList.add('hidden');
    $('json-empty').classList.remove('hidden');
    $('trace-list').innerHTML = '';
    $('tab-trace').parentElement.classList.toggle('hidden', !withTrace);

    if (withTrace) {
      $('trace-empty').classList.add('hidden');
      $('trace-wrap').classList.remove('hidden');
      $('trace-count').classList.remove('hidden');
      $('trace-count').textContent = '0';
      selectTab(1);
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
      const result = await window.AthenaAPI.extractDocument({
        documentType: docType,
        fileBlob: uploadBlob,
        filename: uploadFilename,
        trace: withTrace
      });

      clearInterval(ticker);
      const totalMs = Math.round(performance.now() - started);
      $('latency').textContent = `${totalMs} ms`;

      const payload = result.data || {};
      currentReqId = payload.request_id || '-';
      $('request-id').textContent = formatShortId(currentReqId);
      $('request-id').title = currentReqId !== '-' ? `Full Request ID: ${currentReqId}` : '';

      currentJson = payload.data || payload;

      if (result.ok) {
        setStatus('done');
        $('pages').textContent = payload.pages ? String(payload.pages) : '1';
        $('live-region').textContent = `Extraction completed successfully in ${totalMs} ms.`;
      } else {
        setStatus('failed');
        $('live-region').textContent = `Extraction failed: ${payload.detail || payload.error || 'Unknown error'}`;
      }

      $('json-output').innerHTML = highlightJson(payload);
      $('json-output').classList.remove('hidden');
      $('json-empty').classList.add('hidden');

      if (withTrace && payload.trace) {
        renderTrace(payload.trace);
      } else if (withTrace && !payload.trace) {
        $('trace-empty').classList.remove('hidden');
        $('trace-wrap').classList.add('hidden');
      }

      $('copy-json').disabled = false;
      $('download-json').disabled = false;
      $('copy-id').disabled = !payload.request_id;
      if (!withTrace || result.ok) selectTab(0);
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
      $('btn-spinner').classList.add('hidden');
      $('btn-label').textContent = 'Run extraction';
      running = false;
    }
  }

  /* ── Document Type Select Population ───────────────────────────────── */
  async function loadDocumentTypes() {
    const select = $('doc-type');
    const descEl = $('doc-type-desc');
    try {
      registeredDocs = await window.AthenaAPI.fetchDocumentTypes();
      select.innerHTML = '';

      registeredDocs.forEach((doc, idx) => {
        const opt = document.createElement('option');
        opt.value = doc.slug;
        opt.textContent = doc.name || doc.slug;
        if (idx === 0) opt.selected = true;
        select.appendChild(opt);
      });

      const updateDesc = () => {
        const found = registeredDocs.find((d) => d.slug === select.value);
        if (found && found.description && descEl) {
          descEl.textContent = found.description;
        }
      };

      select.addEventListener('change', updateDesc);
      updateDesc();
    } catch (err) {
      console.error('Failed to load document types:', err);
    }
  }

  /* ── Backend Health Monitor ────────────────────────────────────────── */
  async function loadHealth() {
    const engineDesc = $('engine-desc');

    const health = await window.AthenaAPI.checkHealth();
    if (health && health.status === 'healthy') {
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
      a.download = `extraction-${currentReqId || 'result'}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      showToast('JSON file downloaded');
    });

    $('btn-reset').addEventListener('click', () => {
      clearSelectedFileThumb();
      selectedFile = null;
      currentJson = null;
      currentReqId = null;
      if (window.AthenaCropper) window.AthenaCropper.reset();
      $('doc-file').value = '';
      $('file-chip').classList.replace('flex', 'hidden');
      showError('');
      $('request-id').textContent = '-';
      $('latency').textContent = '-';
      $('pages').textContent = '-';
      $('json-output').classList.add('hidden');
      $('json-empty').classList.remove('hidden');
      $('trace-wrap').classList.add('hidden');
      $('trace-empty').classList.remove('hidden');
      $('trace-list').innerHTML = '';
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
          if (error) showError(error);
          else {
            refreshChip();
            if (appliedCrop) showToast(`Crop applied: ${appliedCrop.width} × ${appliedCrop.height}`);
          }
        },
        toast: showToast
      });
    }

    loadDocumentTypes();
    loadHealth();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
