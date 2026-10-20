<?php
declare(strict_types=1);
namespace Arnett;

function seed(): void {
    if (one('SELECT value FROM settings WHERE name=?',['catalog_seeded'])) return;
    $seed=json_decode(file_get_contents(__DIR__.'/seed/catalog.json'),true,512,JSON_THROW_ON_ERROR);
    db()->beginTransaction();
    try {
        foreach($seed['works'] as $work) {
            query('INSERT OR IGNORE INTO works(slug,title,subtitle,cover_path,shelf,sort_order,is_visible,published_at,updated_at) VALUES(?,?,?,?,?,?,1,?,?)',[$work['slug'],$work['title'],$work['subtitle'],$work['cover_path'],$work['shelf'],$work['sort_order'],time(),time()]);
        }
        $w=one('SELECT id FROM works WHERE slug=?',['moya-slabost-moya-bol']);$c=$seed['prologue'];
        query('INSERT OR IGNORE INTO chapters(work_id,slug,title,number,body,body_format,access_type,is_published,published_at,word_count) VALUES(?,?,?,0,?,\'html\',\'free\',1,?,?)',[$w['id'],$c['slug'],$c['title'],$c['body'],time(),word_count($c['body'])]);
        foreach(['krampus','orden-na-sdachu'] as $slug) query('INSERT OR IGNORE INTO publication_interest(slug,votes) VALUES(?,0)',[$slug]);
        query('INSERT INTO settings(name,value) VALUES(?,?)',['catalog_seeded','1']);
        db()->commit();
    }catch(\Throwable $error){if(db()->inTransaction())db()->rollBack();throw $error;}
}
function word_count(string $html): int { preg_match_all("/[^\\W_]+(?:[-’'][^\\W_]+)*/u",html_entity_decode(strip_tags($html),ENT_QUOTES|ENT_HTML5,'UTF-8'),$matches);return count($matches[0]); }
function visible_work(string $slug): array {
    if(!slug_ok($slug))fail(404);
    $w=one('SELECT * FROM works WHERE slug=? AND is_visible=1 AND published_at IS NOT NULL AND published_at<=?',[$slug,time()]);
    if(!$w)fail(404);return $w;
}
function chapters(int $work): array {
    // Prose columns are intentionally absent from all catalog and access queries.
    return all('SELECT id,work_id,slug,title,number,sort_order,access_type,is_published,published_at FROM chapters WHERE work_id=? AND is_published=1 AND published_at IS NOT NULL AND published_at<=? ORDER BY sort_order,number,id',[$work,time()]);
}
function catalog(): void {
    $shelves=array_fill_keys(array_keys(SHELVES),[]);
    foreach(all('SELECT * FROM works WHERE is_visible=1 AND published_at IS NOT NULL AND published_at<=? ORDER BY sort_order,id',[time()]) as $work) {
        if(TIERS[tier()]<TIERS[required_tier($work)] || !isset($shelves[$work['shelf']]))continue;
        $chapters=chapters((int)$work['id']); $available=null;
        foreach($chapters as $chapter)if(in_array(access($work,$chapter),['full','fragment'],true)){$available=$chapter;break;}
        if($chapters && !$available)continue;
        $work['href']=$available?'/read/'.$work['slug'].'/'.$available['slug'].'/':'#forthcoming-dialog';
        $work['placeholder']=!$available;
        $shelves[$work['shelf']][]=$work;
    }
    page('Библиотека',view('catalog',compact('shelves')),'bookshelf-main','','<link rel="stylesheet" href="/css/library.css?v=5">','<script src="/js/library.js?v=1" defer></script>');
}
function reading(string $workSlug,string $chapterSlug): void {
    rate('reading-minute',30,60);rate('reading-hour',300,3600);
    $work=visible_work($workSlug);if(!slug_ok($chapterSlug))fail(404);
    $chapters=chapters((int)$work['id']);$chapter=null;$index=0;
    foreach($chapters as $i=>$c)if($c['slug']===$chapterSlug){$chapter=$c;$index=$i;break;}
    if(!$chapter)fail(404);
    $mode=access($work,$chapter);
    query('INSERT INTO read_audit(user_id,chapter_id,ip_hash,status,created_at) VALUES(?,?,?,?,?)',[user()['id']??null,$chapter['id'],ip_hash('audit'),$mode==='deny'?403:200,time()]);
    if($mode==='unpublished')fail(404);
    if($mode==='deny')fail(403,'Продолжение доступно читателям с соответствующим уровнем доступа.');
    // The first body query happens only after the access decision, selecting one column.
    $column=$mode==='fragment'?'fragment_body':'body';
    $body=one('SELECT '.$column.' AS content,body_format FROM chapters WHERE id=?',[$chapter['id']]);
    $html=clean_html($body['content'],$body['body_format']);
    $protected=$mode==='full' && user() && (tier()!=='free' || user()['is_admin']);
    if($protected && (config()['fingerprints_enabled']??true))$html=fingerprint($html,(int)$chapter['id']);
    $progress=user()?one('SELECT paragraph_id,scroll_position,updated_at FROM reading_progress WHERE user_id=? AND chapter_id=?',[user()['id'],$chapter['id']]):null;
    page($chapter['title'].' — '.$work['title'],view('reader',compact('work','chapter','chapters','index','mode','html','protected','progress')),'reading-main','reading-page','<link rel="stylesheet" href="/reading.css">','<script src="/js/reader.js?v=3" defer></script>');
}
function progress(): never {
    $u=user();if(!$u)fail(401);rate('progress',12,60,'user:'.$u['id']);
    try{$data=json_decode(file_get_contents('php://input'),true,32,JSON_THROW_ON_ERROR);}catch(\JsonException){fail(400);}
    if(!is_array($data) || !is_int($data['chapter_id']??null))fail(400);
    $c=one('SELECT id,work_id,access_type,is_published,published_at FROM chapters WHERE id=?',[$data['chapter_id']]);if(!$c)fail(404);
    $w=one('SELECT * FROM works WHERE id=?',[$c['work_id']]);$mode=access($w,$c);
    if($mode==='unpublished')fail(404);if($mode==='deny')fail(403);
    $position=$data['scroll_position']??null;$paragraph=$data['paragraph_id']??'';
    if((!is_float($position)&&!is_int($position)) || !is_finite((float)$position) || $position<0 || $position>1 || !is_string($paragraph) || !preg_match('/^p-[1-9][0-9]{0,5}$/D',$paragraph))fail(400);
    query('INSERT INTO reading_progress(user_id,chapter_id,paragraph_id,scroll_position,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id,chapter_id) DO UPDATE SET paragraph_id=excluded.paragraph_id,scroll_position=excluded.scroll_position,updated_at=excluded.updated_at',[$u['id'],$c['id'],$paragraph,$position,time()]);
    json_response(['saved'=>true]);
}
function publication(string $slug,string $method): never {
    if(!in_array($slug,['krampus','orden-na-sdachu'],true))fail(404);
    $keys=[ip_hash('publication:'.$slug),hash_hmac('sha256','publication-cookie:'.$slug.':'.voter_cookie(),config()['secret'])];
    if($method==='GET') {
        $votes=(int)(one('SELECT votes FROM publication_interest WHERE slug=?',[$slug])['votes']??0);
        $row=one('SELECT MAX(voted_at) AS voted_at FROM publication_vote WHERE book_slug=? AND ip_hash IN (?,?)',[$slug,...$keys]);
        json_response(['votes'=>$votes,'retry_after'=>$row?max(0,(int)$row['voted_at']+3600-time()):0,'csrf_token'=>csrf()]);
    }
    rate('vote-submit',120,3600);
    // Close the session before the database transaction, so independent workers are covered too.
    session_write_close();db()->exec('BEGIN IMMEDIATE');
    try {
        $now=time();$row=one('SELECT MAX(voted_at) AS voted_at FROM publication_vote WHERE book_slug=? AND ip_hash IN (?,?)',[$slug,...$keys]);
        $retry=$row?max(0,(int)$row['voted_at']+3600-$now):0;
        if(!$retry) {
            foreach($keys as $key)query('INSERT INTO publication_vote(book_slug,ip_hash,voted_at) VALUES(?,?,?) ON CONFLICT(book_slug,ip_hash) DO UPDATE SET voted_at=excluded.voted_at',[$slug,$key,$now]);
            query('UPDATE publication_interest SET votes=votes+1 WHERE slug=?',[$slug]);
        }
        $votes=(int)one('SELECT votes FROM publication_interest WHERE slug=?',[$slug])['votes'];
        db()->exec('COMMIT');
    }catch(\Throwable $error){db()->exec('ROLLBACK');throw $error;}
    if($retry)header('Retry-After: '.$retry);
    json_response(['votes'=>$votes,'retry_after'=>$retry?:3600,'message'=>$retry?'Вы уже проголосовали. Следующий голос можно оставить через час после предыдущего.':'Спасибо за ваш голос! Он сохранён и поможет автору определить очередь публикации книги.'],$retry?429:200);
}
