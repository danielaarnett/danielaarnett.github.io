(() => {
  'use strict';

  // Existing synopses and manuscript states; no unpublished prose is embedded here.
  const books = {
    krampus: {
      title: 'Дети Крампуса: Тени Йоля',
      genre: 'РОМАН · ТЁМНОЕ ФЭНТЕЗИ · ФОЛК-ХОРРОР',
      cover: './images/Book01.png',
      status: 'В работе · Первый черновик',
      synopsis: 'В городе посреди болот, где бойни и выделочные цеха кормят всех, дети рано узнают, что страх — часть порядка вещей. Йоль здесь не про подарки: в это время дети стараются не попадаться на глаза и не задавать лишних вопросов. Когда накануне праздника на товарном поезде появляется мальчик без имени, в городе начинают пропадать дети, а старые истории перестают казаться выдумкой. Никто не говорит об этом вслух, но все помнят: Йоль — это договор, и если его нарушить, за долгом приходит тот, кого здесь не называют по имени.'
    },
    order: {
      title: 'Орден на сдачу',
      genre: 'РОМАН · САТИРА · АНТИУТОПИЯ',
      cover: './images/Book02.png',
      status: 'В работе · Первый черновик',
      synopsis: 'Орден Света сокращён, выселен и оставлен существовать формально — без средств, без статуса и без ясной причины, по которой он вообще ещё должен существовать. Сэр Элмер пытается сохранить служение, а его правая рука — Тант всё чаще говорит о необходимости подчиниться системе. Но чем сильнее порядок заменяет смысл, тем яснее: опасность не снаружи. И когда над королевством нависает настоящая угроза, выясняется — защищать его больше некому.'
    },
    sero: {
      title: 'Iam sero est',
      genre: 'ЦИКЛ НОВЕЛЛ · ПСИХОЛОГИЧЕСКАЯ ПРОЗА',
      cover: './images/Book06.png',
      status: 'На очереди · Работа приостановлена',
      synopsis: 'Эти новеллы сосредоточены на состояниях, в которых человек перестаёт быть надёжным свидетелем собственной жизни. Насилие, вина, зависимость и искажённая память медленно размывают границы между реальным и воображаемым, оставляя героев наедине с тем, что невозможно ни оправдать, ни забыть. Сюжеты разворачиваются в пространстве психологического надлома, где близость оборачивается угрозой, а попытка спастись — новой формой самообмана.'
    }
  };

  // Word targets stay in the markup as data, never in the reader-facing labels.
  const wordCount = new Intl.NumberFormat('ru-RU');
  document.querySelectorAll('[data-progress-part]').forEach(part => {
    const written = Number(part.dataset.writtenWords);
    const target = Number(part.dataset.targetWords);
    if (!Number.isFinite(written) || written < 0 || !Number.isFinite(target) || target <= 0) return;
    const percent = Math.min(100, Math.round(written / target * 100));
    const words = wordCount.format(written);
    part.querySelector('[data-progress-words]').textContent = words;
    part.querySelector('[data-progress-percent]').textContent = percent;
    part.querySelector('.progress-value').setAttribute('stroke-dasharray', `${percent} 100`);
    part.querySelector('.progress-ring').setAttribute('aria-label', `Написано ${words} слов — ${percent}%`);
  });

  // Keep the accordion exclusive in browsers without native details grouping.
  if (!('name' in document.createElement('details'))) {
    const manuscripts = [...document.querySelectorAll('.manuscript')];
    manuscripts.forEach(current => current.addEventListener('toggle', () => {
      if (current.open) manuscripts.forEach(other => { if (other !== current) other.open = false; });
    }));
  }

  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#main-nav');
  const setMenu = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    nav.classList.toggle('is-open', open);
  };
  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      toggle.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.site-header')) setMenu(false);
  });
  window.matchMedia('(min-width: 1241px)').addEventListener('change', event => {
    if (event.matches) setMenu(false);
  });

  const bookDialog = document.querySelector('#book-dialog');
  document.querySelectorAll('[data-book]').forEach(button => button.addEventListener('click', () => {
    const book = books[button.dataset.book];
    if (!book) return;
    document.querySelector('#dialog-title').textContent = book.title;
    document.querySelector('#dialog-genre').textContent = book.genre;
    document.querySelector('#dialog-status').textContent = book.status;
    document.querySelector('#dialog-synopsis').textContent = book.synopsis;
    const cover = document.querySelector('#dialog-cover');
    cover.src = book.cover;
    cover.alt = `Обложка ${book.title}`;
    bookDialog.showModal();
  }));

  const drafts = { weakness: 'Моя слабость, моя боль', sun: 'Горячее солнце', chalk: 'Мелки', upcoming: 'Новый отрывок' };
  const draftDialog = document.querySelector('#draft-dialog');
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-draft]');
    if (!button || event.defaultPrevented) return;
    const title = drafts[button.dataset.draft];
    if (!title) return;
    event.preventDefault();
    document.querySelector('#draft-dialog-title').textContent = title;
    draftDialog.showModal();
  });

  const viewport = document.querySelector('.excerpt-viewport');
  if (viewport) {
    const track = viewport.querySelector('.excerpt-track');
    const group = track.querySelector('.excerpt-group');
    const originals = [...group.children];
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let loopWidth = 0, observedWidth = 0, previousFrame = 0, scrollRemainder = 0;
    let paused = reducedMotion.matches, hovered = false, focused = false, touching = false, visible = false;
    let drag = null, holdUntil = 0, ignoreClickUntil = 0;

    const copyForLoop = element => {
      const copy = element.cloneNode(true);
      copy.dataset.carouselCopy = '';
      copy.setAttribute('aria-hidden', 'true');
      copy.querySelectorAll('a, button, [tabindex]').forEach(link => link.tabIndex = -1);
      return copy;
    };
    const wrap = (force = false) => {
      if (!loopWidth || (focused && !touching && !force)) return;
      const position = viewport.scrollLeft;
      if (position < loopWidth || position >= loopWidth * 2) {
        viewport.scrollLeft = loopWidth + ((position - loopWidth) % loopWidth + loopWidth) % loopWidth;
      }
    };
    const rebuild = () => {
      const width = viewport.clientWidth;
      if (!width || width === observedWidth || !originals.length) return;
      observedWidth = width;
      const relativePosition = loopWidth ? (viewport.scrollLeft % loopWidth) / loopWidth : 0;
      track.querySelectorAll('[data-carousel-copy]').forEach(copy => copy.remove());
      const originalWidth = group.getBoundingClientRect().width;
      if (!originalWidth) return;
      const repeats = Math.ceil((width + originals[0].getBoundingClientRect().width) / originalWidth);
      for (let i = 1; i < repeats; i++) originals.forEach(card => group.append(copyForLoop(card)));
      loopWidth = group.getBoundingClientRect().width;
      track.prepend(copyForLoop(group));
      track.append(copyForLoop(group));
      viewport.scrollLeft = loopWidth * (1 + relativePosition);
    };
    reducedMotion.addEventListener('change', event => { paused = event.matches; });
    viewport.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse') hovered = true; });
    viewport.addEventListener('pointerleave', () => { hovered = false; });
    viewport.addEventListener('focusin', () => { focused = true; });
    viewport.addEventListener('focusout', event => {
      focused = viewport.contains(event.relatedTarget);
      if (!focused) wrap();
    });
    viewport.addEventListener('scroll', () => wrap(), { passive: true });
    viewport.addEventListener('dragstart', event => event.preventDefault());
    viewport.addEventListener('pointerdown', event => {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      touching = true;
      if (event.pointerType === 'mouse') drag = { id: event.pointerId, startX: event.clientX, lastX: event.clientX, moved: false };
    });
    viewport.addEventListener('pointermove', event => {
      if (!drag || event.pointerId !== drag.id) return;
      if (!drag.moved && Math.abs(event.clientX - drag.startX) > 6) {
        drag.moved = true;
        viewport.setPointerCapture(event.pointerId);
        viewport.classList.add('is-dragging');
      }
      if (drag.moved) {
        event.preventDefault();
        viewport.scrollLeft -= event.clientX - drag.lastX;
        wrap();
        drag.lastX = event.clientX;
      }
    });
    const release = event => {
      if (!touching) return;
      if (drag && event.pointerId !== drag.id) return;
      if (drag?.moved) ignoreClickUntil = performance.now() + 350;
      if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
      drag = null;
      touching = false;
      holdUntil = performance.now() + 2500;
      viewport.classList.remove('is-dragging');
    };
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
    window.addEventListener('blur', () => { drag = null; touching = false; hovered = false; viewport.classList.remove('is-dragging'); });
    viewport.addEventListener('click', event => {
      if (performance.now() < ignoreClickUntil) { event.preventDefault(); event.stopPropagation(); }
    }, true);
    viewport.addEventListener('wheel', event => {
      holdUntil = performance.now() + 2500;
      if (event.shiftKey && !event.deltaX) { event.preventDefault(); viewport.scrollLeft += event.deltaY; }
      requestAnimationFrame(() => wrap(true));
    }, { passive: false });
    viewport.addEventListener('keydown', event => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      viewport.scrollLeft += (event.key === 'ArrowRight' ? 1 : -1) * originals[0].getBoundingClientRect().width;
      wrap(true);
      holdUntil = performance.now() + 2500;
    });
    new ResizeObserver(rebuild).observe(viewport);
    new IntersectionObserver(entries => { visible = entries[0].isIntersecting; }).observe(viewport);
    rebuild();
    const animate = timestamp => {
      const elapsed = previousFrame ? Math.min(timestamp - previousFrame, 64) : 0;
      previousFrame = timestamp;
      if (visible && !document.hidden && !paused && !hovered && !focused && !touching && timestamp > holdUntil && !document.querySelector('dialog[open]')) {
        // Retain fractional movement on browsers that round scrollLeft to pixels.
        scrollRemainder += elapsed * .038;
        const pixels = Math.floor(scrollRemainder);
        if (pixels) { viewport.scrollLeft += pixels; scrollRemainder -= pixels; wrap(); }
      }
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }

  document.querySelector('[data-open-paper]').addEventListener('click', () => document.querySelector('#paper-dialog').showModal());
  document.querySelectorAll('dialog').forEach(dialog => {
    dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
    dialog.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', () => dialog.close()));
  });
  document.querySelector('#year').textContent = new Date().getFullYear();
})();
