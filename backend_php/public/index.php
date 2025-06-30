<?php

declare(strict_types=1);

require_once __DIR__ . '/../vendor/autoload.php';

use OrderFox\Application;

// Create and run the application
$application = new Application();
$application->run();