(() => {
  'use strict';
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

  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const workshop = document.querySelector('.workshop');
  const manuscripts = [...document.querySelectorAll('.manuscript')];
  const states = new WeakMap();
  const animations = new WeakMap();
  const setExpanded = (item, expanded) => {
    const startHeight = item.getBoundingClientRect().height;
    animations.get(item)?.cancel();
    states.set(item, expanded);
    item.querySelector('summary').setAttribute('aria-expanded', String(expanded));
    item.classList.toggle('is-expanded', expanded);
    workshop.classList.toggle('has-open-book', manuscripts.some(book => states.get(book)));
    item.style.height = '';
    item.open = true;
    const endHeight = expanded ? item.getBoundingClientRect().height : item.querySelector('summary').getBoundingClientRect().height + 2;
    const finish = () => { item.open = expanded; item.style.height = ''; animations.delete(item); };
    if (motion.matches) { finish(); return; }
    const animation = item.animate([{ height: `${startHeight}px` }, { height: `${endHeight}px` }], { duration: 420, easing: 'cubic-bezier(.22,.7,.25,1)' });
    animations.set(item, animation);
    animation.onfinish = finish;
  };
  manuscripts.forEach(item => {
    item.removeAttribute('name');
    states.set(item, item.open);
    const summary = item.querySelector('summary');
    summary.setAttribute('aria-expanded', String(item.open));
    summary.addEventListener('click', event => {
      event.preventDefault();
      const expanded = !states.get(item);
      if (expanded) manuscripts.forEach(other => { if (other !== item && states.get(other)) setExpanded(other, false); });
      setExpanded(item, expanded);
    });
  });

  const notices = {
    sun: ['Горячее солнце', 'Публикация готовится. Кнопка чтения станет доступна, когда текст появится на сайте.'],
    krampus: ['Дети Крампуса: Тени Йоля', 'Публикация готовится. Кнопка чтения станет доступна, когда текст появится на сайте.'],
    witness: ['Свидетель', 'Подписка за 150 руб./мес. готовится к открытию. Здесь появится переход на Boosty.'],
    appreciator: ['Ценитель', 'Подписка за 350 руб./мес. готовится к открытию. Здесь появится переход на Boosty.'],
    paper: ['Бумажные издания', 'Предзаказ пока не открыт. Информация о доступных изданиях, сроках и способах заказа появится здесь.'],
    audio: ['Аудиокниги', 'Раздел готовится. Здесь появятся аудиоверсии произведений.']
  };
  const dialog = document.querySelector('#notice-dialog');
  document.querySelectorAll('[data-notice]').forEach(button => button.addEventListener('click', event => {
    const notice = notices[button.dataset.notice];
    if (!notice) return;
    event.preventDefault();
    document.querySelector('#notice-title').textContent = notice[0];
    document.querySelector('#notice-text').textContent = notice[1];
    dialog.showModal();
  }));
  dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  const backToTop = document.querySelector('.back-to-top');
  let scrollFrame = 0;
  const updateBackToTop = () => {
    const visible = window.scrollY > 280;
    backToTop.hidden = !visible;
    scrollFrame = 0;
  };
  window.addEventListener('scroll', () => {
    if (!scrollFrame) scrollFrame = requestAnimationFrame(updateBackToTop);
  }, { passive: true });
  updateBackToTop();
  backToTop.addEventListener('click', event => {
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: motion.matches ? 'instant' : 'smooth' });
    document.querySelector('.brand').focus({ preventScroll: true });
  });
  document.querySelector('#year').textContent = new Date().getFullYear();

})();
