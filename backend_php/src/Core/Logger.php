<?php

namespace OrderFox\Core;

use Monolog\Logger as MonologLogger;
use Monolog\Handler\StreamHandler;
use Monolog\Formatter\LineFormatter;
use Monolog\Level;

class Logger
{
    private static array $loggers = [];
    private static bool $configured = false;
    
    /**
     * Setup application logging with the specified log level
     */
    public static function setup(string $logLevel = 'INFO'): MonologLogger
    {
        if (self::$configured) {
            return self::$loggers['trading_bot'];
        }
        
        // Create main logger
        $logger = new MonologLogger('trading_bot');
        
        // Convert string log level to Monolog Level
        $level = self::parseLogLevel($logLevel);
        
        // Create formatter (matching Python format)
        $formatter = new LineFormatter(
            "%datetime% - %channel% - %level_name% - %message%\n",
            "Y-m-d H:i:s"
        );
        
        // Create console handler (stdout)
        $streamHandler = new StreamHandler('php://stdout', $level);
        $streamHandler->setFormatter($formatter);
        
        $logger->pushHandler($streamHandler);
        
        // Store main logger
        self::$loggers['trading_bot'] = $logger;
        self::$configured = true;
        
        return $logger;
    }
    
    /**
     * Get a logger instance for a specific module
     */
    public static function getLogger(string $name): MonologLogger
    {
        if (!self::$configured) {
            self::setup();
        }
        
        $fullName = "trading_bot.$name";
        
        if (!isset(self::$loggers[$fullName])) {
            $logger = new MonologLogger($fullName);
            
            // Use same handlers as main logger
            $mainLogger = self::$loggers['trading_bot'];
            foreach ($mainLogger->getHandlers() as $handler) {
                $logger->pushHandler($handler);
            }
            
            self::$loggers[$fullName] = $logger;
        }
        
        return self::$loggers[$fullName];
    }
    
    /**
     * Configure external library logging to reduce noise
     */
    public static function configureExternalLoggers(): void
    {
        // Note: PHP doesn't have direct equivalents to Python's urllib3, httpx etc.
        // CCXT PHP library uses its own internal logging
        // We can suppress PHP warnings/notices if needed in production
        
        if (!Config::getInstance()->debug) {
            // Reduce error reporting in production to match Python behavior
            error_reporting(E_ERROR | E_PARSE);
        }
    }
    
    /**
     * Parse string log level to Monolog Level enum
     */
    private static function parseLogLevel(string $logLevel): Level
    {
        return match (strtoupper($logLevel)) {
            'DEBUG' => Level::Debug,
            'INFO' => Level::Info,
            'WARNING', 'WARN' => Level::Warning,
            'ERROR' => Level::Error,
            'CRITICAL' => Level::Critical,
            default => Level::Info
        };
    }
    
    /**
     * Get all configured loggers (for testing/debugging)
     */
    public static function getLoggers(): array
    {
        return self::$loggers;
    }
    
    /**
     * Reset logger configuration (for testing)
     */
    public static function reset(): void
    {
        self::$loggers = [];
        self::$configured = false;
    }
}