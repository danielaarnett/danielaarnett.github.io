<?php namespace Arnett; ?>
<!doctype html><html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title><?=e($title)?> — Daniel A. Arnett</title><meta name="theme-color" content="#202522"><meta name="csrf-token" content="<?=e(csrf())?>">
<link rel="icon" href="/images/arnett-mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="/css/fonts.css"><link rel="stylesheet" href="/css/home.css?v=22"><link rel="stylesheet" href="/css/site.css?v=4">
<?=$styles?><script src="/js/site.js?v=3" defer></script><?=$scripts?>
</head><body class="<?=e($bodyClass)?>"><a class="skip-link" href="#main">Перейти к содержанию</a>
<header class="site-header"><div class="shell header-inner"><a class="brand" href="/" aria-label="Daniel A. Arnett — главная"><img class="brand-logo" src="/images/logo.png?v=eb5760f22b2a" alt="" width="1000" height="942"><span class="brand-name">Daniel A. Arnett<small>АВТОРСКАЯ СТРАНИЦА</small></span></a><button class="menu-toggle" aria-expanded="false" aria-controls="main-nav" aria-label="Открыть меню"><span></span><span></span></button><nav class="main-nav" id="main-nav" aria-label="Основная навигация"><?=navigation($bodyClass==='reading-page'?'reader':($class==='bookshelf-main'?'library':'default'))?></nav></div></header>
<?php if(!empty($_SESSION['flash'])): ?><div class="shell flash-list" role="status"><p><?=e($_SESSION['flash'])?></p></div><?php unset($_SESSION['flash']);endif; ?>
<main id="main" class="<?=$class==='reading-main'?'reading-main':'shell '.e($class)?>"><?=$content?></main>
<footer class="site-footer"><div class="shell footer-content"><a class="footer-brand" href="/">Daniel A. Arnett<span>АВТОРСКИЙ АРХИВ</span></a><p class="footer-title">Конец страницы — не <em>конец истории</em></p><p class="footer-copyright">© 2026-2027 All Rights Reserved.</p></div></footer>
</body></html>
