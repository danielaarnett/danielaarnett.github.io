<?php namespace Arnett; ?>
<a class="text-link" href="/admin/works/<?=(int)$work['id']?>/edit"><?=e($work['title'])?></a><h1 class="space-above"><?=e($record['title']??'Новая глава')?></h1><p class="page-intro">Полный текст и бесплатный фрагмент хранятся отдельно.</p><?php if($error):?><p class="form-error" role="alert"><?=e($error)?></p><?php endif;?>
<form method="post" class="editor-form chapter-editor"><?=csrf_field()?>
<?php
field('title','Название главы',$record);field('slug','Адрес главы (латиницей)',$record);field('number','Номер главы (0 — пролог)',$record,'number');field('sort_order','Порядок в оглавлении',$record,'number');
field('body_format','Формат текста',$record,'select',['markdown'=>'Markdown','html'=>'HTML']);field('body','Полный текст',$record,'textarea');field('access_type','Доступ к главе',$record,'select',ACCESS_LABELS);
field('fragment_body','Бесплатный фрагмент (в том же формате)',$record,'textarea');field('fragment_blocks','Или взять первые N блоков полного текста',$record,'number');field('is_published','Опубликовать главу',$record,'checkbox');
?><button class="button button-dark" type="submit">Сохранить</button></form>
