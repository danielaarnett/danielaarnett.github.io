(() => {
  'use strict';
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('.bookshelf').forEach(shelf => {
    const row = shelf.querySelector('.shelf-books');
    const buttons = [...shelf.querySelectorAll('[data-shelf-step]')];
    let drag = null;
    let ignoreClickUntil = 0;
    const update = () => buttons.forEach(button => {
      button.disabled = Number(button.dataset.shelfStep) < 0
        ? row.scrollLeft <= 1 : row.scrollLeft >= row.scrollWidth - row.clientWidth - 1;
    });
    const move = direction => row.scrollBy({ left: direction * Math.max(200, row.clientWidth * .75), behavior: reducedMotion.matches ? 'instant' : 'smooth' });
    buttons.forEach(button => button.addEventListener('click', () => move(Number(button.dataset.shelfStep))));
    row.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'mouse' || event.button !== 0) return;
      drag = { id: event.pointerId, x: event.clientX, scroll: row.scrollLeft, moved: false };
    });
    row.addEventListener('pointermove', event => {
      if (!drag || drag.id !== event.pointerId) return;
      const distance = event.clientX - drag.x;
      if (!drag.moved && Math.abs(distance) > 6) {
        drag.moved = true;
        row.setPointerCapture(event.pointerId);
        row.classList.add('is-dragging');
      }
      if (drag.moved) {
        event.preventDefault();
        row.scrollLeft = drag.scroll - distance;
      }
    });
    const release = event => {
      if (!drag || (event.pointerId !== undefined && drag.id !== event.pointerId)) return;
      if (drag.moved) ignoreClickUntil = performance.now() + 350;
      const pointerId = drag.id;
      drag = null;
      if (row.hasPointerCapture(pointerId)) row.releasePointerCapture(pointerId);
      row.classList.remove('is-dragging');
    };
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
    window.addEventListener('blur', release);
    row.addEventListener('lostpointercapture', release);
    row.addEventListener('dragstart', event => event.preventDefault());
    row.addEventListener('click', event => {
      if (performance.now() < ignoreClickUntil) { event.preventDefault(); event.stopPropagation(); }
    }, true);
    row.addEventListener('keydown', event => {
      if (event.target !== row || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      move(event.key === 'ArrowLeft' ? -1 : 1);
    });
    row.addEventListener('wheel', event => {
      if (event.ctrlKey || !event.shiftKey || event.deltaX || row.scrollWidth <= row.clientWidth) return;
      const next = Math.max(0, Math.min(row.scrollWidth - row.clientWidth, row.scrollLeft + event.deltaY));
      if (next !== row.scrollLeft) { event.preventDefault(); row.scrollLeft = next; }
    }, { passive: false });
    row.addEventListener('scroll', update, { passive: true });
    new ResizeObserver(update).observe(row);
    update();
  });

  const dialog = document.querySelector('#forthcoming-dialog');
  document.querySelectorAll('[data-forthcoming]').forEach(link => link.addEventListener('click', event => {
    if (event.defaultPrevented) return;
    event.preventDefault();
    dialog.querySelector('#forthcoming-title').textContent = link.dataset.forthcoming;
    dialog.showModal();
  }));
  dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
})();
