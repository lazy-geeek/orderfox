<?php

declare(strict_types=1);

namespace Tests\Unit\Api\V1\Controllers;

use OrderFox\Api\V1\Controllers\MarketDataController;
use OrderFox\Services\ExchangeService;
use OrderFox\Services\SymbolService;
use OrderFox\Core\Logger;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Psr\Http\Message\ServerRequestInterface;
use Psr\Http\Message\ResponseInterface;
use Slim\Psr7\Factory\ServerRequestFactory;
use Slim\Psr7\Response;
use ReflectionClass;

class MarketDataControllerTest extends TestCase
{
    private MarketDataController $controller;
    private MockObject $mockExchangeService;
    private MockObject $mockSymbolService;
    private ServerRequestInterface $request;
    private Response $response;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Reset logger for clean test state
        Logger::reset();
        
        // Create mock services
        $this->mockExchangeService = $this->createMock(ExchangeService::class);
        $this->mockSymbolService = $this->createMock(SymbolService::class);
        
        // Create controller
        $this->controller = new MarketDataController();
        
        // Replace services with mocks using reflection
        $reflection = new ReflectionClass($this->controller);
        
        $exchangeProperty = $reflection->getProperty('exchangeService');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($this->controller, $this->mockExchangeService);
        
        $symbolProperty = $reflection->getProperty('symbolService');
        $symbolProperty->setAccessible(true);
        $symbolProperty->setValue($this->controller, $this->mockSymbolService);
        
        // Create request and response objects
        $factory = new ServerRequestFactory();
        $this->request = $factory->createServerRequest('GET', 'http://localhost/');
        $this->response = new Response();
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    public function testGetSymbolsReturnsSuccessResponse(): void
    {
        $mockSymbols = [
            ['symbol' => 'BTC/USDT', 'base' => 'BTC', 'quote' => 'USDT'],
            ['symbol' => 'ETH/USDT', 'base' => 'ETH', 'quote' => 'USDT']
        ];
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($mockSymbols);
        
        $response = $this->controller->getSymbols($this->request, $this->response);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertIsArray($data);
        $this->assertArrayHasKey('data', $data);
        $this->assertCount(2, $data['data']);
    }

    public function testGetSymbolsHandlesExchangeError(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willThrowException(new \RuntimeException('Exchange API error'));
        
        $response = $this->controller->getSymbols($this->request, $this->response);
        
        $this->assertEquals(500, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertStringContainsString('Failed to fetch symbols', $data['error']['message']);
    }

    public function testGetTickerReturnsSuccessResponse(): void
    {
        $symbol = 'BTC/USDT';
        $resolvedSymbol = 'BTC/USDT';
        $mockTicker = [
            'symbol' => 'BTC/USDT',
            'last' => 50000.0,
            'bid' => 49900.0,
            'ask' => 50100.0
        ];
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->with($symbol)
            ->willReturn($resolvedSymbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchTicker')
            ->with($resolvedSymbol)
            ->willReturn($mockTicker);
        
        $response = $this->controller->getTicker($this->request, $this->response, ['symbol' => $symbol]);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        $this->assertEquals('BTC/USDT', $data['data']['symbol']);
        $this->assertEquals(50000.0, $data['data']['last']);
    }

    public function testGetTickerValidatesSymbolParameter(): void
    {
        // Empty symbol should trigger validation error
        $response = $this->controller->getTicker($this->request, $this->response, ['symbol' => '']);
        
        $this->assertEquals(400, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testGetTickerHandlesSymbolResolutionError(): void
    {
        $symbol = 'INVALID';
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->with($symbol)
            ->willThrowException(new \InvalidArgumentException('Symbol not found'));
        
        $response = $this->controller->getTicker($this->request, $this->response, ['symbol' => $symbol]);
        
        $this->assertEquals(500, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertStringContainsString('Failed to fetch ticker', $data['error']['message']);
    }

    public function testGetTickerHandlesExchangeError(): void
    {
        $symbol = 'BTC/USDT';
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->willReturn($symbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchTicker')
            ->willThrowException(new \RuntimeException('Exchange error'));
        
        $response = $this->controller->getTicker($this->request, $this->response, ['symbol' => $symbol]);
        
        $this->assertEquals(500, $response->getStatusCode());
    }

    public function testGetOrderBookReturnsSuccessResponse(): void
    {
        $symbol = 'BTC/USDT';
        $limit = 50;
        $mockOrderBook = [
            'symbol' => 'BTC/USDT',
            'bids' => [[50000.0, 1.0], [49900.0, 2.0]],
            'asks' => [[50100.0, 1.5], [50200.0, 2.5]],
            'timestamp' => 1640995200000
        ];
        
        // Create request with query parameters
        $request = $this->request->withQueryParams(['limit' => (string) $limit]);
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->with($symbol)
            ->willReturn($symbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOrderBook')
            ->with($symbol, $limit)
            ->willReturn($mockOrderBook);
        
        $response = $this->controller->getOrderBook($request, $this->response, ['symbol' => $symbol]);
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        $this->assertEquals('BTC/USDT', $data['data']['symbol']);
        $this->assertArrayHasKey('bids', $data['data']);
        $this->assertArrayHasKey('asks', $data['data']);
    }

    public function testGetOrderBookUsesDefaultLimit(): void
    {
        $symbol = 'BTC/USDT';
        $defaultLimit = 100;
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->willReturn($symbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOrderBook')
            ->with($symbol, $defaultLimit)
            ->willReturn(['symbol' => $symbol, 'bids' => [], 'asks' => []]);
        
        $response = $this->controller->getOrderBook($this->request, $this->response, ['symbol' => $symbol]);
        
        $this->assertEquals(200, $response->getStatusCode());
    }

    public function testGetOrderBookValidatesLimitParameter(): void
    {
        $symbol = 'BTC/USDT';
        $invalidLimit = 10000; // Over limit
        
        $request = $this->request->withQueryParams(['limit' => (string) $invalidLimit]);
        
        $response = $this->controller->getOrderBook($request, $this->response, ['symbol' => $symbol]);
        
        $this->assertEquals(400, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testGetCandlesReturnsSuccessResponse(): void
    {
        $symbol = 'BTC/USDT';
        $timeframe = '1h';
        $limit = 50;
        $mockCandles = [
            [
                'timestamp' => 1640995200000,
                'open' => 50000.0,
                'high' => 51000.0,
                'low' => 49000.0,
                'close' => 50500.0,
                'volume' => 1000.0
            ]
        ];
        
        $request = $this->request->withQueryParams(['limit' => (string) $limit]);
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->with($symbol)
            ->willReturn($symbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOHLCV')
            ->with($symbol, $timeframe, $limit)
            ->willReturn($mockCandles);
        
        $response = $this->controller->getCandles(
            $request, 
            $this->response, 
            ['symbol' => $symbol, 'timeframe' => $timeframe]
        );
        
        $this->assertEquals(200, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('data', $data);
        $this->assertIsArray($data['data']);
        $this->assertCount(1, $data['data']);
        $this->assertEquals(50000.0, $data['data'][0]['open']);
    }

    public function testGetCandlesUsesDefaultLimit(): void
    {
        $symbol = 'BTC/USDT';
        $timeframe = '1h';
        $defaultLimit = 100;
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->willReturn($symbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOHLCV')
            ->with($symbol, $timeframe, $defaultLimit)
            ->willReturn([]);
        
        $response = $this->controller->getCandles(
            $this->request, 
            $this->response, 
            ['symbol' => $symbol, 'timeframe' => $timeframe]
        );
        
        $this->assertEquals(200, $response->getStatusCode());
    }

    public function testGetCandlesValidatesTimeframe(): void
    {
        $symbol = 'BTC/USDT';
        $invalidTimeframe = 'invalid';
        
        $response = $this->controller->getCandles(
            $this->request, 
            $this->response, 
            ['symbol' => $symbol, 'timeframe' => $invalidTimeframe]
        );
        
        $this->assertEquals(400, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }

    public function testGetCandlesHandlesExchangeError(): void
    {
        $symbol = 'BTC/USDT';
        $timeframe = '1h';
        
        $this->mockSymbolService
            ->expects($this->once())
            ->method('resolveSymbol')
            ->willReturn($symbol);
        
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchOHLCV')
            ->willThrowException(new \RuntimeException('Exchange error'));
        
        $response = $this->controller->getCandles(
            $this->request, 
            $this->response, 
            ['symbol' => $symbol, 'timeframe' => $timeframe]
        );
        
        $this->assertEquals(500, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertStringContainsString('Failed to fetch candles', $data['error']['message']);
    }

    public function testMissingSymbolArgumentsHandled(): void
    {
        // Test ticker with missing symbol
        $response = $this->controller->getTicker($this->request, $this->response, []);
        $this->assertEquals(400, $response->getStatusCode());
        
        // Test orderbook with missing symbol
        $response = $this->controller->getOrderBook($this->request, $this->response, []);
        $this->assertEquals(400, $response->getStatusCode());
        
        // Test candles with missing symbol
        $response = $this->controller->getCandles($this->request, $this->response, ['timeframe' => '1h']);
        $this->assertEquals(400, $response->getStatusCode());
    }

    public function testMissingTimeframeArgumentHandled(): void
    {
        $response = $this->controller->getCandles($this->request, $this->response, ['symbol' => 'BTC/USDT']);
        $this->assertEquals(400, $response->getStatusCode());
        
        $body = (string) $response->getBody();
        $data = json_decode($body, true);
        
        $this->assertArrayHasKey('error', $data);
        $this->assertEquals('validation_error', $data['error']['type']);
    }
}