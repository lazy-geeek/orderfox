<?php

declare(strict_types=1);

namespace Tests\Integration\Api\V1;

use OrderFox\Core\Logger;
use OrderFox\Api\V1\Controllers\MarketDataController;
use PHPUnit\Framework\TestCase;
use Slim\Psr7\Factory\ServerRequestFactory;
use Slim\Psr7\Response;

class ApiFormatValidationTest extends TestCase
{
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
        
        // Create controller and request factory
        $this->controller = new MarketDataController();
        $this->requestFactory = new ServerRequestFactory();
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    public function testSymbolsEndpointResponseFormat(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/symbols');
        $response = new Response();
        
        $result = $this->controller->getSymbols($request, $response);
        
        $this->assertEquals(200, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        // Validate top-level structure
        $this->assertIsArray($data);
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        
        // Validate individual symbol format (if any symbols exist)
        if (!empty($data['data'])) {
            $firstSymbol = $data['data'][0];
            
            // Required fields
            $this->assertArrayHasKey('symbol', $firstSymbol);
            $this->assertArrayHasKey('base', $firstSymbol);
            $this->assertArrayHasKey('quote', $firstSymbol);
            
            // Data types
            $this->assertIsString($firstSymbol['symbol']);
            $this->assertIsString($firstSymbol['base']);
            $this->assertIsString($firstSymbol['quote']);
            
            // Format validation
            $this->assertStringContainsString('/', $firstSymbol['symbol']);
            $this->assertEquals($firstSymbol['base'] . '/' . $firstSymbol['quote'], $firstSymbol['symbol']);
        }
    }

    public function testTickerEndpointResponseFormat(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/BTCUSDT');
        $response = new Response();
        
        $result = $this->controller->getTicker($request, $response, ['symbol' => 'BTCUSDT']);
        
        $this->assertEquals(200, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        // Validate top-level structure
        $this->assertIsArray($data);
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        
        $ticker = $data['data'];
        
        // Required fields
        $requiredFields = [
            'symbol', 'last', 'bid', 'ask', 'high', 'low', 
            'open', 'close', 'change', 'percentage', 'volume', 'quote_volume', 'timestamp'
        ];
        
        foreach ($requiredFields as $field) {
            $this->assertArrayHasKey($field, $ticker, "Ticker should have '{$field}' field");
        }
        
        // Data types validation
        $this->assertIsString($ticker['symbol']);
        $this->assertIsInt($ticker['timestamp']);
        
        // Numeric fields (can be null or numeric)
        $numericFields = ['last', 'bid', 'ask', 'high', 'low', 'open', 'close', 'change', 'percentage', 'volume', 'quote_volume'];
        foreach ($numericFields as $field) {
            if ($ticker[$field] !== null) {
                $this->assertTrue(is_numeric($ticker[$field]), "Field '{$field}' should be numeric or null");
            }
        }
        
        // Symbol format
        $this->assertMatchesRegularExpression('/^[A-Z]+\/[A-Z]+$/', $ticker['symbol']);
        
        // Timestamp validation (should be recent)
        $currentTime = time() * 1000;
        $this->assertGreaterThan($currentTime - 86400000, $ticker['timestamp']); // Within last 24 hours
        $this->assertLessThanOrEqual($currentTime + 60000, $ticker['timestamp']); // Not in future
    }

    public function testOrderBookEndpointResponseFormat(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/orderbook/BTCUSDT?limit=20');
        $response = new Response();
        
        $result = $this->controller->getOrderBook($request, $response, ['symbol' => 'BTCUSDT']);
        
        $this->assertEquals(200, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        // Validate top-level structure
        $this->assertIsArray($data);
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        
        $orderBook = $data['data'];
        
        // Required fields
        $this->assertArrayHasKey('symbol', $orderBook);
        $this->assertArrayHasKey('bids', $orderBook);
        $this->assertArrayHasKey('asks', $orderBook);
        $this->assertArrayHasKey('timestamp', $orderBook);
        
        // Data types
        $this->assertIsString($orderBook['symbol']);
        $this->assertIsArray($orderBook['bids']);
        $this->assertIsArray($orderBook['asks']);
        $this->assertIsInt($orderBook['timestamp']);
        
        // Symbol format
        $this->assertMatchesRegularExpression('/^[A-Z]+\/[A-Z]+$/', $orderBook['symbol']);
        
        // Bids format validation
        if (!empty($orderBook['bids'])) {
            foreach ($orderBook['bids'] as $index => $bid) {
                $this->assertIsArray($bid, "Bid at index {$index} should be an array");
                $this->assertArrayHasKey('price', $bid, "Bid at index {$index} should have 'price'");
                $this->assertArrayHasKey('amount', $bid, "Bid at index {$index} should have 'amount'");
                $this->assertIsFloat($bid['price'], "Bid price at index {$index} should be float");
                $this->assertIsFloat($bid['amount'], "Bid amount at index {$index} should be float");
                $this->assertGreaterThan(0, $bid['price'], "Bid price should be positive");
                $this->assertGreaterThan(0, $bid['amount'], "Bid amount should be positive");
            }
            
            // Bids should be sorted in descending order by price
            for ($i = 1; $i < count($orderBook['bids']); $i++) {
                $this->assertGreaterThanOrEqual(
                    $orderBook['bids'][$i]['price'], 
                    $orderBook['bids'][$i-1]['price'],
                    'Bids should be sorted in descending order by price'
                );
            }
        }
        
        // Asks format validation
        if (!empty($orderBook['asks'])) {
            foreach ($orderBook['asks'] as $index => $ask) {
                $this->assertIsArray($ask, "Ask at index {$index} should be an array");
                $this->assertArrayHasKey('price', $ask, "Ask at index {$index} should have 'price'");
                $this->assertArrayHasKey('amount', $ask, "Ask at index {$index} should have 'amount'");
                $this->assertIsFloat($ask['price'], "Ask price at index {$index} should be float");
                $this->assertIsFloat($ask['amount'], "Ask amount at index {$index} should be float");
                $this->assertGreaterThan(0, $ask['price'], "Ask price should be positive");
                $this->assertGreaterThan(0, $ask['amount'], "Ask amount should be positive");
            }
            
            // Asks should be sorted in ascending order by price
            for ($i = 1; $i < count($orderBook['asks']); $i++) {
                $this->assertLessThanOrEqual(
                    $orderBook['asks'][$i]['price'], 
                    $orderBook['asks'][$i-1]['price'],
                    'Asks should be sorted in ascending order by price'
                );
            }
        }
        
        // Spread validation (if both bids and asks exist)
        if (!empty($orderBook['bids']) && !empty($orderBook['asks'])) {
            $bestBid = $orderBook['bids'][0]['price'];
            $bestAsk = $orderBook['asks'][0]['price'];
            $this->assertLessThan($bestAsk, $bestBid, 'Best bid should be less than best ask (positive spread)');
        }
        
        // Timestamp validation
        $currentTime = time() * 1000;
        $this->assertGreaterThan($currentTime - 60000, $orderBook['timestamp']); // Within last minute
        $this->assertLessThanOrEqual($currentTime + 60000, $orderBook['timestamp']); // Not in future
    }

    public function testCandlesEndpointResponseFormat(): void
    {
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/candles/BTCUSDT/1h?limit=10');
        $response = new Response();
        
        $result = $this->controller->getCandles($request, $response, [
            'symbol' => 'BTCUSDT', 
            'timeframe' => '1h'
        ]);
        
        $this->assertEquals(200, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        // Validate top-level structure
        $this->assertIsArray($data);
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        
        $candles = $data['data'];
        
        // Validate individual candle format (if any candles exist)
        if (!empty($candles)) {
            foreach ($candles as $index => $candle) {
                // Required fields
                $requiredFields = ['timestamp', 'open', 'high', 'low', 'close', 'volume'];
                foreach ($requiredFields as $field) {
                    $this->assertArrayHasKey($field, $candle, "Candle at index {$index} should have '{$field}' field");
                }
                
                // Data types
                $this->assertIsInt($candle['timestamp'], "Candle timestamp at index {$index} should be integer");
                $this->assertIsFloat($candle['open'], "Candle open at index {$index} should be float");
                $this->assertIsFloat($candle['high'], "Candle high at index {$index} should be float");
                $this->assertIsFloat($candle['low'], "Candle low at index {$index} should be float");
                $this->assertIsFloat($candle['close'], "Candle close at index {$index} should be float");
                $this->assertIsFloat($candle['volume'], "Candle volume at index {$index} should be float");
                
                // OHLC validation
                $this->assertGreaterThanOrEqual($candle['low'], $candle['open'], "Candle open should be >= low");
                $this->assertGreaterThanOrEqual($candle['low'], $candle['close'], "Candle close should be >= low");
                $this->assertLessThanOrEqual($candle['high'], $candle['open'], "Candle open should be <= high");
                $this->assertLessThanOrEqual($candle['high'], $candle['close'], "Candle close should be <= high");
                $this->assertLessThanOrEqual($candle['low'], $candle['high'], "Candle low should be <= high");
                
                // Positive values
                $this->assertGreaterThan(0, $candle['open'], "Candle open should be positive");
                $this->assertGreaterThan(0, $candle['high'], "Candle high should be positive");
                $this->assertGreaterThan(0, $candle['low'], "Candle low should be positive");
                $this->assertGreaterThan(0, $candle['close'], "Candle close should be positive");
                $this->assertGreaterThanOrEqual(0, $candle['volume'], "Candle volume should be non-negative");
                
                // Timestamp validation
                $this->assertGreaterThan(0, $candle['timestamp'], "Candle timestamp should be positive");
            }
            
            // Candles should be sorted by timestamp (ascending)
            for ($i = 1; $i < count($candles); $i++) {
                $this->assertGreaterThanOrEqual(
                    $candles[$i-1]['timestamp'], 
                    $candles[$i]['timestamp'],
                    'Candles should be sorted by timestamp (oldest first)'
                );
            }
        }
    }

    public function testErrorResponseFormat(): void
    {
        // Test validation error format
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/');
        $response = new Response();
        
        $result = $this->controller->getTicker($request, $response, ['symbol' => '']);
        
        $this->assertEquals(400, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        // Validate error structure
        $this->assertIsArray($data);
        $this->assertArrayHasKey('error', $data);
        $this->assertIsArray($data['error']);
        
        $error = $data['error'];
        
        // Required error fields
        $this->assertArrayHasKey('type', $error);
        $this->assertArrayHasKey('message', $error);
        
        // Data types
        $this->assertIsString($error['type']);
        $this->assertIsString($error['message']);
        
        // Error type validation
        $this->assertEquals('validation_error', $error['type']);
        $this->assertNotEmpty($error['message']);
    }

    public function testExchangeErrorResponseFormat(): void
    {
        // Test exchange error format with invalid symbol
        $request = $this->requestFactory->createServerRequest('GET', '/api/v1/ticker/INVALID');
        $response = new Response();
        
        $result = $this->controller->getTicker($request, $response, ['symbol' => 'INVALID']);
        
        $this->assertEquals(500, $result->getStatusCode());
        
        $body = (string) $result->getBody();
        $data = json_decode($body, true);
        
        // Validate error structure
        $this->assertIsArray($data);
        $this->assertArrayHasKey('error', $data);
        $this->assertIsArray($data['error']);
        
        $error = $data['error'];
        
        // Required error fields
        $this->assertArrayHasKey('type', $error);
        $this->assertArrayHasKey('message', $error);
        
        // Data types
        $this->assertIsString($error['type']);
        $this->assertIsString($error['message']);
        
        // Error type validation
        $this->assertEquals('exchange_error', $error['type']);
        $this->assertStringContainsString('Failed to fetch ticker', $error['message']);
    }

    public function testContentTypeHeaders(): void
    {
        $endpoints = [
            ['method' => 'getSymbols', 'args' => []],
            ['method' => 'getTicker', 'args' => ['symbol' => 'BTCUSDT']],
            ['method' => 'getOrderBook', 'args' => ['symbol' => 'BTCUSDT']],
            ['method' => 'getCandles', 'args' => ['symbol' => 'BTCUSDT', 'timeframe' => '1h']]
        ];
        
        foreach ($endpoints as $endpoint) {
            $request = $this->requestFactory->createServerRequest('GET', '/test');
            $response = new Response();
            
            $result = $this->controller->{$endpoint['method']}($request, $response, $endpoint['args']);
            
            // All responses should have JSON content type
            $contentType = $result->getHeaderLine('Content-Type');
            $this->assertStringContainsString('application/json', $contentType,
                "Endpoint {$endpoint['method']} should return JSON content type");
        }
    }

    public function testResponseConsistencyAcrossMultipleCalls(): void
    {
        $symbol = 'BTCUSDT';
        $request = $this->requestFactory->createServerRequest('GET', "/api/v1/ticker/{$symbol}");
        $response = new Response();
        
        $responses = [];
        
        // Make multiple calls
        for ($i = 0; $i < 3; $i++) {
            $result = $this->controller->getTicker($request, $response, ['symbol' => $symbol]);
            $body = (string) $result->getBody();
            $data = json_decode($body, true);
            $responses[] = $data;
        }
        
        // All responses should have the same structure
        foreach ($responses as $index => $response) {
            $this->assertArrayHasKey('data', $response, "Response {$index} should have 'data' key");
            
            $ticker = $response['data'];
            $requiredFields = [
                'symbol', 'last', 'bid', 'ask', 'high', 'low', 
                'open', 'close', 'change', 'percentage', 'volume', 'quote_volume', 'timestamp'
            ];
            
            foreach ($requiredFields as $field) {
                $this->assertArrayHasKey($field, $ticker, 
                    "Response {$index} ticker should have '{$field}' field");
            }
        }
    }

    public function testApiVersionConsistency(): void
    {
        // All endpoints should be consistent with v1 API format
        $endpoints = [
            'symbols' => [],
            'ticker' => ['symbol' => 'BTCUSDT'],
            'orderbook' => ['symbol' => 'BTCUSDT'],
            'candles' => ['symbol' => 'BTCUSDT', 'timeframe' => '1h']
        ];
        
        foreach ($endpoints as $endpoint => $args) {
            $request = $this->requestFactory->createServerRequest('GET', "/api/v1/{$endpoint}");
            $response = new Response();
            
            switch ($endpoint) {
                case 'symbols':
                    $result = $this->controller->getSymbols($request, $response);
                    break;
                case 'ticker':
                    $result = $this->controller->getTicker($request, $response, $args);
                    break;
                case 'orderbook':
                    $result = $this->controller->getOrderBook($request, $response, $args);
                    break;
                case 'candles':
                    $result = $this->controller->getCandles($request, $response, $args);
                    break;
            }
            
            $body = (string) $result->getBody();
            $data = json_decode($body, true);
            
            // All successful responses should have 'data' wrapper
            if ($result->getStatusCode() === 200) {
                $this->assertArrayHasKey('data', $data, 
                    "Endpoint {$endpoint} should wrap response in 'data' key");
            }
            
            // All error responses should have 'error' wrapper
            if ($result->getStatusCode() >= 400) {
                $this->assertArrayHasKey('error', $data, 
                    "Endpoint {$endpoint} error response should have 'error' key");
            }
        }
    }
}