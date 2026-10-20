<?php
// Copy to ../arnett-private/config.php, outside public_html. Never commit the copy.
return [
    'production' => true,
    'base_url' => 'https://danielarnett.com',
    'secret' => '', // At least 32 random bytes, e.g. bin2hex(random_bytes(32)).
    'subscriptions_enabled' => false,
    'fingerprints_enabled' => true,
    'audit_days' => 7,
];
