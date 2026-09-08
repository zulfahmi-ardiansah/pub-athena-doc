/**
 * cropper.js - Four-corner quad and rectangle document cropper with perspective homography correction.
 */
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);

  const CORNER_LABELS = ['Top-left corner', 'Top-right corner', 'Bottom-right corner', 'Bottom-left corner'];
  const EDGE_LABELS = ['Top edge', 'Right edge', 'Bottom edge', 'Left edge'];

  let modal, stage, canvas, ctx;
  let img = null;
  let corners = [];
  let mode = 'quad';
  let aspect = null;
  let scale = 1, vw = 0, vh = 0, rotation = 0;
  let active = -1, dragPrev = null, lastFocus = null;
  const handles = [];

  let onCropChangedCallback = null;

  const state = {
    applied: null,
    source: null,
    init,
    open,
    close,
    getBlob,
    reset
  };

  /* Geometry helpers */
  const clampPt = (p) => ({
    x: Math.min(Math.max(p.x, 0), img.width),
    y: Math.min(Math.max(p.y, 0), img.height)
  });
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const mid = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
  const toView = (p) => ({ x: p.x * scale, y: p.y * scale });
  const fullQuad = () => [
    { x: 0, y: 0 },
    { x: img.width, y: 0 },
    { x: img.width, y: img.height },
    { x: 0, y: img.height }
  ];
  const insetQuad = (r = 0.06) => {
    const dx = img.width * r, dy = img.height * r;
    return [
      { x: dx, y: dy },
      { x: img.width - dx, y: dy },
      { x: img.width - dx, y: img.height - dy },
      { x: dx, y: img.height - dy }
    ];
  };
  const setRect = (x0, y0, x1, y1) => {
    corners = [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }];
  };
  const outSize = () => {
    const w = Math.max(dist(corners[0], corners[1]), dist(corners[3], corners[2]));
    const h = Math.max(dist(corners[0], corners[3]), dist(corners[1], corners[2]));
    const k = Math.min(1, 2400 / Math.max(w, h, 1));
    return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)) };
  };
  const isFullFrame = () => corners.every((p, i) => dist(p, fullQuad()[i]) < 2);

  /* Build draggable handles */
  function buildHandles() {
    if (handles.length) return;
    for (let i = 0; i < 8; i++) {
      const isCorner = i < 4;
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.index = i;
      b.setAttribute('aria-label', isCorner ? CORNER_LABELS[i] : EDGE_LABELS[i - 4]);
      b.className = 'absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md focus:outline-none focus:ring-4 focus:ring-blue-300 dark:focus:ring-blue-800 ' +
        (isCorner ? 'h-6 w-6 bg-blue-600 cursor-grab' : 'h-4 w-4 bg-blue-500 cursor-move');
      b.addEventListener('keydown', onHandleKey);
      stage.appendChild(b);
      handles.push(b);
    }
  }

  function onHandleKey(e) {
    const keys = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    if (!keys[e.key]) return;
    e.preventDefault();
    const step = (e.shiftKey ? 10 : 1) / scale;
    const [dx, dy] = keys[e.key];
    moveHandle(Number(e.currentTarget.dataset.index), { x: dx * step, y: dy * step }, true);
    render();
  }

  /* Handle moving */
  function moveHandle(i, delta, isDelta, absPoint) {
    if (mode === 'rect') return moveRect(i, delta, absPoint);
    if (i < 4) {
      corners[i] = clampPt(absPoint && !isDelta ? absPoint : { x: corners[i].x + delta.x, y: corners[i].y + delta.y });
    } else {
      const a = i - 4, b = (a + 1) % 4;
      const d = isDelta ? delta : { x: 0, y: 0 };
      const na = clampPt({ x: corners[a].x + d.x, y: corners[a].y + d.y });
      const nb = clampPt({ x: corners[b].x + d.x, y: corners[b].y + d.y });
      corners[a] = na;
      corners[b] = nb;
    }
  }

  function moveRect(i, delta, absPoint) {
    let x0 = corners[0].x, y0 = corners[0].y, x1 = corners[2].x, y1 = corners[2].y;
    if (i < 4) {
      const p = clampPt(absPoint || { x: corners[i].x + delta.x, y: corners[i].y + delta.y });
      if (i === 0) { x0 = p.x; y0 = p.y; }
      if (i === 1) { x1 = p.x; y0 = p.y; }
      if (i === 2) { x1 = p.x; y1 = p.y; }
      if (i === 3) { x0 = p.x; y1 = p.y; }
      if (aspect) {
        const w = Math.abs(x1 - x0);
        const h = w / aspect;
        if (i === 0 || i === 1) y0 = y1 - h; else y1 = y0 + h;
      }
    } else {
      const a = i - 4;
      if (a === 0) y0 += delta.y;
      if (a === 1) x1 += delta.x;
      if (a === 2) y1 += delta.y;
      if (a === 3) x0 += delta.x;
      if (aspect) {
        if (a === 0 || a === 2) {
          const w = Math.abs(y1 - y0) * aspect, cx = (x0 + x1) / 2;
          x0 = cx - w / 2; x1 = cx + w / 2;
        } else {
          const h = Math.abs(x1 - x0) / aspect, cy = (y0 + y1) / 2;
          y0 = cy - h / 2; y1 = cy + h / 2;
        }
      }
    }
    const min = 24;
    x0 = Math.min(Math.max(x0, 0), img.width); x1 = Math.min(Math.max(x1, 0), img.width);
    y0 = Math.min(Math.max(y0, 0), img.height); y1 = Math.min(Math.max(y1, 0), img.height);
    if (Math.abs(x1 - x0) < min || Math.abs(y1 - y0) < min) return;
    setRect(Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1));
  }

  /* Rendering */
  function render() {
    if (!img) return;
    const availW = Math.max(240, (stage.parentElement.clientWidth || 640) - 32);
    const availH = Math.min(window.innerHeight * 0.52, 520);
    scale = Math.min(availW / img.width, availH / img.height);
    vw = Math.round(img.width * scale);
    vh = Math.round(img.height * scale);

    const dpr = window.devicePixelRatio || 1;
    canvas.width = vw * dpr; canvas.height = vh * dpr;
    canvas.style.width = vw + 'px'; canvas.style.height = vh + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, vw, vh);
    ctx.drawImage(img, 0, 0, vw, vh);

    const v = corners.map(toView);

    // Dim outside selection
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, vw, vh);
    ctx.moveTo(v[0].x, v[0].y);
    for (let i = 1; i < 4; i++) ctx.lineTo(v[i].x, v[i].y);
    ctx.closePath();
    ctx.fillStyle = 'rgba(17, 24, 39, 0.55)';
    ctx.fill('evenodd');
    ctx.restore();

    // Rule of thirds while adjusting
    if (active > -1) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
      ctx.lineWidth = 1;
      for (const t of [1 / 3, 2 / 3]) {
        const a = { x: v[0].x + (v[1].x - v[0].x) * t, y: v[0].y + (v[1].y - v[0].y) * t };
        const b = { x: v[3].x + (v[2].x - v[3].x) * t, y: v[3].y + (v[2].y - v[3].y) * t };
        const c = { x: v[0].x + (v[3].x - v[0].x) * t, y: v[0].y + (v[3].y - v[0].y) * t };
        const d = { x: v[1].x + (v[2].x - v[1].x) * t, y: v[1].y + (v[2].y - v[1].y) * t };
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.stroke();
      }
    }

    // Outline
    ctx.beginPath();
    ctx.moveTo(v[0].x, v[0].y);
    for (let i = 1; i < 4; i++) ctx.lineTo(v[i].x, v[i].y);
    ctx.closePath();
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Magnifier while dragging corner
    if (active > -1 && active < 4) drawLoupe(v[active]);

    // Place handles
    const pts = [...v, mid(v[0], v[1]), mid(v[1], v[2]), mid(v[2], v[3]), mid(v[3], v[0])];
    handles.forEach((h, i) => {
      h.style.left = pts[i].x + 'px';
      h.style.top = pts[i].y + 'px';
    });

    const s = outSize();
    $('crop-size').textContent = `${s.w} × ${s.h} px`;
  }

  function drawLoupe(p) {
    const R = 54, ZOOM = 3;
    const cx = p.x < vw / 2 ? vw - R - 12 : R + 12;
    const cy = p.y < vh / 2 ? vh - R - 12 : R + 12;
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.closePath();
    ctx.fillStyle = '#fff'; ctx.fill(); ctx.clip();
    const srcR = R / (scale * ZOOM);
    const sx = p.x / scale - srcR, sy = p.y / scale - srcR;
    ctx.drawImage(img, sx, sy, srcR * 2, srcR * 2, cx - R, cy - R, R * 2, R * 2);
    ctx.strokeStyle = '#2563eb'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(cx - 10, cy); ctx.lineTo(cx + 10, cy); ctx.moveTo(cx, cy - 10); ctx.lineTo(cx, cy + 10); ctx.stroke();
    ctx.restore();
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
  }

  /* Automatic edge finding via Otsu */
  function detectEdges() {
    const N = 220;
    const k = Math.min(N / img.width, N / img.height, 1);
    const w = Math.max(2, Math.round(img.width * k)), h = Math.max(2, Math.round(img.height * k));
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const cc = c.getContext('2d', { willReadFrequently: true });
    cc.drawImage(img, 0, 0, w, h);
    const d = cc.getImageData(0, 0, w, h).data;

    const lum = new Uint8Array(w * h), hist = new Array(256).fill(0);
    for (let i = 0; i < w * h; i++) {
      const v = (0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]) | 0;
      lum[i] = v; hist[v]++;
    }

    let sum = 0; for (let t = 0; t < 256; t++) sum += t * hist[t];
    let sumB = 0, wB = 0, best = 0, thr = 128;
    for (let t = 0; t < 256; t++) {
      wB += hist[t]; if (!wB) continue;
      const wF = w * h - wB; if (!wF) break;
      sumB += t * hist[t];
      const between = wB * wF * Math.pow(sumB / wB - (sum - sumB) / wF, 2);
      if (between > best) { best = between; thr = t; }
    }
    const centreBright = lum[(h >> 1) * w + (w >> 1)] > thr;
    const inDoc = (i) => (lum[i] > thr) === centreBright;

    let tl = null, tr = null, br = null, bl = null, count = 0;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (!inDoc(y * w + x)) continue;
        count++;
        const s = x + y, dxy = x - y;
        if (!tl || s < tl.s) tl = { x, y, s };
        if (!br || s > br.s) br = { x, y, s };
        if (!tr || dxy > tr.d) tr = { x, y, d: dxy };
        if (!bl || dxy < bl.d) bl = { x, y, d: dxy };
      }
    }
    if (count < w * h * 0.12 || !tl) { corners = insetQuad(); return false; }
    corners = [tl, tr, br, bl].map((p) => clampPt({ x: p.x / k, y: p.y / k }));
    if (mode === 'rect') switchMode('rect', true);
    return true;
  }

  /* Perspective warp calculation */
  function homography(src) {
    const { w, h } = outSize();
    const dst = [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }];
    const A = [], b = [];
    for (let i = 0; i < 4; i++) {
      const { x: u, y: v } = dst[i], { x, y } = src[i];
      A.push([u, v, 1, 0, 0, 0, -u * x, -v * x]); b.push(x);
      A.push([0, 0, 0, u, v, 1, -u * y, -v * y]); b.push(y);
    }
    for (let i = 0; i < 8; i++) {
      let p = i;
      for (let r = i + 1; r < 8; r++) if (Math.abs(A[r][i]) > Math.abs(A[p][i])) p = r;
      [A[i], A[p]] = [A[p], A[i]]; [b[i], b[p]] = [b[p], b[i]];
      const piv = A[i][i] || 1e-9;
      for (let r = 0; r < 8; r++) {
        if (r === i) continue;
        const f = A[r][i] / piv;
        for (let cIdx = i; cIdx < 8; cIdx++) A[r][cIdx] -= f * A[i][cIdx];
        b[r] -= f * b[i];
      }
    }
    return { m: b.map((val, i) => val / (A[i][i] || 1e-9)), w, h };
  }

  function warp() {
    const { m, w, h } = homography(corners);
    const [a, bb, c, dd, e, f, g, hh] = m;
    const sctx = img.getContext('2d', { willReadFrequently: true });
    const src = sctx.getImageData(0, 0, img.width, img.height);
    const sd = src.data, sw = img.width, sh = img.height;

    const out = document.createElement('canvas');
    out.width = w; out.height = h;
    const octx = out.getContext('2d');
    const odata = octx.createImageData(w, h), od = odata.data;

    for (let v = 0; v < h; v++) {
      for (let u = 0; u < w; u++) {
        const den = g * u + hh * v + 1;
        const x = (a * u + bb * v + c) / den, y = (dd * u + e * v + f) / den;
        const o = (v * w + u) * 4;
        if (x < 0 || y < 0 || x > sw - 1 || y > sh - 1) {
          od[o + 3] = 255; od[o] = od[o + 1] = od[o + 2] = 255;
          continue;
        }
        const x0 = x | 0, y0 = y | 0, fx = x - x0, fy = y - y0;
        const x1 = Math.min(x0 + 1, sw - 1), y1 = Math.min(y0 + 1, sh - 1);
        const i00 = (y0 * sw + x0) * 4, i10 = (y0 * sw + x1) * 4;
        const i01 = (y1 * sw + x0) * 4, i11 = (y1 * sw + x1) * 4;
        for (let ch = 0; ch < 3; ch++) {
          const top = sd[i00 + ch] + (sd[i10 + ch] - sd[i00 + ch]) * fx;
          const bot = sd[i01 + ch] + (sd[i11 + ch] - sd[i01 + ch]) * fx;
          od[o + ch] = top + (bot - top) * fy;
        }
        od[o + 3] = 255;
      }
    }
    octx.putImageData(odata, 0, 0);
    return out;
  }

  function thumbOf(c) {
    const t = document.createElement('canvas'); t.width = 88; t.height = 88;
    const k = Math.max(88 / c.width, 88 / c.height);
    const dw = c.width * k, dh = c.height * k;
    t.getContext('2d').drawImage(c, (88 - dw) / 2, (88 - dh) / 2, dw, dh);
    return t.toDataURL('image/jpeg', 0.7);
  }

  const MODE_ON = ['bg-blue-700', 'text-white', 'border-blue-700', 'dark:bg-blue-600', 'dark:border-blue-600'];
  const MODE_OFF = ['bg-white', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300'];

  function switchMode(next, keepCorners) {
    mode = next;
    $('mode-quad').classList.remove(...MODE_ON, ...MODE_OFF);
    $('mode-rect').classList.remove(...MODE_ON, ...MODE_OFF);
    $('mode-quad').classList.add(...(next === 'quad' ? MODE_ON : MODE_OFF));
    $('mode-rect').classList.add(...(next === 'rect' ? MODE_ON : MODE_OFF));
    $('crop-aspect').classList.toggle('hidden', next !== 'rect');
    if (next === 'rect') {
      const xs = corners.map((p) => p.x), ys = corners.map((p) => p.y);
      setRect(Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys));
      if (aspect) moveRect(2, { x: 0, y: 0 }, corners[2]);
    }
    render();
  }

  function rotateOnce(moveCorners) {
    const r = document.createElement('canvas');
    r.width = img.height; r.height = img.width;
    const rc = r.getContext('2d');
    rc.translate(r.width / 2, r.height / 2); rc.rotate(Math.PI / 2);
    rc.drawImage(img, -img.width / 2, -img.height / 2);
    if (moveCorners) {
      corners = corners.map((p) => ({ x: img.height - p.y, y: p.x }));
      corners.unshift(corners.pop());
    }
    img = r;
  }

  function localPoint(e) {
    const r = canvas.getBoundingClientRect();
    return { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale };
  }

  function close() {
    modal.classList.replace('flex', 'hidden');
    document.body.classList.remove('overflow-hidden');
    if (lastFocus) lastFocus.focus();
  }

  function applyCrop() {
    const out = warp();
    state.applied = {
      canvas: out,
      width: out.width,
      height: out.height,
      thumb: thumbOf(out),
      mode,
      rotation,
      aspect: aspect || 'free',
      corners: corners.map((p) => [Math.round(p.x), Math.round(p.y)]),
      source: { width: img.width, height: img.height }
    };
    close();
    if (onCropChangedCallback) onCropChangedCallback(state.applied);
  }

  function reset() {
    state.applied = null;
    state.source = null;
    img = null;
    corners = [];
    rotation = 0;
  }

  function getBlob(quality = 0.92) {
    return new Promise((resolve) => {
      if (!state.applied || !state.applied.canvas) {
        resolve(null);
        return;
      }
      state.applied.canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality);
    });
  }

  function open(file) {
    lastFocus = document.activeElement;
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      const c = document.createElement('canvas');
      c.width = image.naturalWidth; c.height = image.naturalHeight;
      c.getContext('2d').drawImage(image, 0, 0);
      img = c;
      state.source = { width: c.width, height: c.height };
      URL.revokeObjectURL(url);

      buildHandles();
      rotation = state.applied ? state.applied.rotation : 0;
      corners = fullQuad();
      for (let i = 0; i < rotation; i++) rotateOnce(false);
      if (state.applied) corners = state.applied.corners.map(([x, y]) => ({ x, y }));
      else corners = fullQuad();
      aspect = null;
      $('crop-aspect').value = 'free';
      switchMode(state.applied ? state.applied.mode : 'quad', true);
      if (!state.applied) detectEdges();

      modal.classList.replace('hidden', 'flex');
      document.body.classList.add('overflow-hidden');
      render();
      requestAnimationFrame(render);
      $('crop-apply').focus();
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      if (onCropChangedCallback) onCropChangedCallback(null, 'Image could not be loaded for cropping.');
    };
    image.src = url;
  }

  function init(callbacks = {}) {
    onCropChangedCallback = callbacks.onCropChanged || null;
    modal = $('crop-modal');
    stage = $('crop-stage');
    canvas = $('crop-canvas');
    ctx = canvas.getContext('2d');

    stage.addEventListener('pointerdown', (e) => {
      if (!img) return;
      const p = localPoint(e);
      const pts = [...corners, mid(corners[0], corners[1]), mid(corners[1], corners[2]), mid(corners[2], corners[3]), mid(corners[3], corners[0])];
      let best = -1, bestD = 26 / scale;
      pts.forEach((q, i) => { const d = dist(p, q); if (d < bestD) { bestD = d; best = i; } });
      if (best === -1) return;
      active = best; dragPrev = p;
      stage.setPointerCapture(e.pointerId);
      if (e.target === canvas) e.preventDefault();
      handles[best].focus({ preventScroll: true });
      render();
    });

    stage.addEventListener('pointermove', (e) => {
      if (active === -1) return;
      const p = localPoint(e);
      const delta = { x: p.x - dragPrev.x, y: p.y - dragPrev.y };
      moveHandle(active, delta, active >= 4, active < 4 ? p : null);
      dragPrev = p;
      render();
    });

    const endDrag = () => { if (active === -1) return; active = -1; dragPrev = null; render(); };
    stage.addEventListener('pointerup', endDrag);
    stage.addEventListener('pointercancel', endDrag);

    $('mode-quad').addEventListener('click', () => switchMode('quad'));
    $('mode-rect').addEventListener('click', () => switchMode('rect'));
    $('crop-aspect').addEventListener('change', (e) => {
      aspect = e.target.value === 'free' ? null : Number(e.target.value);
      if (aspect) moveRect(2, { x: 0, y: 0 }, corners[2]);
      render();
    });
    if ($('crop-detect')) {
      $('crop-detect').addEventListener('click', () => {
        const found = detectEdges();
        render();
        if (callbacks.toast) callbacks.toast(found ? 'Edges detected' : 'No clear edges found - adjust manually');
      });
    }
    $('crop-reset').addEventListener('click', () => { corners = fullQuad(); render(); });
    $('crop-rotate').addEventListener('click', () => {
      rotation = (rotation + 1) % 4;
      rotateOnce(true);
      render();
    });

    $('crop-close').addEventListener('click', close);
    $('crop-skip').addEventListener('click', () => {
      state.applied = null;
      if (onCropChangedCallback) onCropChangedCallback(null);
      close();
    });
    modal.addEventListener('mousedown', (e) => { if (e.target === modal) close(); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) close();
    });
    window.addEventListener('resize', () => { if (!modal.classList.contains('hidden')) render(); });

    $('crop-apply').addEventListener('click', () => {
      if (isFullFrame()) {
        state.applied = null;
        if (onCropChangedCallback) onCropChangedCallback(null);
        close();
        return;
      }
      const btn = $('crop-apply');
      btn.disabled = true; btn.textContent = 'Straightening…';
      requestAnimationFrame(() => setTimeout(() => {
        applyCrop();
        btn.disabled = false; btn.textContent = 'Apply crop';
      }, 0));
    });
  }

  window.AthenaCropper = state;
})();
