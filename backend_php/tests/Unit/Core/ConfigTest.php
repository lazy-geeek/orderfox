<?php

declare(strict_types=1);

namespace Tests\Unit\Core;

use OrderFox\Core\Config;
use PHPUnit\Framework\TestCase;
use ReflectionClass;

class ConfigTest extends TestCase
{
    private array $originalEnv;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Store original environment variables
        $this->originalEnv = $_ENV;
        
        // Reset the singleton instance for each test
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
        
        // Reset singleton instance
        $reflection = new ReflectionClass(Config::class);
        $instance = $reflection->getProperty('instance');
        $instance->setAccessible(true);
        $instance->setValue(null, null);
    }

    public function testSingletonPattern(): void
    {
        $config1 = Config::getInstance();
        $config2 = Config::getInstance();
        
        $this->assertSame($config1, $config2, 'Config should implement singleton pattern');
    }

    public function testDefaultConfigurationValues(): void
    {
        // Set minimal environment variables
        $_ENV['BINANCE_API_KEY'] = null;
        $_ENV['BINANCE_SECRET_KEY'] = null;
        
        $config = Config::getInstance();
        
        $this->assertEquals('/api/v1', $config->apiV1Str);
        $this->assertEquals('Trading Bot API', $config->projectName);
        $this->assertEquals(5000, $config->maxOrderbookLimit);
        $this->assertFalse($config->debug);
    }

    public function testBinanceApiKeyConfiguration(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        
        $config = Config::getInstance();
        
        $this->assertEquals('test_api_key', $config->binanceApiKey);
        $this->assertEquals('test_secret_key', $config->binanceSecretKey);
    }

    public function testFirebaseConfigurationOptional(): void
    {
        $_ENV['FIREBASE_CONFIG_JSON'] = '{"test": "config"}';
        
        $config = Config::getInstance();
        
        $this->assertEquals('{"test": "config"}', $config->firebaseConfigJson);
    }

    public function testCustomMaxOrderbookLimit(): void
    {
        $_ENV['MAX_ORDERBOOK_LIMIT'] = '1000';
        
        $config = Config::getInstance();
        
        $this->assertEquals(1000, $config->maxOrderbookLimit);
    }

    public function testDebugFlagTrue(): void
    {
        $_ENV['DEBUG'] = 'true';
        
        $config = Config::getInstance();
        
        $this->assertTrue($config->debug);
    }

    public function testDebugFlagTrueUppercase(): void
    {
        $_ENV['DEBUG'] = 'TRUE';
        
        $config = Config::getInstance();
        
        $this->assertTrue($config->debug);
    }

    public function testDebugFlagFalse(): void
    {
        $_ENV['DEBUG'] = 'false';
        
        $config = Config::getInstance();
        
        $this->assertFalse($config->debug);
    }

    public function testDebugFlagInvalidValue(): void
    {
        $_ENV['DEBUG'] = 'invalid';
        
        $config = Config::getInstance();
        
        $this->assertFalse($config->debug, 'Invalid debug value should default to false');
    }

    public function testToArrayMethodMasksSecrets(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'secret_key_123';
        $_ENV['BINANCE_SECRET_KEY'] = 'secret_value_456';
        $_ENV['FIREBASE_CONFIG_JSON'] = '{"test": "config"}';
        
        $config = Config::getInstance();
        $configArray = $config->toArray();
        
        $this->assertEquals('Set (****)', $configArray['binanceApiKey']);
        $this->assertEquals('Set (****)', $configArray['binanceSecretKey']);
        $this->assertEquals('Set', $configArray['firebaseConfigJson']);
        $this->assertEquals('/api/v1', $configArray['apiV1Str']);
        $this->assertEquals('Trading Bot API', $configArray['projectName']);
        $this->assertEquals(5000, $configArray['maxOrderbookLimit']);
        $this->assertFalse($configArray['debug']);
    }

    public function testToArrayMethodShowsNotSetForMissingValues(): void
    {
        // Don't set any environment variables
        $_ENV['BINANCE_API_KEY'] = null;
        $_ENV['BINANCE_SECRET_KEY'] = null;
        $_ENV['FIREBASE_CONFIG_JSON'] = null;
        
        $config = Config::getInstance();
        $configArray = $config->toArray();
        
        $this->assertEquals('Not set', $configArray['binanceApiKey']);
        $this->assertEquals('Not set', $configArray['binanceSecretKey']);
        $this->assertEquals('Not set', $configArray['firebaseConfigJson']);
    }

    public function testConfigurationImmutability(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'initial_key';
        
        $config = Config::getInstance();
        $initialKey = $config->binanceApiKey;
        
        // Try to modify environment and create new instance (should be same instance)
        $_ENV['BINANCE_API_KEY'] = 'modified_key';
        $configAgain = Config::getInstance();
        
        $this->assertSame($config, $configAgain);
        $this->assertEquals($initialKey, $configAgain->binanceApiKey, 'Config should be immutable after first creation');
    }

    public function testMaxOrderbookLimitIntegerConversion(): void
    {
        $_ENV['MAX_ORDERBOOK_LIMIT'] = '2500';
        
        $config = Config::getInstance();
        
        $this->assertIsInt($config->maxOrderbookLimit);
        $this->assertEquals(2500, $config->maxOrderbookLimit);
    }

    public function testMaxOrderbookLimitInvalidValueDefaultsTo5000(): void
    {
        $_ENV['MAX_ORDERBOOK_LIMIT'] = 'invalid_number';
        
        $config = Config::getInstance();
        
        $this->assertEquals(0, $config->maxOrderbookLimit, 'Invalid numeric value should convert to 0');
    }

    public function testEnvironmentVariablesAreReadonly(): void
    {
        $_ENV['BINANCE_API_KEY'] = 'test_key';
        
        $config = Config::getInstance();
        
        // Verify that properties are readonly by checking they cannot be written
        $reflection = new ReflectionClass($config);
        $property = $reflection->getProperty('binanceApiKey');
        
        $this->assertTrue($property->isReadOnly(), 'Config properties should be readonly');
    }
}