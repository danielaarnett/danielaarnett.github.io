<?php
declare(strict_types=1);
namespace Arnett;

function navigation(string $kind='default'): string {
    $links='<a href="https://games.danielarnett.com/">Игры</a>';
    if ($kind==='reader') $links.='<a href="/library/">Книги</a>';
    elseif ($kind==='library') $links.='<a href="/#drafts">Читать</a>';
    else $links.='<a href="/#drafts">Читать</a><a href="/library/">Книги</a>';
    $links.='<a href="/#workshop">В работе</a><a href="/#audiobooks">Аудиокниги</a><a class="nav-support" href="/#prose">Читательский круг</a>';
    if (user()) {
        if (user()['is_admin']) $links.='<a href="/admin">Авторская панель</a>';
        $links.='<form action="/auth/logout" method="post">'.csrf_field().'<button class="nav-action" type="submit">Выйти</button></form>';
    }
    return $links;
}
function view(string $name,array $data=[]): string { extract($data,EXTR_SKIP);ob_start();require __DIR__.'/views/'.$name.'.php';return ob_get_clean(); }
function page(string $title,string $content,string $class='core-main',string $bodyClass='',string $styles='',string $scripts=''): void {
    echo view('layout',compact('title','content','class','bodyClass','styles','scripts'));
}
function field(string $name,string $label,array $record,string $kind='text',array $options=[]): void {
    $value=$record[$name] ?? '';
    echo '<div class="form-field'.($kind==='checkbox'?' checkbox-field':'').'">';
    if($kind==='checkbox') {
        echo '<input type="checkbox" id="'.e($name).'" name="'.e($name).'" value="1"'.($value?' checked':'').'><label for="'.e($name).'">'.e($label).'</label>';
    } else {
        echo '<label for="'.e($name).'">'.e($label).'</label>';
        if($kind==='select') {
            echo '<select name="'.e($name).'" id="'.e($name).'">';
            foreach($options as $key=>$text) echo '<option value="'.e($key).'"'.((string)$key===(string)$value?' selected':'').'>'.e($text).'</option>';
            echo '</select>';
        } elseif($kind==='textarea') echo '<textarea name="'.e($name).'" id="'.e($name).'" maxlength="700000">'.e($value).'</textarea>';
        else echo '<input name="'.e($name).'" id="'.e($name).'" type="'.e($kind).'" value="'.e($kind==='password'?'':$value).'"'.($kind==='password'?' autocomplete="new-password"':'').'>';
    }
    echo '</div>';
}
