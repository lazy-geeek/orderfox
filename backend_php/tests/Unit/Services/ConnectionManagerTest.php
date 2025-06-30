<?php

declare(strict_types=1);

namespace Tests\Unit\Services;

use OrderFox\Services\ConnectionManager;
use OrderFox\Services\ExchangeService;
use OrderFox\Core\Logger;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Ratchet\ConnectionInterface;
use ReflectionClass;

class ConnectionManagerTest extends TestCase
{
    private ConnectionManager $connectionManager;
    private MockObject $mockConnection;
    private MockObject $mockExchangeService;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Reset logger for clean test state
        Logger::reset();
        
        // Create mock connection interface
        $this->mockConnection = $this->createMock(ConnectionInterface::class);
        
        // Create mock exchange service
        $this->mockExchangeService = $this->createMock(ExchangeService::class);
        
        // Create connection manager
        $this->connectionManager = new ConnectionManager();
        
        // Replace exchange service with mock using reflection
        $reflection = new ReflectionClass($this->connectionManager);
        $exchangeProperty = $reflection->getProperty('exchangeService');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($this->connectionManager, $this->mockExchangeService);
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    public function testConstructorInitializesCorrectly(): void
    {
        $manager = new ConnectionManager();
        
        $this->assertInstanceOf(ConnectionManager::class, $manager);
    }

    public function testConnectAddsConnectionToStream(): void
    {
        $streamKey = 'BTC/USDT';
        $streamType = 'orderbook';
        
        $this->connectionManager->connect($this->mockConnection, $streamKey, $streamType);
        
        // Use reflection to check internal state
        $reflection = new ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertArrayHasKey($streamKey, $connections);
        $this->assertContains($this->mockConnection, $connections[$streamKey]);
    }

    public function testConnectStoresStreamType(): void
    {
        $streamKey = 'BTC/USDT';
        $streamType = 'ticker';
        
        $this->connectionManager->connect($this->mockConnection, $streamKey, $streamType);
        
        $reflection = new ReflectionClass($this->connectionManager);
        $typesProperty = $reflection->getProperty('streamKeyTypes');
        $typesProperty->setAccessible(true);
        $types = $typesProperty->getValue($this->connectionManager);
        
        $this->assertArrayHasKey($streamKey, $types);
        $this->assertEquals($streamType, $types[$streamKey]);
    }

    public function testConnectStoresDisplaySymbol(): void
    {
        $streamKey = 'BTC/USDT';
        $streamType = 'orderbook';
        $displaySymbol = 'Bitcoin/Tether';
        
        $this->connectionManager->connect($this->mockConnection, $streamKey, $streamType, $displaySymbol);
        
        $reflection = new ReflectionClass($this->connectionManager);
        $symbolsProperty = $reflection->getProperty('displaySymbols');
        $symbolsProperty->setAccessible(true);
        $symbols = $symbolsProperty->getValue($this->connectionManager);
        
        $this->assertArrayHasKey($streamKey, $symbols);
        $this->assertEquals($displaySymbol, $symbols[$streamKey]);
    }

    public function testConnectRejectsWhenConnectionLimitReached(): void
    {
        $streamKey = 'BTC/USDT';
        $streamType = 'orderbook';
        
        // Set max connections to 1 for testing
        $reflection = new ReflectionClass($this->connectionManager);
        $maxProperty = $reflection->getProperty('maxConnections');
        $maxProperty->setAccessible(true);
        $maxProperty->setValue($this->connectionManager, 1);
        
        // Add first connection
        $this->connectionManager->connect($this->mockConnection, $streamKey, $streamType);
        
        // Create second connection mock
        $secondConnection = $this->createMock(ConnectionInterface::class);
        $secondConnection->expects($this->once())
            ->method('send')
            ->with($this->stringContains('Connection limit reached'));
        
        // Try to add second connection - should be rejected
        $this->connectionManager->connect($secondConnection, $streamKey, $streamType);
        
        // Check that only one connection exists
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertCount(1, $connections[$streamKey]);
    }

    public function testDisconnectRemovesConnection(): void
    {
        $streamKey = 'BTC/USDT';
        $streamType = 'orderbook';
        
        // Connect first
        $this->connectionManager->connect($this->mockConnection, $streamKey, $streamType);
        
        // Then disconnect
        $this->connectionManager->disconnect($this->mockConnection, $streamKey);
        
        $reflection = new ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        // Stream key should be removed when no connections remain
        $this->assertArrayNotHasKey($streamKey, $connections);
    }

    public function testDisconnectFromNonExistentStreamLogsWarning(): void
    {
        // This should not throw an exception, just log a warning
        $this->connectionManager->disconnect($this->mockConnection, 'NONEXISTENT');
        
        // Test passes if no exception is thrown
        $this->assertTrue(true);
    }

    public function testConnectOrderbookBackwardCompatibility(): void
    {
        $symbol = 'BTC/USDT';
        $displaySymbol = 'Bitcoin/Tether';
        $limit = 50;
        
        $this->connectionManager->connectOrderbook($this->mockConnection, $symbol, $displaySymbol, $limit);
        
        $reflection = new ReflectionClass($this->connectionManager);
        
        // Check connections
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        $this->assertArrayHasKey($symbol, $connections);
        
        // Check limits
        $limitsProperty = $reflection->getProperty('streamLimits');
        $limitsProperty->setAccessible(true);
        $limits = $limitsProperty->getValue($this->connectionManager);
        $this->assertEquals($limit, $limits[$symbol]);
    }

    public function testDisconnectOrderbookBackwardCompatibility(): void
    {
        $symbol = 'BTC/USDT';
        
        // Connect first
        $this->connectionManager->connectOrderbook($this->mockConnection, $symbol);
        
        // Then disconnect
        $this->connectionManager->disconnectOrderbook($this->mockConnection, $symbol);
        
        $reflection = new ReflectionClass($this->connectionManager);
        $connectionsProperty = $reflection->getProperty('activeConnections');
        $connectionsProperty->setAccessible(true);
        $connections = $connectionsProperty->getValue($this->connectionManager);
        
        $this->assertArrayNotHasKey($symbol, $connections);
    }

    public function testBroadcastToStreamSendsToAllConnections(): void
    {
        $streamKey = 'BTC/USDT';
        $data = ['type' => 'test', 'message' => 'hello'];
        
        // Create multiple mock connections
        $connection1 = $this->createMock(ConnectionInterface::class);
        $connection2 = $this->createMock(ConnectionInterface::class);
        
        $connection1->expects($this->once())
            ->method('send')
            ->with(json_encode($data));
        
        $connection2->expects($this->once())
            ->method('send')
            ->with(json_encode($data));
        
        // Connect both
        $this->connectionManager->connect($connection1, $streamKey, 'orderbook');
        $this->connectionManager->connect($connection2, $streamKey, 'orderbook');
        
        // Broadcast
        $this->connectionManager->broadcastToStream($streamKey, $data);
    }

    public function testBroadcastToStreamHandlesConnectionErrors(): void
    {
        $streamKey = 'BTC/USDT';
        $data = ['type' => 'test'];
        
        // Create connection that throws exception
        $badConnection = $this->createMock(ConnectionInterface::class);
        $badConnection->method('send')
            ->willThrowException(new \Exception('Connection closed'));
        
        $this->connectionManager->connect($badConnection, $streamKey, 'orderbook');
        
        // This should not throw an exception
        $this->connectionManager->broadcastToStream($streamKey, $data);
        
        $this->assertTrue(true);
    }

    public function testBroadcastToSymbolBackwardCompatibility(): void
    {
        $symbol = 'BTC/USDT';
        $data = ['type' => 'test'];
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with(json_encode($data));
        
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        $this->connectionManager->broadcastToSymbol($symbol, $data);
    }

    public function testGetBaseSymbolFromStreamKeyForOrderbook(): void
    {
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('getBaseSymbolFromStreamKey');
        $method->setAccessible(true);
        
        $result = $method->invoke($this->connectionManager, 'BTC/USDT', 'orderbook');
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testGetBaseSymbolFromStreamKeyForTicker(): void
    {
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('getBaseSymbolFromStreamKey');
        $method->setAccessible(true);
        
        $result = $method->invoke($this->connectionManager, 'BTC/USDT:ticker', 'ticker');
        $this->assertEquals('BTC/USDT:ticker', $result);
    }

    public function testGetBaseSymbolFromStreamKeyForCandles(): void
    {
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('getBaseSymbolFromStreamKey');
        $method->setAccessible(true);
        
        $result = $method->invoke($this->connectionManager, 'BTC/USDT:1h', 'candles');
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testGetBaseSymbolFromStreamKeyReturnsNullForInvalidType(): void
    {
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('getBaseSymbolFromStreamKey');
        $method->setAccessible(true);
        
        $result = $method->invoke($this->connectionManager, 'BTC/USDT', null);
        $this->assertNull($result);
    }

    public function testStreamOrderbookFetchesAndFormatsData(): void
    {
        $symbol = 'BTC/USDT';
        
        // Mock orderbook data
        $mockOrderBook = [
            'timestamp' => 1640995200000,
            'bids' => [[49000.0, 1.5], [48900.0, 2.0]],
            'asks' => [[49100.0, 1.2], [49200.0, 1.8]]
        ];
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOrderBook')
            ->with($symbol, 20)
            ->willReturn($mockOrderBook);
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'orderbook_update' &&
                       $decoded['symbol'] === 'BTC/USDT' &&
                       count($decoded['bids']) === 2 &&
                       count($decoded['asks']) === 2;
            }));
        
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        
        // Use reflection to call private method
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('streamOrderbook');
        $method->setAccessible(true);
        $method->invoke($this->connectionManager, $symbol);
    }

    public function testStreamOrderbookHandlesExchangeError(): void
    {
        $symbol = 'BTC/USDT';
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOrderBook')
            ->willThrowException(new \Exception('Exchange error'));
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'error';
            }));
        
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('streamOrderbook');
        $method->setAccessible(true);
        $method->invoke($this->connectionManager, $symbol);
    }

    public function testStreamTickerFetchesAndFormatsData(): void
    {
        $symbol = 'BTC/USDT';
        $streamKey = 'BTC/USDT:ticker';
        
        // Mock ticker data
        $mockTicker = [
            'last' => 49050.0,
            'bid' => 49000.0,
            'ask' => 49100.0,
            'high' => 50000.0,
            'low' => 45000.0,
            'open' => 47000.0,
            'close' => 49050.0,
            'change' => 2050.0,
            'percentage' => 4.36,
            'baseVolume' => 1000.0,
            'quoteVolume' => 48500000.0,
            'timestamp' => 1640995200000
        ];
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchTicker')
            ->with($symbol)
            ->willReturn($mockTicker);
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'ticker_update' &&
                       $decoded['symbol'] === 'BTC/USDT' &&
                       $decoded['last'] === 49050.0 &&
                       $decoded['bid'] === 49000.0 &&
                       $decoded['ask'] === 49100.0;
            }));
        
        $this->connectionManager->connect($this->mockConnection, $streamKey, 'ticker');
        
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('streamTicker');
        $method->setAccessible(true);
        $method->invoke($this->connectionManager, $symbol, $streamKey);
    }

    public function testSendErrorFormatsAndSendsErrorMessage(): void
    {
        $errorMessage = 'Test error message';
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use ($errorMessage) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'error' &&
                       $decoded['message'] === $errorMessage;
            }));
        
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('sendError');
        $method->setAccessible(true);
        $method->invoke($this->connectionManager, $this->mockConnection, $errorMessage);
    }

    public function testSendErrorHandlesConnectionException(): void
    {
        $this->mockConnection->method('send')
            ->willThrowException(new \Exception('Connection closed'));
        
        $reflection = new ReflectionClass($this->connectionManager);
        $method = $reflection->getMethod('sendError');
        $method->setAccessible(true);
        
        // Should not throw exception
        $method->invoke($this->connectionManager, $this->mockConnection, 'Test error');
        
        $this->assertTrue(true);
    }
}