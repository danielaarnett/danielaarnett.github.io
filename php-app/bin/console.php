<?php
declare(strict_types=1);
namespace Arnett;
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require dirname(__DIR__).'/bootstrap.php';require dirname(__DIR__).'/content.php';
$command=$argv[1]??'help';
try {
    if($command==='init') {config();db();seed();echo "Database ready.\n";exit;}
    if($command==='user:add') {
        $name=$argv[2]??'';$admin=in_array('--admin',$argv,true);
        if(!preg_match('/^[a-z0-9_.@-]{3,120}$/iD',$name))throw new \RuntimeException('Choose a username of 3–120 Latin characters.');
        if(!in_array('--password-stdin',$argv,true))throw new \RuntimeException('Pass --password-stdin and provide the password through standard input.');
        $password=rtrim(stream_get_contents(STDIN),"\r\n");
        if(strlen($password)<16 || strlen($password)>1024)throw new \RuntimeException('Use a password of at least 16 characters.');
        query('INSERT INTO users(username,display_name,password_hash,is_admin,created_at) VALUES(?,?,?,?,?)',[$name,$name,password_hash($password,PASSWORD_DEFAULT),(int)$admin,time()]);
        echo "Account created.\n";exit;
    }
    if($command==='ticket') {
        $name=$argv[2]??'';$u=one('SELECT id FROM users WHERE username=?',[$name]);if(!$u)throw new \RuntimeException('Unknown account.');
        $ticket=bin2hex(random_bytes(32));query('INSERT INTO login_tickets(digest,user_id,expires_at) VALUES(?,?,?)',[hash('sha256',$ticket),$u['id'],time()+600]);
        echo config()['base_url'].'/auth/ticket?ticket='.$ticket."\n";exit;
    }
    if($command==='prune') {
        $cutoff=time()-max(1,(int)(config()['audit_days']??7))*86400;
        query('DELETE FROM read_audit WHERE created_at<?',[$cutoff]);query('DELETE FROM fingerprint_receipts WHERE created_at<?',[$cutoff]);
        query('DELETE FROM rate_limits WHERE window<?',[time()-172800]);query('DELETE FROM login_tickets WHERE expires_at<?',[time()]);
        echo "Old records removed.\n";exit;
    }
    if($command==='trace') {
        $text=file_get_contents($argv[2]??'');$token='';
        if(preg_match('/data-receipt="([a-f0-9]{96})"/',$text,$m))$token=$m[1];
        elseif(preg_match('/\x{2063}([\x{200b}\x{200c}]{384})\x{2063}/u',$text,$m)){
            $bits=strtr($m[1],["\u{200b}"=>'0',"\u{200c}"=>'1']);foreach(str_split($bits,8)as$byte)$token.=str_pad(dechex(bindec($byte)),2,'0',STR_PAD_LEFT);
        }
        if(strlen($token)!==96 || !hash_equals(hash_hmac('sha256','receipt:'.substr($token,0,32),config()['secret']),substr($token,32)))throw new \RuntimeException('No valid receipt found.');
        $row=one('SELECT user_id,chapter_id,created_at FROM fingerprint_receipts WHERE id=?',[substr($token,0,32)]);
        echo json_encode($row,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n";exit;
    }
    echo "Commands: init; user:add USERNAME --admin --password-stdin; ticket USERNAME; prune; trace FILE\n";
}catch(\Throwable $e){fwrite(STDERR,$e->getMessage()."\n");exit(1);}
