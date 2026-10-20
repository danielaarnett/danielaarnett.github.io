<?php namespace Arnett; ?>
<header class="bookshelf-heading"><h1>Выберите книгу, чтобы открыть её и начать читать</h1><span class="reader-level">Ваш доступ: <?=e(TIER_LABELS[tier()])?></span></header>
<div class="bookshelves">
<?php foreach(SHELVES as $key=>$label): ?>
<section class="bookshelf" id="<?=e($key)?>" aria-labelledby="shelf-<?=e($key)?>"><header class="shelf-heading"><h2 id="shelf-<?=e($key)?>"><?=e($label)?></h2><div class="shelf-controls"><button type="button" data-shelf-step="-1" aria-label="Прокрутить полку влево" aria-controls="books-<?=e($key)?>">‹</button><button type="button" data-shelf-step="1" aria-label="Прокрутить полку вправо" aria-controls="books-<?=e($key)?>">›</button></div></header>
<div id="books-<?=e($key)?>" tabindex="0" role="region" aria-label="<?=e($label)?>: горизонтальная прокрутка" class="shelf-books">
<?php foreach($shelves[$key] as $book): ?>
<a class="shelf-book" href="<?=e($book['href'])?>"<?=empty($book['placeholder'])?'':' data-forthcoming="'.e($book['title']).'"'?>><div class="shelf-cover"><img src="/images/shelf-<?=e(COVERS[$key])?>.png" alt="" loading="lazy" draggable="false"></div><h3><?=e($book['title'])?></h3><?php if($book['subtitle']):?><p><?=e($book['subtitle'])?></p><?php endif;?></a>
<?php endforeach; if(!$shelves[$key]): ?><p>На этой полке пока нет доступных вам текстов.</p><?php endif; ?>
</div></section><?php endforeach; ?></div>
<dialog class="notice-dialog" id="forthcoming-dialog" aria-labelledby="forthcoming-title"><button class="dialog-close" type="button" aria-label="Закрыть окно">×</button><h2 id="forthcoming-title">Текст готовится к публикации</h2><p>Эта история пока недоступна для чтения. Здесь появится текст, когда он будет опубликован.</p></dialog>
