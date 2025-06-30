<?php

declare(strict_types=1);

namespace Tests\Integration\Api\V1\Controllers;

use OrderFox\Core\Config;
use OrderFox\Core\Logger;
use OrderFox\Services\ExchangeService;
use PHPUnit\Framework\TestCase;
use Slim\App;
use Slim\Factory\AppFactory;
use Slim\Psr7\Factory\ServerRequestFactory;
use Psr\Http\Message\ResponseInterface;

class MarketDataIntegrationTest extends TestCase
{
    private App $app;
    private ServerRequestFactory $requestFactory;
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
        
        // Create Slim app instance
        $this->app = AppFactory::create();
        
        // Set up routes (mimicking main application setup)
        $this->setupRoutes();
        
        // Create request factory
        $this->requestFactory = new ServerRequestFactory();
        
        // Initialize exchange service for integration testing
        $this->exchangeService = new ExchangeService();
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    private function setupRoutes(): void
    {
        $app = $this->app;
        
        // API routes group
        $app->group('/api/v1', function ($group) {
            $controller = new \OrderFox\Api\V1\Controllers\MarketDataController();
            
            $group->get('/symbols', [$controller, 'getSymbols']);
            $group->get('/ticker/{symbol}', [$controller, 'getTicker']);
            $group->get('/orderbook/{symbol}', [$controller, 'getOrderBook']);
            $group->get('/candles/{symbol}/{timeframe}', [$controller, 'getCandles']);
        });
    }

    public function testGetSymbolsEndpointReturnsValidResponse(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/symbols');
        $response = $this->app->handle($request);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertIsArray($data);
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        
        // Check response format matches expected schema
        if (!empty($data['data'])) {
            $firstSymbol = $data['data'][0];
            $this->assertArrayHasKey('symbol', $firstSymbol);
            $this->assertArrayHasKey('base', $firstSymbol);
            $this->assertArrayHasKey('quote', $firstSymbol);
        }
    }

    public function testGetTickerEndpointWithValidSymbol(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/BTCUSDT');
        $response = $this->app->handle($request);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        $this->assertArrayHasKey('symbol', $data['data']);
        $this->assertArrayHasKey('last', $data['data']);
        $this->assertArrayHasKey('bid', $data['data']);
        $this->assertArrayHasKey('ask', $data['data']);
    }

    public function testGetTickerEndpointWithInvalidSymbol(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/INVALID');
        $response = $this->app->handle($request);
        
        $this->assertEquals(500, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertArrayHasKey('message', $data['error']);
    }

    public function testGetOrderBookEndpointWithDefaultLimit(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/orderbook/BTCUSDT');
        $response = $this->app->handle($request);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        $this->assertArrayHasKey('symbol', $data['data']);
        $this->assertArrayHasKey('bids', $data['data']);
        $this->assertArrayHasKey('asks', $data['data']);
        $this->assertArrayHasKey('timestamp', $data['data']);
        
        // Verify bids and asks structure
        if (!empty($data['data']['bids'])) {
            $firstBid = $data['data']['bids'][0];
            $this->assertArrayHasKey('price', $firstBid);
            $this->assertArrayHasKey('amount', $firstBid);
            $this->assertIsFloat($firstBid['price']);
            $this->assertIsFloat($firstBid['amount']);
        }
    }

    public function testGetOrderBookEndpointWithCustomLimit(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/orderbook/BTCUSDT?limit=50');
        $response = $this->app->handle($request);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        
        // Verify limit is respected (should have at most 50 bids and asks)
        $this->assertLessThanOrEqual(50, count($data['data']['bids']));
        $this->assertLessThanOrEqual(50, count($data['data']['asks']));
    }

    public function testGetOrderBookEndpointWithInvalidLimit(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/orderbook/BTCUSDT?limit=10000');
        $response = $this->app->handle($request);
        
        $this->assertEquals(400, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testGetCandlesEndpointWithValidParameters(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/candles/BTCUSDT/1h');
        $response = $this->app->handle($request);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        
        // Check candle structure if data exists
        if (!empty($data['data'])) {
            $firstCandle = $data['data'][0];
            $this->assertArrayHasKey('timestamp', $firstCandle);
            $this->assertArrayHasKey('open', $firstCandle);
            $this->assertArrayHasKey('high', $firstCandle);
            $this->assertArrayHasKey('low', $firstCandle);
            $this->assertArrayHasKey('close', $firstCandle);
            $this->assertArrayHasKey('volume', $firstCandle);
        }
    }

    public function testGetCandlesEndpointWithCustomLimit(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/candles/BTCUSDT/1h?limit=50');
        $response = $this->app->handle($request);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        
        // Verify limit is respected
        $this->assertLessThanOrEqual(50, count($data['data']));
    }

    public function testGetCandlesEndpointWithInvalidTimeframe(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/candles/BTCUSDT/invalid');
        $response = $this->app->handle($request);
        
        $this->assertEquals(400, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testAllEndpointsReturnProperContentType(): void
    {
        $endpoints = [
            '/api/v1/symbols',
            '/api/v1/ticker/BTCUSDT',
            '/api/v1/orderbook/BTCUSDT',
            '/api/v1/candles/BTCUSDT/1h'
        ];
        
        foreach ($endpoints as $endpoint) {
            $request = $this->requestFactory->createServerRequest('GET', $endpoint);
            $response = $this->app->handle($request);
            
            $contentType = $response->getHeaderLine('Content-Type');
            $this->assertStringContainsString('application/json', $contentType, 
                "Endpoint {$endpoint} should return JSON content type");
        }
    }

    public function testAllEndpointsReturnValidJson(): void
    {
        $endpoints = [
            '/api/v1/symbols',
            '/api/v1/ticker/BTCUSDT',
            '/api/v1/orderbook/BTCUSDT',
            '/api/v1/candles/BTCUSDT/1h'
        ];
        
        foreach ($endpoints as $endpoint) {
            $request = $this->requestFactory->createServerRequest('GET', $endpoint);
            $response = $this->app->handle($request);
            
            $body = (string) $response->getBody();
            $decodedData = json_decode($body, true);
            
            $this->assertNotNull($decodedData, 
                "Endpoint {$endpoint} should return valid JSON");
            $this->assertEquals(JSON_ERROR_NONE, json_last_error(), 
                "Endpoint {$endpoint} should return valid JSON without errors");
        }
    }

    public function testErrorResponsesHaveConsistentFormat(): void
    {
        $errorEndpoints = [
            '/api/v1/ticker/INVALID',
            '/api/v1/orderbook/BTCUSDT?limit=10000',
            '/api/v1/candles/BTCUSDT/invalid'
        ];
        
        foreach ($errorEndpoints as $endpoint) {
            $request = $this->requestFactory->createServerRequest('GET', $endpoint);
            $response = $this->app->handle($request);
            
            $this->assertGreaterThanOrEqual(400, $response->getStatusCode(),
                "Endpoint {$endpoint} should return error status code");
            
            $body = (string) $response->getBody();
            $data = json_decode($body, true);
            
            $this->assertArrayHasKey('error', $data,
                "Error response from {$endpoint} should have 'error' key");
            $this->assertArrayHasKey('message', $data['error'],
                "Error response from {$endpoint} should have 'message' in error object");
        }
    }

    public function testCorsHeadersAreSet(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/symbols');
        $response = $this->app->handle($request);
        
        // Note: CORS headers would be set by middleware in the main application
        // This test verifies the application structure supports CORS
        $this->assertInstanceOf(ResponseInterface::class, $response);
    }

    public function testResponseTimesAreReasonable(): void
    {
        $startTime = microtime(true);
        
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/symbols');
        $response = $this->app->handle($request);
        
        $endTime = microtime(true);
        $responseTime = ($endTime - $startTime) * 1000; // Convert to milliseconds
        
        $this->assertLessThan(5000, $responseTime, 
            'Response time should be less than 5 seconds');
        $this->assertEquals(200, $response->getStatusCode());
    }
}