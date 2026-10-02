(() => {
  'use strict';
  const dialog = document.querySelector('#publication-dialog');
  if (!dialog) return;
  const baseApi = dialog.dataset.voteApi;
  const pages = [...dialog.querySelectorAll('[data-publication-page]')];
  let index = 0, requestId = 0, pending = false;
  const tokens = new Map();
  const apiFor = page => baseApi ? baseApi.replace(/[^/]+$/, page.dataset.publicationPage) : '';
  const show = (page, text) => { page.querySelector('[data-vote-message]').textContent = text; };
  const apply = (page, data) => {
    if (Number.isInteger(data.votes)) page.querySelector('[data-votes]').textContent = new Intl.NumberFormat('ru-RU').format(data.votes);
    page.querySelector('[data-submit-vote]').disabled = Boolean(data.retry_after);
    if (data.csrf_token) tokens.set(page, data.csrf_token);
  };
  const load = async () => {
    const page = pages[index], api = apiFor(page), id = ++requestId;
    page.querySelector('[data-submit-vote]').disabled = true;
    show(page, '');
    if (!api) return;
    try {
      const response = await fetch(api, { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (id !== requestId) return;
      apply(page, data);
      show(page, data.retry_after ? 'Ваш голос уже учтён. Повторить можно через час после предыдущего голоса.' : '');
    } catch {
      if (id === requestId) show(page, 'Не удалось загрузить голосование. Попробуйте открыть окно позже.');
    }
  };
  document.querySelectorAll('[data-open-publication]').forEach(open => open.addEventListener('click', () => {
    dialog.showModal();
    if (!pending) load();
  }));
  dialog.querySelectorAll('[data-publication-step]').forEach(control => control.addEventListener('click', () => {
    if (pending) return;
    index = (index + Number(control.dataset.publicationStep) + pages.length) % pages.length;
    pages.forEach((page, i) => { page.hidden = i !== index; });
    dialog.setAttribute('aria-labelledby', pages[index].querySelector('h2').id);
    dialog.querySelector('[data-publication-position]').textContent = `${index + 1} / ${pages.length}`;
    load();
  }));
  pages.forEach(page => page.querySelector('[data-submit-vote]').addEventListener('click', async () => {
    const api = apiFor(page), csrf = tokens.get(page), button = page.querySelector('[data-submit-vote]');
    if (!api || pending || !csrf) return;
    pending = true;
    button.disabled = true;
    show(page, 'Отправляем ваш голос…');
    try {
      const response = await fetch(api, { method: 'POST', credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrf, 'Accept': 'application/json' } });
      const data = await response.json();
      if (!response.ok && response.status !== 429) throw new Error();
      apply(page, data);
      show(page, data.message);
    } catch {
      show(page, 'Не удалось отправить голос. Попробуйте ещё раз.');
      button.disabled = false;
    } finally { pending = false; }
  }));
  dialog.querySelector('[data-close-publication]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
})();
