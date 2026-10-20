<?php
declare(strict_types=1);
namespace Arnett;

require __DIR__.'/views.php';
require __DIR__.'/content.php';
require __DIR__.'/admin.php';

function dispatch(): void {
    start_http();seed();
    $method=$_SERVER['REQUEST_METHOD']??'GET';
    if(!in_array($method,['GET','HEAD','POST'],true))fail(405);
    $path=parse_url($_SERVER['REQUEST_URI']??'/',PHP_URL_PATH);
    if(!is_string($path) || preg_match('/[\x00-\x20\\\\]/',$path))fail(400);
    // Legacy explicit index.html URLs must pass through the same access checks.
    $path=preg_replace('~/index\.(?:html|php)$~','/',$path);
    $path=$path==='/'?'/':rtrim($path,'/');
    $isPost=in_array($path,['/auth/login','/auth/logout','/auth/ticket','/api/progress'],true)||str_starts_with($path,'/admin/')||preg_match('~^/api/publication/[^/]+$~',$path);
    if($method==='POST' && !$isPost)fail(405);
    if($path==='/auth/login'){login($method);return;}
    if($path==='/auth/ticket'){ticket_login($method);return;}
    if($path==='/auth/logout'){if($method!=='POST')fail(405);$_SESSION=[];session_regenerate_id(true);redirect('/');}
    if($path==='/api/progress'){if($method!=='POST')fail(405);progress();}
    if(preg_match('~^/api/publication/([a-z0-9-]+)$~D',$path,$m)){publication($m[1],$method);}
    if($path==='/admin'||str_starts_with($path,'/admin/')){admin($path,$method);return;}
    if($method==='POST')fail(405);
    if($path==='/') {
        $html=file_get_contents(__DIR__.'/views/home.html');
        $html=str_replace('</head>','<meta name="csrf-token" content="'.e(csrf()).'"></head>',$html);
        echo $html;return;
    }
    if($path==='/library'){catalog();return;}
    if(preg_match('~^/works/([a-z0-9-]+)$~D',$path,$m)) {
        $work=visible_work($m[1]);if(TIERS[tier()]<TIERS[required_tier($work)])fail(403);
        $chapters=chapters((int)$work['id']);page($work['title'],view('work',compact('work','chapters')));return;
    }
    if(preg_match('~^/read/([a-z0-9-]+)/([a-z0-9-]+)$~D',$path,$m)){reading($m[1],$m[2]);return;}
    fail(404);
}
