<?php

declare(strict_types=1);

namespace Tests\Integration\Core;

use OrderFox\Core\Logger;
use OrderFox\Services\ExchangeService;
use OrderFox\Services\SymbolService;
use OrderFox\Services\ConnectionManager;
use OrderFox\Api\V1\Controllers\MarketDataController;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Slim\Psr7\Factory\ServerRequestFactory;
use Slim\Psr7\Response;
use Ratchet\ConnectionInterface;

class ErrorHandlingTest extends TestCase
{
    private ExchangeService $exchangeService;
    private SymbolService $symbolService;
    private ConnectionManager $connectionManager;
    private MarketDataController $controller;
    private ServerRequestFactory $requestFactory;

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
        $this->exchangeService = new ExchangeService();
        $this->symbolService = new SymbolService();
        $this->connectionManager = new ConnectionManager();
        $this->controller = new MarketDataController();
        $this->requestFactory = new ServerRequestFactory();
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    public function testExchangeServiceHandlesNetworkErrors(): void
    {
        // Test that network errors are properly caught and handled
        $this->expectException(\Exception::class);
        
        // Try to fetch data with invalid credentials
        $_ENV['BINANCE_API_KEY'] = 'invalid_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'invalid_secret';
        
        $exchangeService = new ExchangeService();
        
        // This should throw an exception that gets caught by the application
        $exchangeService->fetchTicker('INVALID/SYMBOL');
    }

    public function testSymbolServiceHandlesInvalidSymbols(): void
    {
        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage('Symbol not found');
        
        // Try to resolve an invalid symbol
        $this->symbolService->resolveSymbol('COMPLETELY_INVALID_SYMBOL_12345');
    }

    public function testSymbolServiceHandlesEmptyInput(): void
    {
        $this->expectException(\InvalidArgumentException::class);
        
        // Try to resolve an empty symbol
        $this->symbolService->resolveSymbol('');
    }

    public function testConnectionManagerHandlesConnectionErrors(): void
    {
        $symbol = 'BTC/USDT';
        
        // Create a mock connection that throws exceptions
        $faultyConnection = $this->createMock(ConnectionInterface::class);
        $faultyConnection->method('send')
            ->willThrowException(new \Exception('Connection lost'));
        
        // Connect the faulty connection
        $this->connectionManager->connect($faultyConnection, $symbol, 'orderbook');
        
        // Broadcasting should handle the error without crashing
        $this->connectionManager->broadcastToStream($symbol, ['type' => 'test']);
        
        // Test passes if no exception is thrown
        $this->assertTrue(true);
    }

    public function testControllerHandlesExchangeServiceErrors(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/INVALID');
        $response = new Response();
        
        $result = $this->controller->getTicker($request, $response, ['symbol' => 'INVALID']);
        
        $this->assertEquals(500, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertArrayHasKey('message', $data['error']);
        $this->assertStringContainsString('Failed to fetch ticker', $data['error']['message']);
    }

    public function testControllerHandlesValidationErrors(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/orderbook/BTC?limit=10000');
        $response = new Response();
        
        $result = $this->controller->getOrderBook($request, $response, ['symbol' => 'BTC']);
        
        $this->assertEquals(400, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testControllerHandlesMissingParameters(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/');
        $response = new Response();
        
        // Test with empty symbol parameter
        $result = $this->controller->getTicker($request, $response, ['symbol' => '']);
        
        $this->assertEquals(400, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testControllerHandlesMalformedRequests(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/candles/BTC/invalid_timeframe');
        $response = new Response();
        
        $result = $this->controller->getCandles($request, $response, [
            'symbol' => 'BTC', 
            'timeframe' => 'invalid_timeframe'
        ]);
        
        $this->assertEquals(400, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testWebSocketStreamingHandlesExchangeErrors(): void
    {
        $symbol = 'INVALID/SYMBOL';
        $mockConnection = $this->createMock(ConnectionInterface::class);
        
        // Expect error message to be sent
        $mockConnection->expects($this->once())
            ->method('send')
            ->with($this->callback(function ($data) {
                $decoded = json_decode($data, true);
                return $decoded['type'] === 'error' && 
                       isset($decoded['message']);
            }));
        
        // Connect with invalid symbol
        $this->connectionManager->connect($mockConnection, $symbol, 'orderbook');
        
        // Manually trigger streaming to test error handling
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        $streamMethod->invoke($this->connectionManager, $symbol);
    }

    public function testLoggerHandlesExceptionsDuringLogging(): void
    {
        // Test that logger doesn't crash the application even if logging fails
        $logger = Logger::getLogger('test');
        
        // Try to log various types of data including problematic ones
        $logger->info('Normal message');
        $logger->error('Error message', ['exception' => new \Exception('Test exception')]);
        
        // Test with circular reference (shouldn't crash)
        $obj1 = new \stdClass();
        $obj2 = new \stdClass();
        $obj1->ref = $obj2;
        $obj2->ref = $obj1;
        
        $logger->info('Circular reference test', ['circular' => $obj1]);
        
        // Test passes if no exception is thrown
        $this->assertTrue(true);
    }

    public function testConfigHandlesMissingEnvironmentVariables(): void
    {
        // Temporarily unset required environment variables
        $originalApiKey = $_ENV['BINANCE_API_KEY'] ?? null;
        $originalSecretKey = $_ENV['BINANCE_SECRET_KEY'] ?? null;
        
        unset($_ENV['BINANCE_API_KEY']);
        unset($_ENV['BINANCE_SECRET_KEY']);
        
        try {
            // Config should handle missing variables gracefully
            $config = \OrderFox\Core\Config::getInstance();
            $apiKey = $config->get('BINANCE_API_KEY');
            $secretKey = $config->get('BINANCE_SECRET_KEY');
            
            // Should return null or default values, not crash
            $this->assertNull($apiKey);
            $this->assertNull($secretKey);
            
        } finally {
            // Restore original values
            if ($originalApiKey !== null) {
                $_ENV['BINANCE_API_KEY'] = $originalApiKey;
            }
            if ($originalSecretKey !== null) {
                $_ENV['BINANCE_SECRET_KEY'] = $originalSecretKey;
            }
        }
    }

    public function testExchangeServiceHandlesRateLimiting(): void
    {
        // This test simulates rate limiting scenarios
        $mockConnection = $this->createMock(ConnectionInterface::class);
        
        // Connect multiple streams rapidly to potentially trigger rate limits
        for ($i = 0; $i < 5; $i++) {
            $symbol = "SYMBOL{$i}/USDT";
            $this->connectionManager->connect($mockConnection, $symbol, 'orderbook');
            
            // Trigger streaming
            $reflection = new \ReflectionClass($this->connectionManager);
            $streamMethod = $reflection->getMethod('streamOrderbook');
            $streamMethod->setAccessible(true);
            
            try {
                $streamMethod->invoke($this->connectionManager, $symbol);
            } catch (\Exception $e) {
                // Rate limiting errors should be caught and handled
                $this->assertStringContainsString('rate', strtolower($e->getMessage()));
            }
        }
        
        // Test passes if the application handles rate limiting gracefully
        $this->assertTrue(true);
    }

    public function testMemoryLeakPrevention(): void
    {
        $initialMemory = memory_get_usage();
        
        // Create and destroy many connections to test memory management
        for ($i = 0; $i < 100; $i++) {
            $mockConnection = $this->createMock(ConnectionInterface::class);
            $symbol = "TEST{$i}/USDT";
            
            $this->connectionManager->connect($mockConnection, $symbol, 'orderbook');
            $this->connectionManager->disconnect($mockConnection, $symbol);
        }
        
        // Force garbage collection
        gc_collect_cycles();
        
        $finalMemory = memory_get_usage();
        $memoryIncrease = $finalMemory - $initialMemory;
        
        // Memory increase should be reasonable (less than 1MB for 100 connections)
        $this->assertLessThan(1024 * 1024, $memoryIncrease, 
            'Memory usage should not increase significantly after connection cleanup');
    }

    public function testConcurrentErrorHandling(): void
    {
        $symbols = ['BTC/USDT', 'ETH/USDT', 'INVALID/SYMBOL', 'ANOTHER/INVALID'];
        $connections = [];
        
        // Create connections for multiple symbols (some invalid)
        foreach ($symbols as $symbol) {
            $mockConnection = $this->createMock(ConnectionInterface::class);
            $mockConnection->expects($this->atLeastOnce())
                ->method('send')
                ->with($this->anything());
            
            $connections[] = $mockConnection;
            $this->connectionManager->connect($mockConnection, $symbol, 'orderbook');
        }
        
        // Trigger streaming for all symbols concurrently
        $reflection = new \ReflectionClass($this->connectionManager);
        $streamMethod = $reflection->getMethod('streamOrderbook');
        $streamMethod->setAccessible(true);
        
        foreach ($symbols as $symbol) {
            try {
                $streamMethod->invoke($this->connectionManager, $symbol);
            } catch (\Exception $e) {
                // Errors should be handled gracefully
                $this->assertNotEmpty($e->getMessage());
            }
        }
        
        // Test passes if concurrent error handling works properly
        $this->assertTrue(true);
    }

    public function testErrorResponseFormatConsistency(): void
    {
        $errorScenarios = [
            ['endpoint' => '/api/v1/ticker/INVALID', 'args' => ['symbol' => 'INVALID']],
            ['endpoint' => '/api/v1/orderbook/BTC?limit=10000', 'args' => ['symbol' => 'BTC']],
            ['endpoint' => '/api/v1/candles/BTC/invalid', 'args' => ['symbol' => 'BTC', 'timeframe' => 'invalid']]
        ];
        
        foreach ($errorScenarios as $scenario) {
            $request = $this->requestFactory->createServerRequest('GET', $scenario['endpoint']);
            $response = new Response();
            
            // Determine which controller method to call based on endpoint
            if (strpos($scenario['endpoint'], '/ticker/') !== false) {
                $result = $this->controller->getTicker($request, $response, $scenario['args']);
            } elseif (strpos($scenario['endpoint'], '/orderbook/') !== false) {
                $result = $this->controller->getOrderBook($request, $response, $scenario['args']);
            } elseif (strpos($scenario['endpoint'], '/candles/') !== false) {
                $result = $this->controller->getCandles($request, $response, $scenario['args']);
            }
            
            $this->assertGreaterThanOrEqual(400, $result->getStatusCode());
            
            $body = (string) $result->getBody();
            $data = json_decode($body, true);
            
            // All error responses should have consistent format
            $this->assertArrayHasKey('error', $data);
            $this->assertArrayHasKey('message', $data['error']);
            $this->assertIsString($data['error']['message']);
        }
    }
}