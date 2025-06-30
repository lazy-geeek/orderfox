<?php

namespace OrderFox\WebSocket\Handlers;

use Monolog\Logger as MonologLogger;
use OrderFox\Services\ConnectionManager;
use OrderFox\Services\SymbolService;
use Ratchet\ConnectionInterface;
use Ratchet\MessageComponentInterface;

class TickerHandler implements MessageComponentInterface
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

        if (!$symbol) {
            $this->sendError($conn, "Symbol parameter is required");
            $conn->close();
            return;
        }

        $this->logger->info("WebSocket ticker connection attempt for {$symbol} from {$conn->remoteAddress}");

        try {
            // Validate and convert symbol using symbol service
            $exchangeSymbol = $this->symbolService->resolveSymbol($symbol);

            $this->logger->info("Using exchange symbol: {$exchangeSymbol} for WebSocket ticker: {$symbol}");

            // Connect to the connection manager using unique ticker stream key
            $tickerStreamKey = "{$exchangeSymbol}:ticker";
            $this->connectionManager->connect($conn, $tickerStreamKey, 'ticker', $symbol);
            $this->logger->info("WebSocket ticker streaming started for {$symbol} (exchange: {$exchangeSymbol})");

            // Store connection info for cleanup
            $conn->orderFoxStreamKey = $tickerStreamKey;
            $conn->orderFoxExchangeSymbol = $exchangeSymbol;

        } catch (\Exception $e) {
            $this->logger->error("WebSocket ticker error for {$symbol}: " . $e->getMessage());
            $this->sendError($conn, "Connection error: " . $e->getMessage());
            $conn->close();
        }
    }

    public function onMessage(ConnectionInterface $from, $msg): void
    {
        try {
            $data = json_decode($msg, true);
            
            if ($data === null) {
                $this->logger->warning("Invalid JSON received from ticker client", [
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

            // Ticker handlers typically don't need to handle other message types
            // Just log for debugging
            $this->logger->debug("Received ticker message", [
                'type' => $data['type'] ?? 'unknown',
                'resource_id' => $from->resourceId
            ]);

        } catch (\Exception $e) {
            $this->logger->error("Error processing ticker message: " . $e->getMessage());
        }
    }

    public function onClose(ConnectionInterface $conn): void
    {
        $this->logger->info("WebSocket ticker client disconnected", [
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);

        // Clean up the connection
        if (isset($conn->orderFoxStreamKey)) {
            $this->connectionManager->disconnect($conn, $conn->orderFoxStreamKey);
        } elseif (isset($conn->orderFoxExchangeSymbol)) {
            // Fallback if stream key is not available
            $this->connectionManager->disconnect($conn, $conn->orderFoxExchangeSymbol);
        }
    }

    public function onError(ConnectionInterface $conn, \Exception $e): void
    {
        $this->logger->error("WebSocket ticker error", [
            'error' => $e->getMessage(),
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);
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