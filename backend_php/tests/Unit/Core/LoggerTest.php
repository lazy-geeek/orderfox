<?php

declare(strict_types=1);

namespace Tests\Unit\Core;

use OrderFox\Core\Logger;
use OrderFox\Core\Config;
use Monolog\Logger as MonologLogger;
use Monolog\Level;
use PHPUnit\Framework\TestCase;
use ReflectionClass;

class LoggerTest extends TestCase
{
    private array $originalEnv;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Store original environment variables
        $this->originalEnv = $_ENV;
        
        // Reset logger state before each test
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
        
        // Reset logger state after each test
        Logger::reset();
        
        // Reset Config singleton
        $reflection = new ReflectionClass(Config::class);
        $instance = $reflection->getProperty('instance');
        $instance->setAccessible(true);
        $instance->setValue(null, null);
    }

    public function testSetupReturnsMonologLogger(): void
    {
        $logger = Logger::setup();
        
        $this->assertInstanceOf(MonologLogger::class, $logger);
        $this->assertEquals('trading_bot', $logger->getName());
    }

    public function testSetupWithCustomLogLevel(): void
    {
        $logger = Logger::setup('DEBUG');
        
        $this->assertInstanceOf(MonologLogger::class, $logger);
        
        // Verify that the logger has handlers with the correct level
        $handlers = $logger->getHandlers();
        $this->assertNotEmpty($handlers);
        $this->assertEquals(Level::Debug, $handlers[0]->getLevel());
    }

    public function testSetupIsIdempotent(): void
    {
        $logger1 = Logger::setup('INFO');
        $logger2 = Logger::setup('DEBUG'); // Should return same logger, not reconfigure
        
        // Both should be the same instance and return the main logger
        $this->assertSame($logger1, $logger2);
        $this->assertEquals('trading_bot', $logger1->getName());
        $this->assertEquals('trading_bot', $logger2->getName());
    }

    public function testGetLoggerCreatesNamedLogger(): void
    {
        $logger = Logger::getLogger('test_module');
        
        $this->assertInstanceOf(MonologLogger::class, $logger);
        $this->assertEquals('trading_bot.test_module', $logger->getName());
    }

    public function testGetLoggerReturnsExistingLogger(): void
    {
        $logger1 = Logger::getLogger('test_module');
        $logger2 = Logger::getLogger('test_module');
        
        $this->assertSame($logger1, $logger2);
    }

    public function testGetLoggerSetsUpMainLoggerIfNotConfigured(): void
    {
        // Logger should auto-setup if not already configured
        $logger = Logger::getLogger('auto_setup_test');
        
        $this->assertInstanceOf(MonologLogger::class, $logger);
        
        // Main logger should also be created
        $loggers = Logger::getLoggers();
        $this->assertArrayHasKey('trading_bot', $loggers);
    }

    public function testParseLogLevelDebug(): void
    {
        $logger = Logger::setup('DEBUG');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Debug, $handlers[0]->getLevel());
    }

    public function testParseLogLevelInfo(): void
    {
        $logger = Logger::setup('INFO');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Info, $handlers[0]->getLevel());
    }

    public function testParseLogLevelWarning(): void
    {
        $logger = Logger::setup('WARNING');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Warning, $handlers[0]->getLevel());
    }

    public function testParseLogLevelWarn(): void
    {
        $logger = Logger::setup('WARN');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Warning, $handlers[0]->getLevel());
    }

    public function testParseLogLevelError(): void
    {
        $logger = Logger::setup('ERROR');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Error, $handlers[0]->getLevel());
    }

    public function testParseLogLevelCritical(): void
    {
        $logger = Logger::setup('CRITICAL');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Critical, $handlers[0]->getLevel());
    }

    public function testParseLogLevelInvalidDefaultsToInfo(): void
    {
        $logger = Logger::setup('INVALID_LEVEL');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Info, $handlers[0]->getLevel());
    }

    public function testParseLogLevelCaseInsensitive(): void
    {
        $logger = Logger::setup('debug');
        $handlers = $logger->getHandlers();
        
        $this->assertEquals(Level::Debug, $handlers[0]->getLevel());
    }

    public function testGetLoggersReturnsAllLoggers(): void
    {
        Logger::setup();
        Logger::getLogger('module1');
        Logger::getLogger('module2');
        
        $loggers = Logger::getLoggers();
        
        $this->assertArrayHasKey('trading_bot', $loggers);
        $this->assertArrayHasKey('trading_bot.module1', $loggers);
        $this->assertArrayHasKey('trading_bot.module2', $loggers);
    }

    public function testResetClearsAllLoggers(): void
    {
        Logger::setup();
        Logger::getLogger('test_module');
        
        $this->assertNotEmpty(Logger::getLoggers());
        
        Logger::reset();
        
        $this->assertEmpty(Logger::getLoggers());
    }

    public function testResetAllowsReconfiguration(): void
    {
        $logger1 = Logger::setup('INFO');
        Logger::reset();
        $logger2 = Logger::setup('DEBUG');
        
        $this->assertNotSame($logger1, $logger2);
        
        $handlers1 = $logger1->getHandlers();
        $handlers2 = $logger2->getHandlers();
        
        // Should have different log levels after reset and reconfiguration
        $this->assertEquals(Level::Info, $handlers1[0]->getLevel());
        $this->assertEquals(Level::Debug, $handlers2[0]->getLevel());
    }

    public function testConfigureExternalLoggersWithDebugTrue(): void
    {
        $_ENV['DEBUG'] = 'true';
        
        $originalErrorReporting = error_reporting();
        
        Logger::configureExternalLoggers();
        
        // Should not change error reporting when debug is true
        $this->assertEquals($originalErrorReporting, error_reporting());
    }

    public function testConfigureExternalLoggersWithDebugFalse(): void
    {
        $_ENV['DEBUG'] = 'false';
        
        $originalErrorReporting = error_reporting();
        
        Logger::configureExternalLoggers();
        
        // Should reduce error reporting when debug is false
        $this->assertEquals(E_ERROR | E_PARSE, error_reporting());
        
        // Restore original error reporting
        error_reporting($originalErrorReporting);
    }

    public function testLoggerFormatterFormat(): void
    {
        $logger = Logger::setup();
        $handlers = $logger->getHandlers();
        
        $this->assertNotEmpty($handlers);
        
        $formatter = $handlers[0]->getFormatter();
        $this->assertNotNull($formatter);
        
        // Test that the formatter is configured correctly
        $reflection = new ReflectionClass($formatter);
        $formatProperty = $reflection->getProperty('format');
        $formatProperty->setAccessible(true);
        
        $format = $formatProperty->getValue($formatter);
        $this->assertEquals("%datetime% - %channel% - %level_name% - %message%\n", $format);
    }

    public function testMultipleModuleLoggersShareHandlers(): void
    {
        Logger::setup();
        $logger1 = Logger::getLogger('module1');
        $logger2 = Logger::getLogger('module2');
        
        $handlers1 = $logger1->getHandlers();
        $handlers2 = $logger2->getHandlers();
        
        // Both loggers should have the same handlers (shared from main logger)
        $this->assertCount(count($handlers1), $handlers2);
        $this->assertSame($handlers1[0], $handlers2[0]);
    }
}