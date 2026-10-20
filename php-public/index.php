<?php
declare(strict_types=1);
// Application, dependency source and database live outside public_html.
try {
    $app=getenv('ARNETT_APP_DIR') ?: dirname(__DIR__).'/arnett-app';
    require $app.'/bootstrap.php';
    require $app.'/routes.php';
    \Arnett\dispatch();
} catch (Throwable $error) {
    error_log('Arnett application failure: '.get_class($error));
    http_response_code(503);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');
    echo '<!doctype html><html lang="ru"><meta charset="utf-8"><title>Сайт временно недоступен</title><h1>Сайт временно недоступен</h1><p>Попробуйте открыть страницу немного позже.</p></html>';
}
