(() => {
  'use strict';
  const dialog = document.querySelector('#publication-dialog');
  if (!dialog) return;
  const api = dialog.dataset.voteApi;
  const button = dialog.querySelector('[data-submit-vote]');
  const count = dialog.querySelector('[data-votes]');
  const message = dialog.querySelector('[data-vote-message]');
  let csrf = '', pending = false;
  const show = text => { message.textContent = text; };
  const apply = data => {
    if (Number.isInteger(data.votes)) count.textContent = new Intl.NumberFormat('ru-RU').format(data.votes);
    button.disabled = Boolean(data.retry_after);
    if (data.csrf_token) csrf = data.csrf_token;
  };
  document.querySelectorAll('[data-open-publication]').forEach(open => open.addEventListener('click', async () => {
    dialog.showModal();
    if (pending) return;
    button.disabled = true;
    if (!api) { show(''); return; }
    show('Загружаем число голосов…');
    try {
      const response = await fetch(api, { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error();
      const data = await response.json();
      apply(data);
      show(data.retry_after ? 'Ваш голос уже учтён. Повторить можно через час после предыдущего голоса.' : '');
    } catch { show('Не удалось загрузить голосование. Попробуйте открыть окно позже.'); }
  }));
  button.addEventListener('click', async () => {
    if (!api || pending || !csrf) return;
    pending = true;
    button.disabled = true;
    show('Отправляем ваш голос…');
    try {
      const response = await fetch(api, { method: 'POST', credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrf, 'Accept': 'application/json' } });
      const data = await response.json();
      if (!response.ok && response.status !== 429) throw new Error();
      apply(data);
      show(data.message);
    } catch {
      show('Не удалось отправить голос. Попробуйте ещё раз.');
      button.disabled = false;
    } finally { pending = false; }
  });
  dialog.querySelector('[data-close-publication]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
})();
