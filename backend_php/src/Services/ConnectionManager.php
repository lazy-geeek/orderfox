<?php

declare(strict_types=1);

namespace OrderFox\Services;

use OrderFox\Core\Logger;
use OrderFox\Services\ExchangeService;
use Ratchet\ConnectionInterface;
use React\EventLoop\Loop;
use React\EventLoop\TimerInterface;

class ConnectionManager
{
    private \Monolog\Logger $logger;
    private ExchangeService $exchangeService;
    private array $activeConnections = [];
    private array $streamingTasks = [];
    private array $symbolActiveStreams = [];
    private array $streamKeyTypes = [];
    private array $displaySymbols = [];
    private array $streamLimits = [];
    private int $maxConnections = 5000;

    public function __construct()
    {
        $this->logger = Logger::getLogger('connection_manager');
        $this->exchangeService = new ExchangeService();
        $this->logger->info("ConnectionManager initialized");
    }

    /**
     * Connect a WebSocket client for a stream
     */
    public function connect(ConnectionInterface $websocket, string $streamKey, string $streamType = 'orderbook', ?string $displaySymbol = null): void
    {
        $this->logger->info("Connecting WebSocket for stream {$streamKey} (type: {$streamType})");

        // Store display symbol for response formatting
        if ($displaySymbol && !isset($this->displaySymbols[$streamKey])) {
            $this->displaySymbols[$streamKey] = $displaySymbol;
        }

        // Initialize connections array if needed
        if (!isset($this->activeConnections[$streamKey])) {
            $this->activeConnections[$streamKey] = [];
        }

        // Check connection limit
        if (count($this->activeConnections[$streamKey]) >= $this->maxConnections) {
            $this->logger->warning("Connection limit reached for stream {$streamKey}");
            $this->sendError($websocket, "Connection limit reached");
            return;
        }

        $this->activeConnections[$streamKey][] = $websocket;
        $this->streamKeyTypes[$streamKey] = $streamType;

        $connectionCount = count($this->activeConnections[$streamKey]);
        $this->logger->info("WebSocket connected to stream {$streamKey}. Total connections: {$connectionCount}");

        // Track active streams by base symbol
        $baseSymbol = $this->getBaseSymbolFromStreamKey($streamKey, $streamType);
        if ($baseSymbol) {
            if (!isset($this->symbolActiveStreams[$baseSymbol])) {
                $this->symbolActiveStreams[$baseSymbol] = [];
            }
            $this->symbolActiveStreams[$baseSymbol][] = $streamKey;
            $this->logger->debug("Active streams for {$baseSymbol}: " . implode(', ', $this->symbolActiveStreams[$baseSymbol]));
        }

        // Start streaming task if this is the first connection for this stream
        if ($connectionCount === 1) {
            $this->logger->info("Starting streaming task for {$streamKey}");
            $this->startStreaming($streamKey, $streamType);
        }
    }

    /**
     * Disconnect a WebSocket connection
     */
    public function disconnect(ConnectionInterface $websocket, string $streamKey): void
    {
        if (!isset($this->activeConnections[$streamKey])) {
            $this->logger->warning("Attempted to disconnect from non-existent stream: {$streamKey}");
            return;
        }

        $index = array_search($websocket, $this->activeConnections[$streamKey], true);
        if ($index !== false) {
            array_splice($this->activeConnections[$streamKey], $index, 1);
            $remainingConnections = count($this->activeConnections[$streamKey]);
            $this->logger->info("WebSocket disconnected from stream {$streamKey}. Remaining connections: {$remainingConnections}");

            // If no more connections, stop streaming and cleanup
            if ($remainingConnections === 0) {
                $this->logger->info("No more connections for stream_key: {$streamKey}. Stopping streaming task.");
                $this->stopStreaming($streamKey);

                $streamType = $this->streamKeyTypes[$streamKey] ?? null;
                unset($this->activeConnections[$streamKey]);

                $baseSymbol = null;
                if ($streamType) {
                    $baseSymbol = $this->getBaseSymbolFromStreamKey($streamKey, $streamType);
                }

                if ($baseSymbol && isset($this->symbolActiveStreams[$baseSymbol])) {
                    $streamIndex = array_search($streamKey, $this->symbolActiveStreams[$baseSymbol], true);
                    if ($streamIndex !== false) {
                        array_splice($this->symbolActiveStreams[$baseSymbol], $streamIndex, 1);
                    }
                    $this->logger->debug("Updated active streams for {$baseSymbol}: " . implode(', ', $this->symbolActiveStreams[$baseSymbol]));

                    // If no more streams for this symbol, cleanup completely
                    if (empty($this->symbolActiveStreams[$baseSymbol])) {
                        $this->logger->info("No more active streams for base_symbol {$baseSymbol}. Complete cleanup.");
                        unset($this->symbolActiveStreams[$baseSymbol]);

                        // Stop all related streaming tasks
                        foreach (array_keys($this->streamingTasks) as $taskKey) {
                            $taskType = $this->streamKeyTypes[$taskKey] ?? null;
                            if ($taskType) {
                                $taskBaseSymbol = $this->getBaseSymbolFromStreamKey($taskKey, $taskType);
                                if ($taskBaseSymbol === $baseSymbol) {
                                    $this->logger->debug("Stopping task {$taskKey} as part of {$baseSymbol} cleanup.");
                                    $this->stopStreaming($taskKey);
                                }
                            }
                        }

                        // Cleanup stream key types for this base symbol
                        foreach (array_keys($this->streamKeyTypes) as $key) {
                            $type = $this->streamKeyTypes[$key];
                            if ($this->getBaseSymbolFromStreamKey($key, $type) === $baseSymbol) {
                                unset($this->streamKeyTypes[$key]);
                            }
                        }
                    }
                }
            }
        }
    }

    /**
     * Connect orderbook (backward compatibility)
     */
    public function connectOrderbook(ConnectionInterface $websocket, string $symbol, ?string $displaySymbol = null, int $limit = 20): void
    {
        // Store the limit for this symbol stream
        $currentLimit = $this->streamLimits[$symbol] ?? null;
        if ($currentLimit !== $limit && isset($this->activeConnections[$symbol])) {
            $this->logger->info("Updating orderbook limit for {$symbol} from {$currentLimit} to {$limit}");
            $this->streamLimits[$symbol] = $limit;
            // Signal the streaming task to restart with new limit
            $this->restartOrderbookStream($symbol);
        } else {
            $this->streamLimits[$symbol] = $limit;
        }

        $this->connect($websocket, $symbol, 'orderbook', $displaySymbol);
    }

    /**
     * Disconnect orderbook (backward compatibility)
     */
    public function disconnectOrderbook(ConnectionInterface $websocket, string $symbol): void
    {
        $this->disconnect($websocket, $symbol);
    }

    /**
     * Broadcast data to all connections for a stream
     */
    public function broadcastToStream(string $streamKey, array $data): void
    {
        if (!isset($this->activeConnections[$streamKey])) {
            return;
        }

        $disconnected = [];
        foreach ($this->activeConnections[$streamKey] as $index => $connection) {
            try {
                $connection->send(json_encode($data));
            } catch (\Exception $e) {
                $this->logger->error("Error sending to connection on stream {$streamKey}: " . $e->getMessage());
                $disconnected[] = $index;
            }
        }

        // Remove disconnected connections
        foreach (array_reverse($disconnected) as $index) {
            $connection = $this->activeConnections[$streamKey][$index];
            $this->disconnect($connection, $streamKey);
        }
    }

    /**
     * Broadcast to symbol (backward compatibility)
     */
    public function broadcastToSymbol(string $symbol, array $data): void
    {
        $this->broadcastToStream($symbol, $data);
    }

    /**
     * Start streaming for a stream key
     */
    private function startStreaming(string $streamKey, string $streamType): void
    {
        if (isset($this->streamingTasks[$streamKey])) {
            $this->logger->warning("Streaming task for {$streamKey} already exists. Not starting a new one.");
            return;
        }

        $loop = Loop::get();

        switch ($streamType) {
            case 'orderbook':
                $this->streamingTasks[$streamKey] = $loop->addPeriodicTimer(1.0, function() use ($streamKey) {
                    $this->streamOrderbook($streamKey);
                });
                break;
            case 'ticker':
                // Extract symbol from stream_key (format: "SYMBOL:ticker" -> "SYMBOL")
                $symbol = str_replace(':ticker', '', $streamKey);
                $this->streamingTasks[$streamKey] = $loop->addPeriodicTimer(1.5, function() use ($symbol, $streamKey) {
                    $this->streamTicker($symbol, $streamKey);
                });
                break;
            case 'candles':
                $parts = explode(':', $streamKey);
                if (count($parts) >= 2) {
                    $symbol = implode(':', array_slice($parts, 0, -1));
                    $timeframe = end($parts);
                    $this->streamingTasks[$streamKey] = $loop->addPeriodicTimer(2.0, function() use ($symbol, $timeframe, $streamKey) {
                        $this->streamCandles($symbol, $timeframe, $streamKey);
                    });
                }
                break;
            default:
                $this->logger->error("Unknown stream type: {$streamType} for stream_key: {$streamKey}");
                return;
        }

        $this->logger->info("Successfully started streaming task for {$streamKey} (type: {$streamType})");
    }

    /**
     * Stop streaming for a stream key
     */
    private function stopStreaming(string $streamKey): void
    {
        if (isset($this->streamingTasks[$streamKey])) {
            $this->logger->info("Cancelling streaming task for {$streamKey}");
            try {
                $loop = Loop::get();
                $loop->cancelTimer($this->streamingTasks[$streamKey]);
            } catch (\Exception $e) {
                $this->logger->error("Error cancelling task for {$streamKey}: " . $e->getMessage());
            }
            unset($this->streamingTasks[$streamKey]);
        }
    }

    /**
     * Get base symbol from stream key
     */
    private function getBaseSymbolFromStreamKey(string $streamKey, ?string $streamType): ?string
    {
        if (!$streamType) {
            return null;
        }

        switch ($streamType) {
            case 'candles':
                $parts = explode(':', $streamKey);
                if (count($parts) >= 2) {
                    return implode(':', array_slice($parts, 0, -1));
                }
                break;
            case 'orderbook':
            case 'ticker':
                return $streamKey;
        }

        return null;
    }

    /**
     * Restart orderbook stream with updated limit
     */
    private function restartOrderbookStream(string $symbol): void
    {
        $this->logger->info("Restarting orderbook stream for {$symbol} with new limit");

        if (isset($this->streamingTasks[$symbol])) {
            $this->stopStreaming($symbol);
        }

        if (isset($this->activeConnections[$symbol]) && !empty($this->activeConnections[$symbol])) {
            $this->startStreaming($symbol, 'orderbook');
        }
    }

    /**
     * Stream orderbook data using CCXT
     */
    private function streamOrderbook(string $symbol): void
    {
        try {
            // Get the dynamic limit for this symbol, default to 20
            $limit = $this->streamLimits[$symbol] ?? 20;
            $limit = max(5, min($limit, 5000)); // Clamp limit

            // Fetch real orderbook data from exchange
            $orderBook = $this->exchangeService->fetchOrderBook($symbol, $limit);

            // Convert to our schema format
            $bids = [];
            $orderBookBids = $orderBook['bids'] ?? [];
            foreach (array_slice($orderBookBids, 0, $limit) as $bid) {
                $bids[] = [
                    'price' => (float)$bid[0],
                    'amount' => (float)$bid[1]
                ];
            }

            $asks = [];
            $orderBookAsks = $orderBook['asks'] ?? [];
            foreach (array_slice($orderBookAsks, 0, $limit) as $ask) {
                $asks[] = [
                    'price' => (float)$ask[0],
                    'amount' => (float)$ask[1]
                ];
            }

            $formattedData = [
                'type' => 'orderbook_update',
                'symbol' => $this->displaySymbols[$symbol] ?? $symbol,
                'bids' => $bids,
                'asks' => $asks,
                'timestamp' => $orderBook['timestamp'] ?? (time() * 1000)
            ];

            $this->broadcastToStream($symbol, $formattedData);

        } catch (\Exception $e) {
            $this->logger->error("Error streaming orderbook for {$symbol}: " . $e->getMessage());
            
            // Send error to clients
            $errorData = [
                'type' => 'error',
                'message' => "Error streaming orderbook for {$symbol}: " . $e->getMessage()
            ];
            $this->broadcastToStream($symbol, $errorData);
        }
    }

    /**
     * Stream ticker data using CCXT
     */
    private function streamTicker(string $symbol, string $streamKey): void
    {
        try {
            // Fetch real ticker data from exchange
            $ticker = $this->exchangeService->fetchTicker($symbol);

            // Convert to our schema format (matching Python API exactly)
            $formattedData = [
                'type' => 'ticker_update',
                'symbol' => $this->displaySymbols[$streamKey] ?? $symbol,
                'last' => isset($ticker['last']) && $ticker['last'] ? (float)$ticker['last'] : null,
                'bid' => isset($ticker['bid']) && $ticker['bid'] ? (float)$ticker['bid'] : null,
                'ask' => isset($ticker['ask']) && $ticker['ask'] ? (float)$ticker['ask'] : null,
                'high' => isset($ticker['high']) && $ticker['high'] ? (float)$ticker['high'] : null,
                'low' => isset($ticker['low']) && $ticker['low'] ? (float)$ticker['low'] : null,
                'open' => isset($ticker['open']) && $ticker['open'] ? (float)$ticker['open'] : null,
                'close' => isset($ticker['close']) && $ticker['close'] ? (float)$ticker['close'] : null,
                'change' => isset($ticker['change']) && $ticker['change'] ? (float)$ticker['change'] : null,
                'percentage' => isset($ticker['percentage']) && $ticker['percentage'] ? (float)$ticker['percentage'] : null,
                'volume' => isset($ticker['baseVolume']) && $ticker['baseVolume'] ? (float)$ticker['baseVolume'] : null,
                'quote_volume' => isset($ticker['quoteVolume']) && $ticker['quoteVolume'] ? (float)$ticker['quoteVolume'] : null,
                'timestamp' => $ticker['timestamp'] ?? (time() * 1000)
            ];

            $this->broadcastToStream($streamKey, $formattedData);

        } catch (\Exception $e) {
            $this->logger->error("Error streaming ticker for {$symbol}: " . $e->getMessage());
            
            // Send error to clients
            $errorData = [
                'type' => 'error',
                'message' => "Error streaming ticker for {$symbol}: " . $e->getMessage()
            ];
            $this->broadcastToStream($streamKey, $errorData);
        }
    }

    /**
     * Stream candle data using CCXT
     */
    private function streamCandles(string $symbol, string $timeframe, string $streamKey): void
    {
        try {
            // Fetch real OHLCV data from exchange
            $ohlcv = $this->exchangeService->fetchOHLCV($symbol, $timeframe, 1);

            // Get the latest candle
            if (!empty($ohlcv)) {
                $latestCandle = end($ohlcv);

                // Convert to our schema format (matching Python API exactly)
                $formattedData = [
                    'type' => 'candle_update',
                    'symbol' => $this->displaySymbols[$streamKey] ?? $symbol,
                    'timeframe' => $timeframe,
                    'timestamp' => $latestCandle['timestamp'],
                    'open' => (float)$latestCandle['open'],
                    'high' => (float)$latestCandle['high'],
                    'low' => (float)$latestCandle['low'],
                    'close' => (float)$latestCandle['close'],
                    'volume' => (float)$latestCandle['volume']
                ];

                $this->broadcastToStream($streamKey, $formattedData);
            }

        } catch (\Exception $e) {
            $this->logger->error("Error streaming candles for {$symbol} {$timeframe}: " . $e->getMessage());
            
            // Send error to clients
            $errorData = [
                'type' => 'error',
                'message' => "Error streaming candles for {$symbol} {$timeframe}: " . $e->getMessage()
            ];
            $this->broadcastToStream($streamKey, $errorData);
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