<?php

declare(strict_types=1);

namespace Tests\Unit\Services;

use OrderFox\Services\SymbolService;
use OrderFox\Services\ExchangeService;
use OrderFox\Core\Logger;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;

class SymbolServiceTest extends TestCase
{
    private SymbolService $symbolService;
    private MockObject $mockExchangeService;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Reset logger for clean test state
        Logger::reset();
        
        // Create mock exchange service
        $this->mockExchangeService = $this->createMock(ExchangeService::class);
        
        // Create symbol service with mock
        $this->symbolService = new SymbolService($this->mockExchangeService);
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        Logger::reset();
    }

    private function getMockSymbols(): array
    {
        return [
            ['symbol' => 'BTC/USDT'],
            ['symbol' => 'ETH/USDT'],
            ['symbol' => 'BNB/USDT'],
            ['symbol' => 'ADA/USDT'],
            ['symbol' => 'DOT/USDT'],
            ['symbol' => 'BTC/BNB'],
            ['symbol' => 'ETH/BTC'],
            ['symbol' => 'LINK/USDT'],
            ['symbol' => 'UNI/USDT'],
            ['symbol' => 'SOL/USDT']
        ];
    }

    public function testResolveSymbolDirectMatch(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $result = $this->symbolService->resolveSymbol('BTC/USDT');
        
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testResolveSymbolCaseInsensitiveMatch(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $result = $this->symbolService->resolveSymbol('btc/usdt');
        
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testResolveSymbolWithoutSlash(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $result = $this->symbolService->resolveSymbol('BTCUSDT');
        
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testResolveSymbolRemoveSlashAndReAdd(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        // Test with incorrect slash position
        $result = $this->symbolService->resolveSymbol('BTCU/SDT');
        
        // Should normalize to BTC/USDT
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testResolveSymbolFuzzyMatch(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $result = $this->symbolService->resolveSymbol('BTCUSD');
        
        // Should find BTC/USDT as closest match
        $this->assertEquals('BTC/USDT', $result);
    }

    public function testResolveSymbolInvalidThrowsException(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage("Symbol 'INVALIDXYZ' not found or not supported");
        
        $this->symbolService->resolveSymbol('INVALIDXYZ');
    }

    public function testIsValidSymbolFormatValid(): void
    {
        $this->assertTrue($this->symbolService->isValidSymbolFormat('BTC/USDT'));
        $this->assertTrue($this->symbolService->isValidSymbolFormat('ETH/BTC'));
        $this->assertTrue($this->symbolService->isValidSymbolFormat('LINK123/USDT456'));
    }

    public function testIsValidSymbolFormatInvalid(): void
    {
        $this->assertFalse($this->symbolService->isValidSymbolFormat('BTCUSDT')); // No slash
        $this->assertFalse($this->symbolService->isValidSymbolFormat('BTC/US/DT')); // Multiple slashes
        $this->assertFalse($this->symbolService->isValidSymbolFormat('B/USDT')); // Base too short
        $this->assertFalse($this->symbolService->isValidSymbolFormat('BTC/U')); // Quote too short
        $this->assertFalse($this->symbolService->isValidSymbolFormat('BTC/')); // Empty quote
        $this->assertFalse($this->symbolService->isValidSymbolFormat('/USDT')); // Empty base
        $this->assertFalse($this->symbolService->isValidSymbolFormat('BTC/USD-T')); // Invalid characters
    }

    public function testGetSymbolSuggestions(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $suggestions = $this->symbolService->getSymbolSuggestions('BTC', 3);
        
        $this->assertIsArray($suggestions);
        $this->assertLessThanOrEqual(3, count($suggestions));
        $this->assertContains('BTC/USDT', $suggestions);
        $this->assertContains('BTC/BNB', $suggestions);
    }

    public function testGetSymbolSuggestionsShortQuery(): void
    {
        $suggestions = $this->symbolService->getSymbolSuggestions('B');
        
        $this->assertEmpty($suggestions);
    }

    public function testClearCache(): void
    {
        // First call to populate cache
        $this->mockExchangeService
            ->expects($this->exactly(2))
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $this->symbolService->resolveSymbol('BTC/USDT');
        
        // Clear cache
        $this->symbolService->clearCache();
        
        // Next call should fetch symbols again
        $this->symbolService->resolveSymbol('ETH/USDT');
    }

    public function testGetCacheStats(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        // Populate cache
        $this->symbolService->resolveSymbol('BTC/USDT');
        
        $stats = $this->symbolService->getCacheStats();
        
        $this->assertIsArray($stats);
        $this->assertArrayHasKey('cached_symbols', $stats);
        $this->assertArrayHasKey('cache_age_seconds', $stats);
        $this->assertArrayHasKey('cache_expiry_seconds', $stats);
        $this->assertArrayHasKey('is_cache_valid', $stats);
        
        $this->assertEquals(10, $stats['cached_symbols']); // Mock symbols count
        $this->assertTrue($stats['is_cache_valid']);
        $this->assertGreaterThanOrEqual(0, $stats['cache_age_seconds']);
        $this->assertEquals(3600, $stats['cache_expiry_seconds']);
    }

    public function testCacheExpiryBehavior(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        // Populate cache
        $this->symbolService->resolveSymbol('BTC/USDT');
        
        // Second call should use cache (not call fetchSymbols again)
        $result = $this->symbolService->resolveSymbol('ETH/USDT');
        $this->assertEquals('ETH/USDT', $result);
    }

    public function testAddSlashToSymbolCommonQuotes(): void
    {
        // Test with reflection to access private method
        $reflection = new \ReflectionClass($this->symbolService);
        $method = $reflection->getMethod('addSlashToSymbol');
        $method->setAccessible(true);

        $this->assertEquals('BTC/USDT', $method->invoke($this->symbolService, 'BTCUSDT'));
        $this->assertEquals('ETH/USDC', $method->invoke($this->symbolService, 'ETHUSDC'));
        $this->assertEquals('BNB/BTC', $method->invoke($this->symbolService, 'BNBBTC'));
        $this->assertEquals('LINK/ETH', $method->invoke($this->symbolService, 'LINKETH'));
    }

    public function testAddSlashToSymbolFallback(): void
    {
        $reflection = new \ReflectionClass($this->symbolService);
        $method = $reflection->getMethod('addSlashToSymbol');
        $method->setAccessible(true);

        // Test with uncommon quote currency
        $result = $method->invoke($this->symbolService, 'ABCDEFG');
        $this->assertEquals('ABC/DEFG', $result); // Should split at 3 chars
    }

    public function testAddSlashToSymbolInvalid(): void
    {
        $reflection = new \ReflectionClass($this->symbolService);
        $method = $reflection->getMethod('addSlashToSymbol');
        $method->setAccessible(true);

        // Too short
        $this->assertNull($method->invoke($this->symbolService, 'AB'));
        $this->assertNull($method->invoke($this->symbolService, 'ABCD')); // 4 chars but no common quote
    }

    public function testFindSimilarSymbols(): void
    {
        $reflection = new \ReflectionClass($this->symbolService);
        $method = $reflection->getMethod('findSimilarSymbols');
        $method->setAccessible(true);

        $availableSymbols = array_flip(['BTC/USDT', 'ETH/USDT', 'BTC/BNB', 'LTC/USDT']);
        
        $suggestions = $method->invoke($this->symbolService, 'BTCUSD', $availableSymbols);
        
        $this->assertIsArray($suggestions);
        $this->assertContains('BTC/USDT', $suggestions);
    }

    public function testExchangeServiceFallsBackToDefault(): void
    {
        // Create service without providing exchange service
        $service = new SymbolService();
        
        // This should not throw an error and should create a default exchange service
        $this->assertInstanceOf(SymbolService::class, $service);
    }

    public function testExchangeServiceExceptionHandling(): void
    {
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willThrowException(new \Exception('Exchange API error'));

        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('Exchange API error');
        
        $this->symbolService->resolveSymbol('BTC/USDT');
    }

    public function testExchangeServiceExceptionWithStaleCache(): void
    {
        // First populate cache successfully
        $this->mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willReturn($this->getMockSymbols());

        $this->symbolService->resolveSymbol('BTC/USDT');
        
        // Manually set up stale cache and make next fetchSymbols call fail
        $reflection = new \ReflectionClass($this->symbolService);
        $cacheProperty = $reflection->getProperty('symbolCache');
        $cacheProperty->setAccessible(true);
        $cacheProperty->setValue($this->symbolService, ['BTC/USDT' => ['symbol' => 'BTC/USDT']]);
        
        // Set cache timestamp to expired
        $timestampProperty = $reflection->getProperty('cacheTimestamp');
        $timestampProperty->setAccessible(true);
        $timestampProperty->setValue($this->symbolService, time() - 7200); // 2 hours ago

        // Create a new service with a mock that throws exception
        $mockExchangeService = $this->createMock(ExchangeService::class);
        $mockExchangeService
            ->expects($this->once())
            ->method('fetchSymbols')
            ->willThrowException(new \Exception('Network error'));
            
        $symbolService = new SymbolService($mockExchangeService);
        
        // Set up stale cache on new service
        $cacheProperty->setValue($symbolService, ['BTC/USDT' => ['symbol' => 'BTC/USDT']]);
        $timestampProperty->setValue($symbolService, time() - 7200);

        // Should use stale cache instead of throwing
        $result = $symbolService->resolveSymbol('BTC/USDT');
        $this->assertEquals('BTC/USDT', $result);
    }
}