<?php

declare(strict_types=1);

namespace Tests\Integration\WebSocket;

use OrderFox\Core\Logger;
use OrderFox\Services\ConnectionManager;
use OrderFox\Services\ExchangeService;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Ratchet\ConnectionInterface;
use React\EventLoop\Loop;
use React\Socket\SocketServer;
use React\Socket\ConnectionInterface as SocketConnectionInterface;

class WebSocketConnectionTest extends TestCase
{
    private ConnectionManager $connectionManager;
    private MockObject $mockConnection;
    private ExchangeService $exchangeService;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Set up test environment
        $_ENV['APP_ENV'] = 'testing';
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        $_ENV['PAPER_TRADING'] = 'true';
        
        // Reset logger for clean test state
        Logger::reset();
        
        // Create real connection manager
        $this->connectionManager = new ConnectionManager();
        
        // Create mock WebSocket connection
        $this->mockConnection = $this->createMock(ConnectionInterface::class);
        
        // Initialize exchange service for integration testing
        $this->exchangeService = new ExchangeService();
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    public function testWebSocketConnectionEstablishment(): void
    {
        $symbol = 'BTC/USDT';
        $streamType = 'orderbook';
        
        // Test connection establishment
        $this->connectionManager->connect($this->mockConnection, $symbol, $streamType);
        
        // Verify connection was established by checking internal state
        $reflection = new \ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertArrayHasKey($symbol, $connections);
        $this->assertContains($this->mockConnection, $connections[$symbol]);
    }

    public function testWebSocketConnectionDisconnection(): void
    {
        $symbol = 'BTC/USDT';
        $streamType = 'orderbook';
        
        // Connect first
        $this->connectionManager->connect($this->mockConnection, $symbol, $streamType);
        
        // Then disconnect
        $this->connectionManager->disconnect($this->mockConnection, $symbol);
        
        // Verify connection was removed
        $reflection = new \ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertArrayNotHasKey($symbol, $connections);
    }

    public function testMultipleWebSocketConnections(): void
    {
        $symbol = 'BTC/USDT';
        $streamType = 'orderbook';
        
        // Create multiple mock connections
        $connection1 = $this->createMock(ConnectionInterface::class);
        $connection2 = $this->createMock(ConnectionInterface::class);
        $connection3 = $this->createMock(ConnectionInterface::class);
        
        // Connect all three
        $this->connectionManager->connect($connection1, $symbol, $streamType);
        $this->connectionManager->connect($connection2, $symbol, $streamType);
        $this->connectionManager->connect($connection3, $symbol, $streamType);
        
        // Verify all connections are tracked
        $reflection = new \ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertCount(3, $connections[$symbol]);
        $this->assertContains($connection1, $connections[$symbol]);
        $this->assertContains($connection2, $connections[$symbol]);
        $this->assertContains($connection3, $connections[$symbol]);
    }

    public function testWebSocketConnectionLimit(): void
    {
        $symbol = 'BTC/USDT';
        $streamType = 'orderbook';
        
        // Set connection limit to 2 for testing
        $reflection = new \ReflectionClass($this->connectionManager);
        $maxProperty = $reflection->getProperty('maxConnections');
        $maxProperty->setAccessible(true);
        $maxProperty->setValue($this->connectionManager, 2);
        
        // Create mock connections
        $connection1 = $this->createMock(ConnectionInterface::class);
        $connection2 = $this->createMock(ConnectionInterface::class);
        $connection3 = $this->createMock(ConnectionInterface::class);
        
        // Connection 3 should receive error message when limit is reached
        $connection3->expects($this->once())
            ->method('send')
            ->with($this->stringContains('Connection limit reached'));
        
        // Connect first two successfully
        $this->connectionManager->connect($connection1, $symbol, $streamType);
        $this->connectionManager->connect($connection2, $symbol, $streamType);
        
        // Third connection should be rejected
        $this->connectionManager->connect($connection3, $symbol, $streamType);
        
        // Verify only 2 connections exist
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertCount(2, $connections[$symbol]);
    }

    public function testWebSocketOrderbookStreaming(): void
    {
        $symbol = 'BTC/USDT';
        $limit = 20;
        
        // Mock connection expects to receive orderbook update
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'orderbook_update' &&
                       isset($decoded['symbol']) &&
                       isset($decoded['bids']) &&
                       isset($decoded['asks']) &&
                       isset($decoded['timestamp']);
            }));
        
        // Connect to orderbook stream
        $this->connectionManager->connectOrderbook($this->mockConnection, $symbol, $symbol, $limit);
        
        // Simulate streaming by calling the private method
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        
        // This should trigger the mock expectation
        $streamMethod->invoke($this->connectionManager, $symbol);
    }

    public function testWebSocketTickerStreaming(): void
    {
        $symbol = 'BTC/USDT';
        $streamKey = 'BTC/USDT:ticker';
        
        // Mock connection expects to receive ticker update
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'ticker_update' &&
                       isset($decoded['symbol']) &&
                       isset($decoded['last']) &&
                       isset($decoded['timestamp']);
            }));
        
        // Connect to ticker stream
        $this->connectionManager->connect($this->mockConnection, $streamKey, 'ticker');
        
        // Simulate streaming by calling the private method
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamTicker');
        $streamMethod->setAccessible(true);
        
        // This should trigger the mock expectation
        $streamMethod->invoke($this->connectionManager, $symbol, $streamKey);
    }

    public function testWebSocketCandleStreaming(): void
    {
        $symbol = 'BTC/USDT';
        $timeframe = '1h';
        $streamKey = 'BTC/USDT:1h';
        
        // Mock connection expects to receive candle update
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'candle_update' &&
                       isset($decoded['symbol']) &&
                       isset($decoded['timeframe']) &&
                       isset($decoded['open']) &&
                       isset($decoded['high']) &&
                       isset($decoded['low']) &&
                       isset($decoded['close']) &&
                       isset($decoded['volume']) &&
                       isset($decoded['timestamp']);
            }));
        
        // Connect to candle stream
        $this->connectionManager->connect($this->mockConnection, $streamKey, 'candles');
        
        // Simulate streaming by calling the private method
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamCandles');
        $streamMethod->setAccessible(true);
        
        // This should trigger the mock expectation
        $streamMethod->invoke($this->connectionManager, $symbol, $timeframe, $streamKey);
    }

    public function testWebSocketErrorHandling(): void
    {
        $symbol = 'INVALID/SYMBOL';
        
        // Mock connection expects to receive error message
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'error' &&
                       isset($decoded['message']);
            }));
        
        // Connect to stream with invalid symbol
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        
        // Simulate streaming with invalid symbol (should trigger error)
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        
        // This should trigger error handling and mock expectation
        $streamMethod->invoke($this->connectionManager, $symbol);
    }

    public function testWebSocketBroadcastToMultipleConnections(): void
    {
        $symbol = 'BTC/USDT';
        $data = [
            'type' => 'test_broadcast',
            'symbol' => $symbol,
            'data' => 'test message'
        ];
        
        // Create multiple mock connections
        $connection1 = $this->createMock(ConnectionInterface::class);
        $connection2 = $this->createMock(ConnectionInterface::class);
        $connection3 = $this->createMock(ConnectionInterface::class);
        
        // All connections should receive the broadcast
        $connection1->expects($this->once())
            ->method('send')
            ->with(json_encode($data));
        
        $connection2->expects($this->once())
            ->method('send')
            ->with(json_encode($data));
        
        $connection3->expects($this->once())
            ->method('send')
            ->with(json_encode($data));
        
        // Connect all three
        $this->connectionManager->connect($connection1, $symbol, 'orderbook');
        $this->connectionManager->connect($connection2, $symbol, 'orderbook');
        $this->connectionManager->connect($connection3, $symbol, 'orderbook');
        
        // Broadcast message
        $this->connectionManager->broadcastToStream($symbol, $data);
    }

    public function testWebSocketConnectionCleanupOnError(): void
    {
        $symbol = 'BTC/USDT';
        $data = ['type' => 'test'];
        
        // Create connection that throws exception on send
        $faultyConnection = $this->createMock(ConnectionInterface::class);
        $faultyConnection->method('send')
            ->willThrowException(new \Exception('Connection closed'));
        
        // Connect the faulty connection
        $this->connectionManager->connect($faultyConnection, $symbol, 'orderbook');
        
        // Broadcasting should handle the error gracefully
        $this->connectionManager->broadcastToStream($symbol, $data);
        
        // Connection should be automatically cleaned up
        $reflection = new \ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        // Since the faulty connection should be removed, the stream should be empty
        $this->assertArrayNotHasKey($symbol, $connections);
    }

    public function testWebSocketStreamTypeTracking(): void
    {
        $orderbookKey = 'BTC/USDT';
        $tickerKey = 'ETH/USDT:ticker';
        $candleKey = 'LTC/USDT:1h';
        
        $this->connectionManager->connect($this->mockConnection, $orderbookKey, 'orderbook');
        $this->connectionManager->connect($this->mockConnection, $tickerKey, 'ticker');
        $this->connectionManager->connect($this->mockConnection, $candleKey, 'candles');
        
        $reflection = new \ReflectionClass($this->connectionManager);
        $typesProperty = $reflection->getProperty('streamKeyTypes');
        $typesProperty->setAccessible(true);
        $types = $typesProperty->getValue($this->connectionManager);
        
        $this->assertEquals('orderbook', $types[$orderbookKey]);
        $this->assertEquals('ticker', $types[$tickerKey]);
        $this->assertEquals('candles', $types[$candleKey]);
    }

    public function testWebSocketLimitUpdates(): void
    {
        $symbol = 'BTC/USDT';
        $initialLimit = 20;
        $newLimit = 50;
        
        // Connect with initial limit
        $this->connectionManager->connectOrderbook($this->mockConnection, $symbol, $symbol, $initialLimit);
        
        // Connect again with different limit (should trigger restart)
        $connection2 = $this->createMock(ConnectionInterface::class);
        $this->connectionManager->connectOrderbook($connection2, $symbol, $symbol, $newLimit);
        
        // Verify new limit is stored
        $reflection = new \ReflectionClass($this->connectionManager);
        $limitsProperty = $reflection->getProperty('streamLimits');
        $limitsProperty->setAccessible(true);
        $limits = $limitsProperty->getValue($this->connectionManager);
        
        $this->assertEquals($newLimit, $limits[$symbol]);
    }
}