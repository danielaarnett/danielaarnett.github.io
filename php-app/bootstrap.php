<?php
declare(strict_types=1);

namespace Arnett;

use PDO;
use RuntimeException;

const TIERS = ['free' => 0, 'witness' => 1, 'appreciator' => 2];
const TIER_LABELS = ['free' => 'Бесплатно', 'witness' => 'Свидетель', 'appreciator' => 'Ценитель'];
const SHELVES = ['novellas'=>'Новеллы','short_novels'=>'Повести','novels'=>'Романы','scripts'=>'Сценарии','unfinished'=>'Незаконченные','poetry'=>'Стихотворения','songs'=>'Песни'];
const COVERS = ['novellas'=>'novellas','short_novels'=>'short-novels','novels'=>'novels','scripts'=>'scripts','unfinished'=>'unfinished','poetry'=>'poetry','songs'=>'songs'];
const ACCESS_LABELS = ['free'=>'Бесплатно','fragment'=>'Ознакомительный фрагмент','subscriber'=>'Для читательского круга'];
const STATUS_LABELS = ['draft'=>'Черновик','ongoing'=>'В работе','completed'=>'Завершено'];

require __DIR__ . '/vendor/autoload.php';

function private_dir(): string {
    return getenv('ARNETT_PRIVATE_DIR') ?: dirname(__DIR__) . '/arnett-private';
}
function config(): array {
    static $config;
    if ($config !== null) return $config;
    $file = private_dir() . '/config.php';
    if (!is_file($file)) throw new RuntimeException('Private configuration is missing');
    $config = require $file;
    if (!is_array($config) || strlen($config['secret'] ?? '') < 32) throw new RuntimeException('Configure a random application secret');
    if (($config['production'] ?? true) && !str_starts_with($config['base_url'] ?? '', 'https://')) throw new RuntimeException('HTTPS is required');
    return $config;
}
function db(): PDO {
    static $db;
    if ($db) return $db;
    $dir = private_dir();
    if (!is_dir($dir)) mkdir($dir, 0700, true);
    $db = new PDO('sqlite:' . $dir . '/library.sqlite', null, null, [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
    $db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=10000; PRAGMA journal_mode=WAL');
    $db->exec(file_get_contents(__DIR__.'/schema.sql'));
    @chmod($dir . '/library.sqlite', 0600);
    return $db;
}
function query(string $sql, array $params=[]): \PDOStatement { $q=db()->prepare($sql); $q->execute($params); return $q; }
function one(string $sql, array $params=[]): ?array { return query($sql,$params)->fetch() ?: null; }
function all(string $sql, array $params=[]): array { return query($sql,$params)->fetchAll(); }
function e(mixed $s): string { return htmlspecialchars((string)($s ?? ''), ENT_QUOTES|ENT_SUBSTITUTE, 'UTF-8'); }
function slug_ok(string $s): bool { return strlen($s)<=120 && preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D',$s)===1; }
function cover_ok(string $s): bool { return $s==='' || preg_match('~^/images/[A-Za-z0-9_-]+\.(png|jpe?g|webp|svg)$~D',$s)===1; }
function json_response(array $data, int $status=200): never { http_response_code($status); header('Content-Type: application/json; charset=utf-8'); echo json_encode($data,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR); exit; }
function redirect(string $path, int $status=303): never { header('Location: '.$path,true,$status); exit; }
function fail(int $status, string $message=''): never {
    http_response_code($status);
    $labels=[400=>'Некорректный запрос',401=>'Войдите в аккаунт',403=>'Этот текст пока недоступен',404=>'Страница не найдена',405=>'Этот способ обращения не поддерживается',429=>'Слишком много обращений',503=>'Сайт временно недоступен'];
    if (str_starts_with($_SERVER['REQUEST_URI'] ?? '', '/api/')) json_response(['message'=>$message ?: ($labels[$status] ?? 'Ошибка')],$status);
    page($labels[$status] ?? 'Ошибка', '<div class="narrow-panel"><h1>'.e($labels[$status] ?? 'Ошибка').'</h1><p class="page-intro">'.e($message).'</p><a class="button button-dark" href="/">Главная страница</a></div>'); exit;
}
function safe_next(string $s): string { return str_starts_with($s,'/') && !str_starts_with($s,'//') && !preg_match('/[\\\\\x00-\x20]/',$s) ? $s : '/library/'; }
function csrf(): string { return $_SESSION['csrf'] ??= bin2hex(random_bytes(32)); }
function check_csrf(): void {
    $token=$_SERVER['HTTP_X_CSRFTOKEN'] ?? ($_POST['csrf_token'] ?? '');
    if (!is_string($token) || !isset($_SESSION['csrf']) || !hash_equals($_SESSION['csrf'],$token)) fail(400,'Сессия формы истекла. Обновите страницу.');
}
function csrf_field(): string { return '<input type="hidden" name="csrf_token" value="'.e(csrf()).'">'; }
function user(): ?array {
    static $loaded=false,$user=null;
    if (!$loaded) {
        $loaded=true;
        if (!empty($_SESSION['user_id']) && ($_SESSION['expires_at'] ?? 0)>time()) {
            $user=one('SELECT * FROM users WHERE id=?',[(int)$_SESSION['user_id']]);
            if (!$user || (int)$user['session_version']!==($_SESSION['version'] ?? 0)) $user=null;
        }
    }
    return $user;
}
function owner(): array { $u=user(); if (!$u || !$u['is_admin']) fail(403); return $u; }
function tier(): string {
    $u=user(); if ($u && $u['is_admin']) return 'appreciator';
    return $u && (config()['subscriptions_enabled'] ?? false) && (int)$u['tier_expires_at']>time() && isset(TIERS[$u['tier']]) ? $u['tier'] : 'free';
}
function required_tier(array $w): string { return $w['minimum_tier']==='free' && $w['access_type']==='subscriber' ? 'witness' : $w['minimum_tier']; }
function access(array $w, array $c): string {
    if (!$w['is_visible'] || !$w['published_at'] || $w['published_at']>time() || !$c['is_published'] || !$c['published_at'] || $c['published_at']>time()) return 'unpublished';
    if (user()['is_admin'] ?? false) return 'full';
    $required=required_tier($w);
    if (TIERS[tier()]<TIERS[$required]) return 'deny';
    if ($required!=='free' || tier()!=='free') return 'full';
    $access=$w['access_type']==='subscriber' ? 'subscriber' : $c['access_type'];
    return $access==='free' ? 'full' : ($access==='fragment' ? 'fragment' : 'deny');
}
function ip_hash(string $purpose): string { return hash_hmac('sha256',$purpose.':'.($_SERVER['REMOTE_ADDR'] ?? ''),config()['secret']); }
function voter_cookie(): string {
    $raw=$_COOKIE['arnett_voter']??'';
    if(is_string($raw) && preg_match('/^([a-f0-9]{64})\.([a-f0-9]{64})$/D',$raw,$m) && hash_equals(hash_hmac('sha256','voter:'.$m[1],config()['secret']),$m[2]))return $m[1];
    $id=bin2hex(random_bytes(32));$value=$id.'.'.hash_hmac('sha256','voter:'.$id,config()['secret']);
    setcookie('arnett_voter',$value,['expires'=>time()+31536000,'path'=>'/','secure'=>config()['production']??true,'httponly'=>true,'samesite'=>'Lax']);
    $_COOKIE['arnett_voter']=$value;return $id;
}
function rate(string $bucket, int $limit, int $seconds, ?string $subject=null): void {
    $subject ??= ip_hash('rate'); $window=(int)(floor(time()/$seconds)*$seconds);
    query('INSERT INTO rate_limits(bucket,subject,window,count) VALUES(?,?,?,1) ON CONFLICT(bucket,subject,window) DO UPDATE SET count=count+1',[$bucket,$subject,$window]);
    $row=one('SELECT count FROM rate_limits WHERE bucket=? AND subject=? AND window=?',[$bucket,$subject,$window]);
    if ((int)$row['count']>$limit) { header('Retry-After: '.max(1,$window+$seconds-time())); fail(429,'Подождите немного и попробуйте снова.'); }
}
function clean_html(string $body, string $format='html'): string {
    if ($format==='markdown') {
        $converter=new \League\CommonMark\CommonMarkConverter(['html_input'=>'strip','allow_unsafe_links'=>false,'max_nesting_level'=>30]);
        $body=(string)$converter->convert($body);
    }
    $config=\HTMLPurifier_Config::createDefault();
    $config->set('HTML.Allowed','p,br,em,strong,blockquote,h2,h3,h4,hr,ul,ol,li,a[href|title],sup,sub');
    $config->set('URI.AllowedSchemes',['https'=>true,'http'=>true]);
    $config->set('Cache.DefinitionImpl',null);
    $body=(new \HTMLPurifier($config))->purify($body);
    $i=0;
    return preg_replace_callback('/<(p|h2|h3|h4|blockquote)>/',function($m)use(&$i){return '<'.$m[1].' id="p-'.(++$i).'">';},$body);
}
function fragment(string $body, int $count): string {
    $doc=new \DOMDocument(); $old=libxml_use_internal_errors(true);
    $doc->loadHTML('<?xml encoding="UTF-8"><div id="fragment-root">'.$body.'</div>',LIBXML_HTML_NOIMPLIED|LIBXML_HTML_NODEFDTD);
    libxml_clear_errors();libxml_use_internal_errors($old);
    $html='';$i=0;foreach($doc->getElementById('fragment-root')->childNodes as $node) {
        if ($node instanceof \DOMElement && $i++ >= $count) break;
        $html.=$doc->saveHTML($node);
    }
    return $html;
}
function fingerprint(string $html, int $chapter): string {
    $id=bin2hex(random_bytes(16)); $signature=hash_hmac('sha256','receipt:'.$id,config()['secret']);
    query('INSERT INTO fingerprint_receipts(id,user_id,chapter_id,created_at) VALUES(?,?,?,?)',[$id,user()['id'],$chapter,time()]);
    $bits='';foreach(str_split(hex2bin($id.$signature)) as $char) $bits.=str_pad(decbin(ord($char)),8,'0',STR_PAD_LEFT);
    $invisible="\u{2063}".strtr($bits,['0'=>"\u{200b}",'1'=>"\u{200c}"])."\u{2063}";
    $marker='<span aria-hidden="true" class="receipt" data-receipt="'.$id.$signature.'">'.$invisible.'</span>';
    return str_contains($html,'</p>') ? preg_replace('~</p>~',$marker.'</p>',$html,1) : $html.$marker;
}
function start_http(): void {
    $c=config(); $production=$c['production'] ?? true;
    $host=parse_url($c['base_url'],PHP_URL_HOST);
    $actual=strtolower(explode(':',$_SERVER['HTTP_HOST'] ?? '')[0]);
    if (!in_array($actual,array_filter([$host,'www.'.$host,$production ? null : '127.0.0.1',$production ? null : 'localhost']),true)) { http_response_code(400); exit; }
    $secure=(!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS']!=='off') || ($_SERVER['SERVER_PORT'] ?? '')==='443';
    if ($production && !$secure) {
        if (($_SERVER['REQUEST_METHOD'] ?? 'GET')!=='GET' && ($_SERVER['REQUEST_METHOD'] ?? '')!=='HEAD') { http_response_code(400);exit; }
        redirect($c['base_url'].($_SERVER['REQUEST_URI'] ?? '/'),308);
    }
    header('Content-Type: text/html; charset=utf-8'); header('Cache-Control: private, no-store'); header('Vary: Cookie');
    header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'");
    header('X-Content-Type-Options: nosniff'); header('Referrer-Policy: no-referrer'); header('X-Frame-Options: DENY');
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
    if ($production) header('Strict-Transport-Security: max-age=31536000');
    ini_set('session.use_strict_mode','1'); ini_set('session.use_only_cookies','1');
    session_name('arnett_session');
    session_set_cookie_params(['lifetime'=>0,'path'=>'/','secure'=>$production,'httponly'=>true,'samesite'=>'Lax']);
    session_cache_limiter('');
    session_start();
    if (($_SERVER['CONTENT_LENGTH'] ?? 0)>2097152) fail(400,'Слишком большой запрос.');
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET')==='POST') check_csrf();
}
