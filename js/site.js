(() => {
  'use strict';
  const audioLinks = document.querySelectorAll('[data-open-audio]');
  if (audioLinks.length) {
    const dialog = document.createElement('dialog');
    dialog.id = 'audio-dialog';
    dialog.className = 'notice-dialog';
    dialog.setAttribute('aria-labelledby', 'audio-dialog-title');
    const close = document.createElement('button');
    close.className = 'dialog-close';
    close.setAttribute('aria-label', 'Закрыть окно');
    close.textContent = '×';
    const title = document.createElement('h2');
    title.id = 'audio-dialog-title';
    title.textContent = 'Аудиокниги';
    const description = document.createElement('p');
    description.textContent = 'Раздел готовится. Здесь появятся аудиоверсии произведений.';
    dialog.append(close, title, description);
    document.body.append(dialog);
    audioLinks.forEach(link => link.addEventListener('click', event => {
      event.preventDefault();
      dialog.showModal();
    }));
    close.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
  }
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#main-nav');
  if (!toggle || !nav) return;
  const setMenu = open => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    nav.classList.toggle('is-open', open);
  };
  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { setMenu(false); toggle.focus(); }
  });
  document.addEventListener('click', event => { if (!event.target.closest('.site-header')) setMenu(false); });
  matchMedia('(min-width: 1101px)').addEventListener('change', event => { if (event.matches) setMenu(false); });
})();
