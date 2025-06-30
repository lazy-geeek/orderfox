<?php

namespace OrderFox\WebSocket\Handlers;

use Monolog\Logger as MonologLogger;
use OrderFox\Services\ConnectionManager;
use OrderFox\Services\SymbolService;
use Ratchet\ConnectionInterface;
use Ratchet\MessageComponentInterface;

class OrderBookHandler implements MessageComponentInterface
{
    private ConnectionManager $connectionManager;
    private MonologLogger $logger;
    private SymbolService $symbolService;

    public function __construct(ConnectionManager $connectionManager, MonologLogger $logger)
    {
        $this->connectionManager = $connectionManager;
        $this->logger = $logger;
        $this->symbolService = new SymbolService();
    }

    public function onOpen(ConnectionInterface $conn, array $params = []): void
    {
        $symbol = $params['symbol'] ?? null;
        $limit = $this->parseLimit($conn);

        if (!$symbol) {
            $this->sendError($conn, "Symbol parameter is required");
            $conn->close();
            return;
        }

        $this->logger->info("WebSocket orderbook connection attempt for {$symbol} from {$conn->remoteAddress}");

        try {
            // Validate and convert symbol using symbol service
            $exchangeSymbol = $this->symbolService->resolveSymbol($symbol);

            $this->logger->info("Using exchange symbol: {$exchangeSymbol} for WebSocket symbol: {$symbol}");

            // Validate and clamp limit parameter
            $limit = max(5, min($limit, 1000)); // Ensure limit is between 5 and 1000

            // Connect to the connection manager using the exchange symbol and limit
            $this->connectionManager->connectOrderbook($conn, $exchangeSymbol, $symbol, $limit);
            $this->logger->info("WebSocket orderbook streaming started for {$symbol} (exchange: {$exchangeSymbol})");

        } catch (\Exception $e) {
            $this->logger->error("WebSocket orderbook error for {$symbol}: " . $e->getMessage());
            $this->sendError($conn, "Connection error: " . $e->getMessage());
            $conn->close();
        }
    }

    public function onMessage(ConnectionInterface $from, $msg): void
    {
        try {
            $data = json_decode($msg, true);
            
            if ($data === null) {
                $this->logger->warning("Invalid JSON received from orderbook client", [
                    'message' => $msg,
                    'resource_id' => $from->resourceId
                ]);
                return;
            }

            // Handle ping messages
            if (isset($data['type']) && $data['type'] === 'ping') {
                $from->send(json_encode(['type' => 'pong']));
                return;
            }

            // Handle limit update messages
            if (isset($data['type']) && $data['type'] === 'update_limit' && isset($data['limit'])) {
                $this->handleLimitUpdate($from, (int)$data['limit']);
                return;
            }

        } catch (\Exception $e) {
            $this->logger->error("Error processing orderbook message: " . $e->getMessage());
        }
    }

    public function onClose(ConnectionInterface $conn): void
    {
        $this->logger->info("WebSocket orderbook client disconnected", [
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);

        // The connection manager will handle the cleanup
        if (isset($conn->orderFoxParams['symbol'])) {
            $symbol = $conn->orderFoxParams['symbol'];
            try {
                $exchangeSymbol = $this->symbolService->resolveSymbol($symbol);
                $this->connectionManager->disconnectOrderbook($conn, $exchangeSymbol);
            } catch (\Exception $e) {
                $this->logger->warning("Could not resolve symbol on close: " . $e->getMessage());
            }
        }
    }

    public function onError(ConnectionInterface $conn, \Exception $e): void
    {
        $this->logger->error("WebSocket orderbook error", [
            'error' => $e->getMessage(),
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);
    }

    /**
     * Parse limit parameter from WebSocket query string
     */
    private function parseLimit(ConnectionInterface $conn): int
    {
        $defaultLimit = 20;
        
        try {
            // Parse query string from WebSocket URI
            $uri = $conn->httpRequest->getUri();
            $query = $uri->getQuery();
            
            if (empty($query)) {
                return $defaultLimit;
            }

            parse_str($query, $params);
            
            if (!isset($params['limit'])) {
                return $defaultLimit;
            }

            $limit = (int)$params['limit'];
            
            // Validate limit range (5-5000 as per Python version)
            if ($limit < 5 || $limit > 5000) {
                $this->logger->warning("Invalid limit parameter: {$limit}, using default");
                return $defaultLimit;
            }

            return $limit;

        } catch (\Exception $e) {
            $this->logger->warning("Error parsing limit parameter: " . $e->getMessage());
            return $defaultLimit;
        }
    }

    /**
     * Handle limit update requests
     */
    private function handleLimitUpdate(ConnectionInterface $conn, int $newLimit): void
    {
        try {
            if (!isset($conn->orderFoxParams['symbol'])) {
                $this->sendError($conn, "No symbol associated with connection");
                return;
            }

            $symbol = $conn->orderFoxParams['symbol'];
            try {
                $exchangeSymbol = $this->symbolService->resolveSymbol($symbol);
            } catch (\Exception $e) {
                $this->sendError($conn, "Invalid symbol");
                return;
            }

            // Validate new limit
            $newLimit = max(5, min($newLimit, 5000));

            // Update the connection with new limit
            $this->connectionManager->connectOrderbook($conn, $exchangeSymbol, $symbol, $newLimit);
            
            $this->logger->info("Updated orderbook limit for {$symbol} to {$newLimit}");
            
            // Send confirmation
            $conn->send(json_encode([
                'type' => 'limit_updated',
                'symbol' => $symbol,
                'limit' => $newLimit
            ]));

        } catch (\Exception $e) {
            $this->logger->error("Error updating limit: " . $e->getMessage());
            $this->sendError($conn, "Failed to update limit");
        }
    }

    /**
     * Send error message to connection
     */
    private function sendError(ConnectionInterface $conn, string $message): void
    {
        $errorData = [
            'type' => 'error',
            'message' => $message
        ];

        try {
            $conn->send(json_encode($errorData));
        } catch (\Exception $e) {
            $this->logger->error("Failed to send error message: " . $e->getMessage());
        }
    }
}