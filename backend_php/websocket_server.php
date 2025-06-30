<?php

require_once __DIR__ . '/vendor/autoload.php';

use OrderFox\Core\Config;
use OrderFox\Core\Logger;
use OrderFox\WebSocket\WebSocketServer;

// Initialize configuration and logging
try {
    $config = Config::getInstance();
    $logger = Logger::setup();
    
    $logger->info("Starting OrderFox WebSocket Server");
    
    // Get WebSocket port from environment or use default
    $port = (int)($_ENV['WEBSOCKET_PORT'] ?? 8080);
    
    $logger->info("WebSocket server will start on port: {$port}");
    
    // Start the WebSocket server
    WebSocketServer::start($port);
    
} catch (Exception $e) {
    echo "Failed to start WebSocket server: " . $e->getMessage() . "\n";
    exit(1);
}