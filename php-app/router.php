<?php
// Development router for PHP's built-in server; not included in hosting bundles.
declare(strict_types=1);
$root=dirname(__DIR__);
$path=rawurldecode(parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH) ?: '/');
$file=realpath($root.$path);
if($file && str_starts_with($file,$root.DIRECTORY_SEPARATOR) && is_file($file) && (preg_match('~^/(css|js|fonts|images)/~',$path) || in_array($path,['/reading.css','/static-texture.webp'],true)))return false;
putenv('ARNETT_APP_DIR='.__DIR__);
require $root.'/php-public/index.php';
