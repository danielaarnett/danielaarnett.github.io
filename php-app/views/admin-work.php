<?php namespace Arnett; ?>
<a class="text-link" href="/admin">Авторская панель</a><h1 class="space-above"><?=e($work['title']??'Новое произведение')?></h1><?php if($error):?><p class="form-error" role="alert"><?=e($error)?></p><?php endif;?>
<form method="post" class="editor-form"><?=csrf_field()?>
<?php
field('title','Название',$record);field('slug','Адрес произведения (латиницей)',$record);field('subtitle','Подзаголовок / вид произведения',$record);
field('shelf','Полка в библиотеке',$record,'select',SHELVES);field('minimum_tier','Минимальный уровень для книги',$record,'select',TIER_LABELS);
field('description','Описание',$record,'textarea');field('cover_path','Обложка, например /images/Book01.png',$record);
field('status','Состояние',$record,'select',STATUS_LABELS);field('access_type','Доступ к произведению',$record,'select',ACCESS_LABELS);
field('sort_order','Порядок в библиотеке',$record,'number');field('completion_percent','Готовность, %',$record,'number');field('is_visible','Показывать произведение читателям',$record,'checkbox');
?><button class="button button-dark" type="submit">Сохранить</button></form>
<?php if($work):?><section class="contents"><h2>Главы</h2><a class="text-link" href="/admin/works/<?=(int)$work['id']?>/chapters/new">Добавить главу +</a><?php foreach($chapters as $chapter):?><a class="chapter-link" href="/admin/works/<?=(int)$work['id']?>/chapters/<?=(int)$chapter['id']?>/edit"><span><?=(int)$chapter['number']?>. <?=e($chapter['title'])?></span><small><?=$chapter['is_published']?'Опубликована':'Скрыта'?></small></a><?php endforeach;?></section><?php endif;?>
