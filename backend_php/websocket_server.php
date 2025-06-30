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
    
    // Get WebSocket host and port from config (which handles container vs local environment)
    $host = $config->websocketHost;
    $port = $config->websocketPort;
    
    $logger->info("WebSocket server will start on {$host}:{$port}");
    
    // Start the WebSocket server
    WebSocketServer::start($port, $host);
    
} catch (Exception $e) {
    echo "Failed to start WebSocket server: " . $e->getMessage() . "\n";
    exit(1);
}