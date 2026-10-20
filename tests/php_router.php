<?php
// Test fixture only. This file is never included in the deployment archive.
declare(strict_types=1);
$_SERVER['REMOTE_ADDR']=$_SERVER['HTTP_X_TEST_REMOTE_ADDR']??'127.0.0.1';
putenv('ARNETT_APP_DIR='.dirname(__DIR__).'/php-app');
require dirname(__DIR__).'/php-public/index.php';
