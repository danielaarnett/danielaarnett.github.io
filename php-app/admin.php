<?php
declare(strict_types=1);
namespace Arnett;

function ticket_login(string $method): void {
    rate('ticket-login',10,60);
    $ticket=$method==='POST'?input('ticket',200):(string)($_GET['ticket']??'');
    if(!preg_match('/^[a-f0-9]{64}$/D',$ticket))fail(403);
    $row=one('SELECT t.user_id,u.session_version FROM login_tickets t JOIN users u ON u.id=t.user_id WHERE t.digest=? AND t.expires_at>?',[hash('sha256',$ticket),time()]);
    if(!$row)fail(403,'Ссылка входа истекла или уже использована.');
    if($method==='POST'){
        $result=query('DELETE FROM login_tickets WHERE digest=? AND expires_at>?',[hash('sha256',$ticket),time()]);if($result->rowCount()!==1)fail(403);
        $_SESSION=[];session_regenerate_id(true);$_SESSION['user_id']=(int)$row['user_id'];$_SESSION['version']=(int)$row['session_version'];$_SESSION['expires_at']=time()+43200;redirect('/admin');
    }
    page('Вход по одноразовой ссылке','<div class="narrow-panel"><h1>Вход в аккаунт</h1><form method="post">'.csrf_field().'<input type="hidden" name="ticket" value="'.e($ticket).'"><button class="button button-dark" type="submit">Войти</button></form></div>');
}

function login(string $method): void {
    $error='';$next=safe_next((string)($_POST['next']??$_GET['next']??'/admin'));
    if($method==='POST') {
        rate('login-minute',10,60);rate('login-hour',50,3600);
        $name=trim(is_string($_POST['username']??null)?$_POST['username']:'');
        $password=is_string($_POST['password']??null)?$_POST['password']:'';
        if(strlen($name)>120 || strlen($password)>1024)fail(400);
        $u=one('SELECT * FROM users WHERE username=?',[$name]);
        $dummy='$2y$12$2ncw9XJtJjFmJSdS0frhAu6e38jJ0gV8wsT3I4a4A/gQZ8m5CiPZi';
        $valid=password_verify($password,$u['password_hash']??$dummy);
        if($u && $valid) {
            if(password_needs_rehash($u['password_hash'],PASSWORD_DEFAULT))query('UPDATE users SET password_hash=? WHERE id=?',[password_hash($password,PASSWORD_DEFAULT),$u['id']]);
            $_SESSION=[];session_regenerate_id(true);
            $_SESSION['user_id']=(int)$u['id'];$_SESSION['version']=(int)$u['session_version'];$_SESSION['expires_at']=time()+43200;
            redirect($next);
        }
        $error='Неверное имя пользователя или пароль.';
    }
    page('Вход',view('login',compact('error','next')));
}
function input(string $key,int $max=240): string {
    $value=$_POST[$key]??'';if(!is_string($value)||mb_strlen($value)>$max)throw new \InvalidArgumentException('Проверьте длину заполненных полей.');return trim($value);
}
function choice(string $name,array $choices,string $default=''): string {
    $value=input($name);if($value==='' && $default!=='')return $default;
    if(!array_key_exists($value,$choices))throw new \InvalidArgumentException('Выберите значение из списка.');return $value;
}
function integer(string $key,int $max=100000,bool $nullable=false): ?int {
    $raw=input($key,12);if($nullable&&$raw==='')return null;
    if(!preg_match('/^[0-9]+$/D',$raw)||($v=(int)$raw)>$max)throw new \InvalidArgumentException('Укажите допустимое неотрицательное число.');return $v;
}
function posted_check(string $name): int { return isset($_POST[$name])?1:0; }
function save_work(?array $work): int {
    $data=[];foreach(['title','slug','subtitle','cover_path'] as $key)$data[$key]=input($key);
    if(!$data['title']||!slug_ok($data['slug'])||!cover_ok($data['cover_path']))throw new \InvalidArgumentException('Проверьте название, адрес произведения и путь к обложке.');
    $data['description']=input('description',10000);
    $data['shelf']=choice('shelf',SHELVES);$data['minimum_tier']=choice('minimum_tier',TIER_LABELS);
    $data['access_type']=choice('access_type',ACCESS_LABELS);$data['status']=choice('status',STATUS_LABELS);
    $data['sort_order']=integer('sort_order');$data['completion_percent']=integer('completion_percent',100,true);
    $data['is_visible']=posted_check('is_visible');$data['published_at']=$data['is_visible']?($work['published_at']??time()):null;$data['updated_at']=time();
    if($work){$sets=implode(',',array_map(fn($k)=>$k.'=?',array_keys($data)));query('UPDATE works SET '.$sets.' WHERE id=?',[...array_values($data),$work['id']]);return (int)$work['id'];}
    query('INSERT INTO works('.implode(',',array_keys($data)).') VALUES('.implode(',',array_fill(0,count($data),'?')).')',array_values($data));return (int)db()->lastInsertId();
}
function save_chapter(array $work,?array $chapter): int {
    $data=['title'=>input('title'),'slug'=>input('slug')];
    if(!$data['title']||!slug_ok($data['slug']))throw new \InvalidArgumentException('Укажите название и адрес главы латиницей.');
    $data['number']=integer('number');$data['sort_order']=integer('sort_order');
    $data['body_format']=choice('body_format',['html'=>'HTML','markdown'=>'Markdown']);
    $data['body']=input('body',700000);$data['fragment_body']=input('fragment_body',700000);
    if(!$data['body'])throw new \InvalidArgumentException('Укажите текст главы.');
    $blocks=integer('fragment_blocks',10000,true);
    if($blocks!==null && $blocks<1)throw new \InvalidArgumentException('Число блоков должно быть больше нуля.');
    $safe=clean_html($data['body'],$data['body_format']);
    if($blocks){$data['body']=$safe;$data['fragment_body']=fragment($safe,$blocks);$data['body_format']='html';}
    $data['access_type']=choice('access_type',ACCESS_LABELS);
    if($data['access_type']==='fragment' && !trim(strip_tags(clean_html($data['fragment_body'],$data['body_format']))))throw new \InvalidArgumentException('Укажите отдельный бесплатный фрагмент.');
    $data['is_published']=posted_check('is_published');$data['published_at']=$data['is_published']?($chapter['published_at']??time()):null;$data['word_count']=word_count($safe);
    if($chapter){$sets=implode(',',array_map(fn($k)=>$k.'=?',array_keys($data)));query('UPDATE chapters SET '.$sets.' WHERE id=? AND work_id=?',[...array_values($data),$chapter['id'],$work['id']]);return (int)$chapter['id'];}
    $data['work_id']=$work['id'];query('INSERT INTO chapters('.implode(',',array_keys($data)).') VALUES('.implode(',',array_fill(0,count($data),'?')).')',array_values($data));return (int)db()->lastInsertId();
}
function admin(string $path,string $method): void {
    owner();rate('admin',120,60,'user:'.user()['id']);
    if($path==='/admin') {
        $works=all('SELECT id,title,is_visible,status FROM works ORDER BY sort_order,id');page('Авторская панель',view('admin-dashboard',compact('works')));return;
    }
    if($path==='/admin/users'){users_admin($method);return;}
    if(preg_match('~^/admin/works/(new|([1-9][0-9]*)/edit)$~D',$path,$m)) {
        $work=isset($m[2])?one('SELECT * FROM works WHERE id=?',[(int)$m[2]]):null;
        if(isset($m[2])&&!$work)fail(404);$error='';
        if($method==='POST') {
            try{$id=save_work($work);$_SESSION['flash']='Произведение сохранено.';redirect('/admin/works/'.$id.'/edit');}
            catch(\InvalidArgumentException $e){$error=$e->getMessage();}
            catch(\PDOException $e){if($e->getCode()!=='23000')throw $e;$error='Такой адрес произведения уже используется.';}
        }
        $record=$method==='POST'?$_POST:($work??['shelf'=>'unfinished','minimum_tier'=>'free','access_type'=>'free','status'=>'draft','sort_order'=>0]);
        $chapters=$work?all('SELECT id,number,title,is_published FROM chapters WHERE work_id=? ORDER BY sort_order,number',[$work['id']]):[];
        page('Произведение',view('admin-work',compact('work','record','chapters','error')));return;
    }
    if(preg_match('~^/admin/works/([1-9][0-9]*)/chapters/(new|([1-9][0-9]*)/edit)$~D',$path,$m)) {
        $work=one('SELECT * FROM works WHERE id=?',[(int)$m[1]]);if(!$work)fail(404);
        $chapter=isset($m[3])?one('SELECT * FROM chapters WHERE id=? AND work_id=?',[(int)$m[3],$work['id']]):null;
        if(isset($m[3])&&!$chapter)fail(404);$error='';
        if($method==='POST') {
            try{$id=save_chapter($work,$chapter);$_SESSION['flash']='Глава сохранена.';redirect('/admin/works/'.$work['id'].'/chapters/'.$id.'/edit');}
            catch(\InvalidArgumentException $e){$error=$e->getMessage();}
            catch(\PDOException $e){if($e->getCode()!=='23000')throw $e;$error='Адрес или номер главы уже используется.';}
        }
        $record=$method==='POST'?$_POST:($chapter??['number'=>1,'sort_order'=>0,'body_format'=>'markdown','access_type'=>'free']);
        page('Глава',view('admin-chapter',compact('work','record','error')));return;
    }
    fail(404);
}
function users_admin(string $method): void {
    $error='';
    if($method==='POST') {
        try {
            $id=integer('id',2147483647);$tier=choice('tier',TIER_LABELS);$days=integer('days',366);
            $u=one('SELECT id,is_admin FROM users WHERE id=?',[$id]);if(!$u||$u['is_admin'])throw new \InvalidArgumentException('Выберите читательский аккаунт.');
            if($tier!=='free' && $days<1)throw new \InvalidArgumentException('Укажите срок доступа в днях.');
            query('UPDATE users SET tier=?,tier_expires_at=? WHERE id=?',[$tier,$tier==='free'?null:time()+$days*86400,$id]);
            $_SESSION['flash']='Доступ читателя обновлён.';redirect('/admin/users');
        }catch(\InvalidArgumentException $e){$error=$e->getMessage();}
    }
    $page=max(1,min(100000,(int)($_GET['page']??1)));$offset=($page-1)*30;
    $users=all('SELECT id,username,display_name,is_admin,tier,tier_expires_at FROM users ORDER BY id DESC LIMIT 31 OFFSET '.$offset);
    $next=count($users)>30;$users=array_slice($users,0,30);
    page('Читатели',view('admin-users',compact('users','page','next','error')));
}
