<?php

declare(strict_types=1);

namespace Tests\Unit\Services;

use OrderFox\Services\ExchangeService;
use OrderFox\Core\Config;
use OrderFox\Core\Logger;
use PHPUnit\Framework\TestCase;
use ReflectionClass;
use ccxt\Exchange;

class ExchangeServiceTest extends TestCase
{
    private array $originalEnv;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Store original environment variables
        $this->originalEnv = $_ENV;
        
        // Reset logger for clean test state
        Logger::reset();
        
        // Reset Config singleton
        $reflection = new ReflectionClass(Config::class);
        $instance = $reflection->getProperty('instance');
        $instance->setAccessible(true);
        $instance->setValue(null, null);
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        
        // Restore original environment variables
        $_ENV = $this->originalEnv;
        
        Logger::reset();
        
        // Reset Config singleton
        $reflection = new ReflectionClass(Config::class);
        $instance = $reflection->getProperty('instance');
        $instance->setAccessible(true);
        $instance->setValue(null, null);
    }

    public function testConstructorInitializesExchangeWithApiKeys(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $this->assertInstanceOf(ExchangeService::class, $exchangeService);
        $this->assertFalse($exchangeService->isSandbox());
    }

    public function testConstructorInitializesExchangeWithoutApiKeys(): void
    {
        // Don't set API keys
        $_ENV['BINANCE_API_KEY'] = null;
        $_ENV['BINANCE_SECRET_KEY'] = null;
        
        $exchangeService = new ExchangeService();
        
        $this->assertInstanceOf(ExchangeService::class, $exchangeService);
        $this->assertTrue($exchangeService->isSandbox());
    }

    public function testGetExchangeReturnsExchangeInstance(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        $exchange = $exchangeService->getExchange();
        
        $this->assertInstanceOf(Exchange::class, $exchange);
    }

    public function testFetchSymbolsReturnsFormattedArray(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        // Create exchange service
        $exchangeService = new ExchangeService();
        
        // Mock the exchange object
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('load_markets')
            ->willReturn([
                'BTC/USDT' => [
                    'symbol' => 'BTC/USDT',
                    'base' => 'BTC',
                    'quote' => 'USDT', 
                    'active' => true,
                    'spot' => true,
                    'margin' => false,
                    'future' => false,
                    'precision' => ['amount' => 8, 'price' => 2],
                    'limits' => [
                        'amount' => ['min' => 0.00001, 'max' => 9000],
                        'price' => ['min' => 0.01, 'max' => 1000000],
                        'cost' => ['min' => 10, 'max' => null]
                    ]
                ],
                'ETH/BTC' => [
                    'symbol' => 'ETH/BTC',
                    'base' => 'ETH',
                    'quote' => 'BTC',
                    'active' => false, // Should be filtered out
                    'spot' => true,
                ]
            ]);

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $symbols = $exchangeService->fetchSymbols();
        
        $this->assertIsArray($symbols);
        $this->assertCount(1, $symbols); // Only active symbols
        
        $symbol = $symbols[0];
        $this->assertEquals('BTC/USDT', $symbol['symbol']);
        $this->assertEquals('BTC', $symbol['base']);
        $this->assertEquals('USDT', $symbol['quote']);
        $this->assertTrue($symbol['active']);
        $this->assertTrue($symbol['spot']);
        $this->assertArrayHasKey('precision', $symbol);
        $this->assertArrayHasKey('limits', $symbol);
    }

    public function testFetchSymbolsThrowsExceptionOnError(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        // Mock the exchange to throw an exception
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('load_markets')
            ->willThrowException(new \Exception('Network error'));

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Failed to fetch symbols: Network error');
        
        $exchangeService->fetchSymbols();
    }

    public function testFetchTickerReturnsFormattedData(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockTicker = [
            'symbol' => 'BTC/USDT',
            'timestamp' => 1640995200000,
            'datetime' => '2022-01-01T00:00:00.000Z',
            'high' => 50000.0,
            'low' => 45000.0,
            'bid' => 49000.0,
            'bidVolume' => 1.5,
            'ask' => 49100.0,
            'askVolume' => 2.0,
            'vwap' => 48500.0,
            'open' => 47000.0,
            'close' => 49050.0,
            'last' => 49050.0,
            'previousClose' => 47000.0,
            'change' => 2050.0,
            'percentage' => 4.36,
            'average' => 48025.0,
            'baseVolume' => 1000.0,
            'quoteVolume' => 48500000.0,
            'info' => []
        ];
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('fetch_ticker')
            ->with('BTC/USDT')
            ->willReturn($mockTicker);

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $ticker = $exchangeService->fetchTicker('BTC/USDT');
        
        $this->assertIsArray($ticker);
        $this->assertEquals('BTC/USDT', $ticker['symbol']);
        $this->assertEquals(1640995200000, $ticker['timestamp']);
        $this->assertEquals(50000.0, $ticker['high']);
        $this->assertEquals(45000.0, $ticker['low']);
        $this->assertEquals(49000.0, $ticker['bid']);
        $this->assertEquals(49100.0, $ticker['ask']);
        $this->assertEquals(49050.0, $ticker['last']);
    }

    public function testFetchTickerThrowsExceptionOnError(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('fetch_ticker')
            ->willThrowException(new \Exception('Symbol not found'));

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Failed to fetch ticker for BTC/USDT: Symbol not found');
        
        $exchangeService->fetchTicker('BTC/USDT');
    }

    public function testFetchOrderBookReturnsFormattedData(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockOrderBook = [
            'timestamp' => 1640995200000,
            'datetime' => '2022-01-01T00:00:00.000Z',
            'nonce' => 12345,
            'bids' => [[49000.0, 1.5], [48900.0, 2.0]],
            'asks' => [[49100.0, 1.2], [49200.0, 1.8]],
            'info' => []
        ];
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('fetch_order_book')
            ->with('BTC/USDT', 100)
            ->willReturn($mockOrderBook);

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $orderBook = $exchangeService->fetchOrderBook('BTC/USDT');
        
        $this->assertIsArray($orderBook);
        $this->assertEquals('BTC/USDT', $orderBook['symbol']);
        $this->assertEquals(1640995200000, $orderBook['timestamp']);
        $this->assertEquals(12345, $orderBook['nonce']);
        $this->assertCount(2, $orderBook['bids']);
        $this->assertCount(2, $orderBook['asks']);
        $this->assertEquals([49000.0, 1.5], $orderBook['bids'][0]);
        $this->assertEquals([49100.0, 1.2], $orderBook['asks'][0]);
    }

    public function testFetchOrderBookWithCustomLimit(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->expects($this->once())
            ->method('fetch_order_book')
            ->with('BTC/USDT', 50)
            ->willReturn([
                'timestamp' => 1640995200000,
                'datetime' => '2022-01-01T00:00:00.000Z',
                'bids' => [],
                'asks' => []
            ]);

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $exchangeService->fetchOrderBook('BTC/USDT', 50);
    }

    public function testFetchOrderBookThrowsExceptionOnError(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('fetch_order_book')
            ->willThrowException(new \Exception('Rate limit exceeded'));

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Failed to fetch order book for BTC/USDT: Rate limit exceeded');
        
        $exchangeService->fetchOrderBook('BTC/USDT');
    }

    public function testFetchOHLCVReturnsFormattedData(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockOHLCV = [
            [1640995200000, 47000.0, 50000.0, 45000.0, 49000.0, 1000.0],
            [1640995260000, 49000.0, 51000.0, 48000.0, 50000.0, 1200.0]
        ];
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('fetch_ohlcv')
            ->with('BTC/USDT', '1h', null, 100)
            ->willReturn($mockOHLCV);

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $candles = $exchangeService->fetchOHLCV('BTC/USDT');
        
        $this->assertIsArray($candles);
        $this->assertCount(2, $candles);
        
        $firstCandle = $candles[0];
        $this->assertEquals(1640995200000, $firstCandle['timestamp']);
        $this->assertEquals(47000.0, $firstCandle['open']);
        $this->assertEquals(50000.0, $firstCandle['high']);
        $this->assertEquals(45000.0, $firstCandle['low']);
        $this->assertEquals(49000.0, $firstCandle['close']);
        $this->assertEquals(1000.0, $firstCandle['volume']);
        $this->assertArrayHasKey('datetime', $firstCandle);
    }

    public function testFetchOHLCVWithCustomParameters(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->expects($this->once())
            ->method('fetch_ohlcv')
            ->with('BTC/USDT', '15m', null, 50)
            ->willReturn([]);

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $exchangeService->fetchOHLCV('BTC/USDT', '15m', 50);
    }

    public function testFetchOHLCVThrowsExceptionOnError(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $mockExchange = $this->createMock(\ccxt\binance::class);
        $mockExchange->method('fetch_ohlcv')
            ->willThrowException(new \Exception('Invalid timeframe'));

        // Use reflection to replace the exchange instance
        $reflection = new ReflectionClass($exchangeService);
        $exchangeProperty = $reflection->getProperty('exchange');
        $exchangeProperty->setAccessible(true);
        $exchangeProperty->setValue($exchangeService, $mockExchange);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Failed to fetch OHLCV data for BTC/USDT: Invalid timeframe');
        
        $exchangeService->fetchOHLCV('BTC/USDT');
    }

    public function testIsSandboxReturnsTrueInSandboxMode(): void
    {
        $_ENV['BINANCE_API_KEY'] = null;
        $_ENV['BINANCE_SECRET_KEY'] = null;
        
        $exchangeService = new ExchangeService();
        
        $this->assertTrue($exchangeService->isSandbox());
    }

    public function testIsSandboxReturnsFalseInLiveMode(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $exchangeService = new ExchangeService();
        
        $this->assertFalse($exchangeService->isSandbox());
    }
}