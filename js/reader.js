(() => {
  'use strict';
  const reader = document.querySelector('#reader');
  if (!reader) return;
  const blocks = [...reader.querySelectorAll('[id^="p-"]')];
  const indicator = document.querySelector('#reading-progress');
  const resume = document.querySelector('#resume-reading');
  const key = `arnett-reading:${reader.dataset.work}:${reader.dataset.chapter}`;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(key)); } catch (_) { /* Private storage may be unavailable. */ }
  if (reader.dataset.savedParagraph && (!saved || Date.parse(reader.dataset.savedAt) > saved.updated)) {
    saved = { paragraph: reader.dataset.savedParagraph };
  }
  if (saved && /^p-\d+$/.test(saved.paragraph) && document.getElementById(saved.paragraph)) {
    resume.hidden = false;
    resume.addEventListener('click', () => {
      document.getElementById(saved.paragraph).scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      resume.hidden = true;
    });
  }
  let lastSave = 0;
  let touched = false;
  let scheduled = false;
  let position = 0;
  let paragraph = '';
  function measure() {
    scheduled = false;
    const rect = reader.getBoundingClientRect();
    position = Math.max(0, Math.min(1, (innerHeight - rect.top) / Math.max(1, rect.height)));
    const current = [...blocks].reverse().find(block => block.getBoundingClientRect().top <= 150) || blocks[0];
    paragraph = current?.id || '';
    const total = Math.round((Number(reader.dataset.index) + position) / Number(reader.dataset.total) * 100);
    indicator.textContent = `Чтение: ${total}%`;
    if (touched) save(false);
  }
  function save(force) {
    if (!paragraph || !touched) return;
    const now = Date.now();
    if (!force && now - lastSave < 10000) return;
    lastSave = now;
    try { localStorage.setItem(key, JSON.stringify({ paragraph, position, updated: now })); } catch (_) { /* Optional local bookmark. */ }
    if (reader.dataset.saveUrl) {
      fetch(reader.dataset.saveUrl, { method: 'POST', credentials: 'same-origin', keepalive: force,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content },
        body: JSON.stringify({ chapter_id: Number(reader.dataset.chapter), paragraph_id: paragraph, scroll_position: position })
      }).catch(() => { /* The local bookmark still works while offline. */ });
    }
  }
  addEventListener('scroll', () => { touched = true; if (!scheduled) { scheduled = true; requestAnimationFrame(measure); } }, { passive: true });
  addEventListener('pagehide', () => save(true));
  document.addEventListener('visibilitychange', () => { if (document.hidden) save(true); });
  // Discourage casual copying on every reader page, including free chapters.
  // This is a UI restriction; server-side access and fingerprints are separate.
  const isEditing = target => target instanceof Element && target.closest(
    'input, textarea, [contenteditable]:not([contenteditable="false"]), [role="textbox"]'
  );
  const blockCopy = event => { if (!isEditing(event.target)) event.preventDefault(); };
  ['copy', 'cut'].forEach(name => document.addEventListener(name, blockCopy, true));
  ['contextmenu', 'selectstart', 'dragstart'].forEach(name => reader.addEventListener(name, blockCopy));
  document.addEventListener('keydown', event => {
    if (isEditing(event.target)) return;
    // Physical key codes also cover the Russian keyboard layout.
    const copyKeys = ['KeyA', 'KeyC', 'KeyX'].includes(event.code)
      || ['a', 'c', 'x'].includes(event.key.toLowerCase());
    const insert = event.code === 'Insert' || event.key === 'Insert';
    const remove = event.code === 'Delete' || event.key === 'Delete';
    if (((event.ctrlKey || event.metaKey) && copyKeys)
        || (event.ctrlKey && insert) || (event.shiftKey && remove)) event.preventDefault();
  }, true);
  measure();
})();
