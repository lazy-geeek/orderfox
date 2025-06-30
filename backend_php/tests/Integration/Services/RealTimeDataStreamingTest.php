<?php

declare(strict_types=1);

namespace Tests\Integration\Services;

use OrderFox\Core\Logger;
use OrderFox\Services\ConnectionManager;
use OrderFox\Services\ExchangeService;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Ratchet\ConnectionInterface;

class RealTimeDataStreamingTest extends TestCase
{
    private ConnectionManager $connectionManager;
    private ExchangeService $exchangeService;
    private MockObject $mockConnection;

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
        
        // Create services
        $this->connectionManager = new ConnectionManager();
        $this->exchangeService = new ExchangeService();
        
        // Create mock WebSocket connection
        $this->mockConnection = $this->createMock(ConnectionInterface::class);
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    public function testOrderBookDataStreamingFormat(): void
    {
        $symbol = 'BTC/USDT';
        $limit = 20;
        
        // Test that orderbook streaming produces correct format
        $receivedData = null;
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$receivedData) {
                $receivedData = json_decode($data, true);
                return true;
            }));
        
        // Connect and trigger streaming
        $this->connectionManager->connectOrderbook($this->mockConnection, $symbol, $symbol, $limit);
        
        // Manually trigger streaming to test format
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol);
        
        // Verify data format
        $this->assertNotNull($receivedData);
        $this->assertEquals('orderbook_update', $receivedData['type']);
        $this->assertEquals($symbol, $receivedData['symbol']);
        $this->assertArrayHasKey('bids', $receivedData);
        $this->assertArrayHasKey('asks', $receivedData);
        $this->assertArrayHasKey('timestamp', $receivedData);
        
        // Verify bids/asks structure
        if (!empty($receivedData['bids'])) {
            $firstBid = $receivedData['bids'][0];
            $this->assertArrayHasKey('price', $firstBid);
            $this->assertArrayHasKey('amount', $firstBid);
            $this->assertIsFloat($firstBid['price']);
            $this->assertIsFloat($firstBid['amount']);
        }
        
        if (!empty($receivedData['asks'])) {
            $firstAsk = $receivedData['asks'][0];
            $this->assertArrayHasKey('price', $firstAsk);
            $this->assertArrayHasKey('amount', $firstAsk);
            $this->assertIsFloat($firstAsk['price']);
            $this->assertIsFloat($firstAsk['amount']);
        }
    }

    public function testTickerDataStreamingFormat(): void
    {
        $symbol = 'BTC/USDT';
        $streamKey = 'BTC/USDT:ticker';
        
        $receivedData = null;
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$receivedData) {
                $receivedData = json_decode($data, true);
                return true;
            }));
        
        // Connect and trigger streaming
        $this->connectionManager->connect($this->mockConnection, $streamKey, 'ticker');
        
        // Manually trigger streaming
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamTicker');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol, $streamKey);
        
        // Verify data format
        $this->assertNotNull($receivedData);
        $this->assertEquals('ticker_update', $receivedData['type']);
        $this->assertEquals($symbol, $receivedData['symbol']);
        $this->assertArrayHasKey('last', $receivedData);
        $this->assertArrayHasKey('bid', $receivedData);
        $this->assertArrayHasKey('ask', $receivedData);
        $this->assertArrayHasKey('high', $receivedData);
        $this->assertArrayHasKey('low', $receivedData);
        $this->assertArrayHasKey('open', $receivedData);
        $this->assertArrayHasKey('close', $receivedData);
        $this->assertArrayHasKey('change', $receivedData);
        $this->assertArrayHasKey('percentage', $receivedData);
        $this->assertArrayHasKey('volume', $receivedData);
        $this->assertArrayHasKey('quote_volume', $receivedData);
        $this->assertArrayHasKey('timestamp', $receivedData);
        
        // Verify numeric fields are properly typed
        foreach (['last', 'bid', 'ask', 'high', 'low', 'open', 'close', 'change', 'percentage', 'volume', 'quote_volume'] as $field) {
            if ($receivedData[$field] !== null) {
                $this->assertIsFloat($receivedData[$field], "Field {$field} should be float or null");
            }
        }
        
        $this->assertIsInt($receivedData['timestamp']);
    }

    public function testCandleDataStreamingFormat(): void
    {
        $symbol = 'BTC/USDT';
        $timeframe = '1h';
        $streamKey = 'BTC/USDT:1h';
        
        $receivedData = null;
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$receivedData) {
                $receivedData = json_decode($data, true);
                return true;
            }));
        
        // Connect and trigger streaming
        $this->connectionManager->connect($this->mockConnection, $streamKey, 'candles');
        
        // Manually trigger streaming
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamCandles');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol, $timeframe, $streamKey);
        
        // Verify data format
        $this->assertNotNull($receivedData);
        $this->assertEquals('candle_update', $receivedData['type']);
        $this->assertEquals($symbol, $receivedData['symbol']);
        $this->assertEquals($timeframe, $receivedData['timeframe']);
        $this->assertArrayHasKey('timestamp', $receivedData);
        $this->assertArrayHasKey('open', $receivedData);
        $this->assertArrayHasKey('high', $receivedData);
        $this->assertArrayHasKey('low', $receivedData);
        $this->assertArrayHasKey('close', $receivedData);
        $this->assertArrayHasKey('volume', $receivedData);
        
        // Verify OHLCV data types
        $this->assertIsInt($receivedData['timestamp']);
        $this->assertIsFloat($receivedData['open']);
        $this->assertIsFloat($receivedData['high']);
        $this->assertIsFloat($receivedData['low']);
        $this->assertIsFloat($receivedData['close']);
        $this->assertIsFloat($receivedData['volume']);
        
        // Verify OHLC logic
        $this->assertGreaterThanOrEqual($receivedData['low'], $receivedData['open']);
        $this->assertGreaterThanOrEqual($receivedData['low'], $receivedData['close']);
        $this->assertLessThanOrEqual($receivedData['high'], $receivedData['open']);
        $this->assertLessThanOrEqual($receivedData['high'], $receivedData['close']);
    }

    public function testDataStreamingConsistency(): void
    {
        $symbol = 'BTC/USDT';
        $receivedMessages = [];
        
        // Capture multiple messages
        $this->mockConnection->expects($this->exactly(3))
            ->method('send')
            ->with($this->callback(function ($data) use (&$receivedMessages) {
                $receivedMessages[] = json_decode($data, true);
                return true;
            }));
        
        // Connect
        $this->connectionManager->connectOrderbook($this->mockConnection, $symbol, $symbol, 20);
        
        // Trigger streaming multiple times
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        
        $streamMethod->invoke($this->connectionManager, $symbol);
        $streamMethod->invoke($this->connectionManager, $symbol);
        $streamMethod->invoke($this->connectionManager, $symbol);
        
        // Verify all messages have consistent format
        $this->assertCount(3, $receivedMessages);
        
        foreach ($receivedMessages as $i => $message) {
            $this->assertEquals('orderbook_update', $message['type'], "Message {$i} should have correct type");
            $this->assertEquals($symbol, $message['symbol'], "Message {$i} should have correct symbol");
            $this->assertArrayHasKey('bids', $message, "Message {$i} should have bids");
            $this->assertArrayHasKey('asks', $message, "Message {$i} should have asks");
            $this->assertArrayHasKey('timestamp', $message, "Message {$i} should have timestamp");
        }
    }

    public function testDataStreamingWithDifferentLimits(): void
    {
        $symbol = 'BTC/USDT';
        $limits = [5, 20, 50, 100];
        
        foreach ($limits as $limit) {
            $receivedData = null;
            $mockConnection = $this->createMock(ConnectionInterface::class);
            
            $mockConnection->expects($this->once())
                ->method('send')
                ->with($this->callback(function ($data) use (&$receivedData) {
                    $receivedData = json_decode($data, true);
                    return true;
                }));
            
            // Connect with specific limit
            $this->connectionManager->connectOrderbook($mockConnection, $symbol, $symbol, $limit);
            
            // Trigger streaming
            $reflection = new \ReflectionClass($this->connectionManager);
            $streamMethod = $reflection->getMethod('streamOrderbook');
            $streamMethod->setAccessible(true);
            $streamMethod->invoke($this->connectionManager, $symbol);
            
            // Verify limit is respected
            $this->assertNotNull($receivedData);
            $this->assertLessThanOrEqual($limit, count($receivedData['bids']), 
                "Bids count should not exceed limit {$limit}");
            $this->assertLessThanOrEqual($limit, count($receivedData['asks']), 
                "Asks count should not exceed limit {$limit}");
            
            // Disconnect for next iteration
            $this->connectionManager->disconnectOrderbook($mockConnection, $symbol);
        }
    }

    public function testStreamingErrorHandlingAndRecovery(): void
    {
        $symbol = 'INVALID/SYMBOL';
        $errorReceived = false;
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$errorReceived) {
                $decoded = json_decode($data, true);
                if ($decoded['type'] === 'error') {
                    $errorReceived = true;
                }
                return true;
            }));
        
        // Connect with invalid symbol
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        
        // Trigger streaming (should produce error)
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol);
        
        $this->assertTrue($errorReceived, 'Error should be sent when streaming fails');
    }

    public function testMultipleSymbolStreamingIsolation(): void
    {
        $symbol1 = 'BTC/USDT';
        $symbol2 = 'ETH/USDT';
        
        $connection1 = $this->createMock(ConnectionInterface::class);
        $connection2 = $this->createMock(ConnectionInterface::class);
        
        $symbol1Data = null;
        $symbol2Data = null;
        
        $connection1->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$symbol1Data) {
                $symbol1Data = json_decode($data, true);
                return true;
            }));
        
        $connection2->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$symbol2Data) {
                $symbol2Data = json_decode($data, true);
                return true;
            }));
        
        // Connect to different symbols
        $this->connectionManager->connect($connection1, $symbol1, 'orderbook');
        $this->connectionManager->connect($connection2, $symbol2, 'orderbook');
        
        // Stream both symbols
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        
        $streamMethod->invoke($this->connectionManager, $symbol1);
        $streamMethod->invoke($this->connectionManager, $symbol2);
        
        // Verify each connection received data for its respective symbol
        $this->assertNotNull($symbol1Data);
        $this->assertNotNull($symbol2Data);
        $this->assertEquals($symbol1, $symbol1Data['symbol']);
        $this->assertEquals($symbol2, $symbol2Data['symbol']);
    }

    public function testStreamingDataTimestamps(): void
    {
        $symbol = 'BTC/USDT';
        $currentTime = time() * 1000; // Current time in milliseconds
        
        $receivedData = null;
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) use (&$receivedData) {
                $receivedData = json_decode($data, true);
                return true;
            }));
        
        // Connect and trigger streaming
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol);
        
        // Verify timestamp is reasonable (within last 5 minutes)
        $this->assertNotNull($receivedData);
        $this->assertArrayHasKey('timestamp', $receivedData);
        $this->assertIsInt($receivedData['timestamp']);
        $this->assertGreaterThan($currentTime - 300000, $receivedData['timestamp']); // Within 5 minutes
        $this->assertLessThanOrEqual($currentTime + 60000, $receivedData['timestamp']); // Not in future
    }

    public function testStreamingPerformance(): void
    {
        $symbol = 'BTC/USDT';
        $startTime = microtime(true);
        
        $this->mockConnection->expects($this->once())
            ->method('send')
            ->with($this->anything());
        
        // Connect and trigger streaming
        $this->connectionManager->connect($this->mockConnection, $symbol, 'orderbook');
        
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol);
        
        $endTime = microtime(true);
        $processingTime = ($endTime - $startTime) * 1000; // Convert to milliseconds
        
        // Streaming should complete within reasonable time (2 seconds)
        $this->assertLessThan(2000, $processingTime, 
            'Streaming processing should complete within 2 seconds');
    }
}