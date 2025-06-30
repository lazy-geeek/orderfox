<?php

require_once __DIR__ . '/vendor/autoload.php';

use App\Core\Config;
use App\Core\Logger;
use App\WebSocket\WebSocketServer;

// Initialize configuration and logging
try {
    $config = new Config();
    $logger = new Logger();
    
    $logger->info("Starting OrderFox WebSocket Server");
    
    // Get WebSocket port from environment or use default
    $port = (int)($config->get('WEBSOCKET_PORT') ?? 8080);
    
    $logger->info("WebSocket server will start on port: {$port}");
    
    // Start the WebSocket server
    WebSocketServer::start($port);
    
} catch (Exception $e) {
    echo "Failed to start WebSocket server: " . $e->getMessage() . "\n";
    exit(1);
}