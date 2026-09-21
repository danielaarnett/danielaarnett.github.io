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
  window.matchMedia('(min-width: 901px)').addEventListener('change', event => {
    if (event.matches) setMenu(false);
  });

  const filters = [...document.querySelectorAll('[data-filter]')];
  const cards = [...document.querySelectorAll('[data-genre]')];
  filters.forEach(button => button.addEventListener('click', () => {
    filters.forEach(filter => {
      const active = filter === button;
      filter.classList.toggle('active', active);
      filter.setAttribute('aria-pressed', String(active));
    });
    let count = 0;
    cards.forEach(card => {
      card.hidden = button.dataset.filter !== 'all' && card.dataset.genre !== button.dataset.filter;
      if (!card.hidden) count++;
    });
    document.querySelector('#filter-status').textContent = `Показано произведений: ${count}`;
  }));

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

  document.querySelector('[data-open-support]').addEventListener('click', () => document.querySelector('#support-dialog').showModal());
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
