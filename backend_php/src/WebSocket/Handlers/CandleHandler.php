<?php

namespace App\WebSocket\Handlers;

use App\Core\Logger;
use App\Services\ConnectionManager;
use App\Services\SymbolService;
use Ratchet\ConnectionInterface;
use Ratchet\MessageComponentInterface;

class CandleHandler implements MessageComponentInterface
{
    private ConnectionManager $connectionManager;
    private Logger $logger;
    private SymbolService $symbolService;
    private array $validTimeframes = [
        '1m', '3m', '5m', '15m', '30m',
        '1h', '2h', '4h', '6h', '8h', '12h',
        '1d', '3d', '1w', '1M'
    ];

    public function __construct(ConnectionManager $connectionManager, Logger $logger)
    {
        $this->connectionManager = $connectionManager;
        $this->logger = $logger;
        $this->symbolService = new SymbolService();
    }

    public function onOpen(ConnectionInterface $conn, array $params = []): void
    {
        $symbol = $params['symbol'] ?? null;
        $timeframe = $params['timeframe'] ?? null;

        if (!$symbol) {
            $this->sendError($conn, "Symbol parameter is required");
            $conn->close();
            return;
        }

        if (!$timeframe) {
            $this->sendError($conn, "Timeframe parameter is required");
            $conn->close();
            return;
        }

        // Validate timeframe first
        if (!in_array($timeframe, $this->validTimeframes)) {
            $this->logger->warning("WebSocket candles invalid timeframe: {$timeframe}");
            $errorMsg = "Invalid timeframe. Valid options: " . implode(', ', $this->validTimeframes);
            $this->sendError($conn, $errorMsg);
            $conn->close();
            return;
        }

        $this->logger->info("WebSocket candles connection attempt for {$symbol}/{$timeframe} from {$conn->remoteAddress}");

        try {
            // Validate and convert symbol using symbol service
            $exchangeSymbol = $this->symbolService->resolveSymbolToExchangeFormat($symbol);
            if (!$exchangeSymbol) {
                // Get suggestions for invalid symbol
                $suggestions = $this->symbolService->getSymbolSuggestions($symbol);
                $errorMsg = "Symbol {$symbol} not found";
                if (!empty($suggestions)) {
                    $errorMsg .= ". Did you mean: " . implode(', ', array_slice($suggestions, 0, 3)) . "?";
                }

                $this->logger->warning("WebSocket candles error: {$errorMsg}");
                $this->sendError($conn, $errorMsg);
                $conn->close();
                return;
            }

            $this->logger->info("Using exchange symbol: {$exchangeSymbol} for WebSocket candles: {$symbol}/{$timeframe}");

            // Create stream key for this symbol:timeframe combination using exchange symbol
            $streamKey = "{$exchangeSymbol}:{$timeframe}";

            // Connect to the connection manager
            $this->connectionManager->connect($conn, $streamKey, 'candles', $symbol);
            $this->logger->info("WebSocket candles streaming started for {$symbol}/{$timeframe} (exchange: {$exchangeSymbol})");

            // Store connection info for cleanup
            $conn->orderFoxStreamKey = $streamKey;
            $conn->orderFoxSymbol = $symbol;
            $conn->orderFoxTimeframe = $timeframe;

        } catch (\Exception $e) {
            $this->logger->error("WebSocket candles error for {$symbol}/{$timeframe}: " . $e->getMessage());
            $this->sendError($conn, "Connection error: " . $e->getMessage());
            $conn->close();
        }
    }

    public function onMessage(ConnectionInterface $from, $msg): void
    {
        try {
            $data = json_decode($msg, true);
            
            if ($data === null) {
                $this->logger->warning("Invalid JSON received from candles client", [
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

            // Handle timeframe change requests
            if (isset($data['type']) && $data['type'] === 'change_timeframe' && isset($data['timeframe'])) {
                $this->handleTimeframeChange($from, $data['timeframe']);
                return;
            }

            // Candle handlers typically don't need to handle other message types
            // Just log for debugging
            $this->logger->debug("Received candles message", [
                'type' => $data['type'] ?? 'unknown',
                'resource_id' => $from->resourceId
            ]);

        } catch (\Exception $e) {
            $this->logger->error("Error processing candles message: " . $e->getMessage());
        }
    }

    public function onClose(ConnectionInterface $conn): void
    {
        $symbol = $conn->orderFoxSymbol ?? 'unknown';
        $timeframe = $conn->orderFoxTimeframe ?? 'unknown';

        $this->logger->info("WebSocket candles client disconnected for {$symbol}/{$timeframe}", [
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);

        // Clean up the connection
        if (isset($conn->orderFoxStreamKey)) {
            $this->connectionManager->disconnect($conn, $conn->orderFoxStreamKey);
        }
    }

    public function onError(ConnectionInterface $conn, \Exception $e): void
    {
        $symbol = $conn->orderFoxSymbol ?? 'unknown';
        $timeframe = $conn->orderFoxTimeframe ?? 'unknown';

        $this->logger->error("WebSocket candles error for {$symbol}/{$timeframe}", [
            'error' => $e->getMessage(),
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);
    }

    /**
     * Handle timeframe change requests
     */
    private function handleTimeframeChange(ConnectionInterface $conn, string $newTimeframe): void
    {
        try {
            if (!in_array($newTimeframe, $this->validTimeframes)) {
                $this->sendError($conn, "Invalid timeframe. Valid options: " . implode(', ', $this->validTimeframes));
                return;
            }

            $symbol = $conn->orderFoxSymbol ?? null;
            if (!$symbol) {
                $this->sendError($conn, "No symbol associated with connection");
                return;
            }

            $exchangeSymbol = $this->symbolService->resolveSymbolToExchangeFormat($symbol);
            if (!$exchangeSymbol) {
                $this->sendError($conn, "Invalid symbol");
                return;
            }

            // Disconnect from current stream
            if (isset($conn->orderFoxStreamKey)) {
                $this->connectionManager->disconnect($conn, $conn->orderFoxStreamKey);
            }

            // Create new stream key and connect
            $newStreamKey = "{$exchangeSymbol}:{$newTimeframe}";
            $this->connectionManager->connect($conn, $newStreamKey, 'candles', $symbol);

            // Update connection info
            $conn->orderFoxStreamKey = $newStreamKey;
            $conn->orderFoxTimeframe = $newTimeframe;

            $this->logger->info("Changed candles timeframe for {$symbol} to {$newTimeframe}");

            // Send confirmation
            $conn->send(json_encode([
                'type' => 'timeframe_changed',
                'symbol' => $symbol,
                'timeframe' => $newTimeframe
            ]));

        } catch (\Exception $e) {
            $this->logger->error("Error changing timeframe: " . $e->getMessage());
            $this->sendError($conn, "Failed to change timeframe");
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