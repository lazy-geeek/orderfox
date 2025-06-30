<?php

namespace OrderFox\Core;

use Dotenv\Dotenv;

class Config
{
    private static ?Config $instance = null;
    
    // Binance API Configuration
    public readonly ?string $binanceApiKey;
    public readonly ?string $binanceSecretKey;
    
    // Firebase Configuration
    public readonly ?string $firebaseConfigJson;
    
    // API Configuration
    public readonly string $apiV1Str;
    public readonly string $projectName;
    
    // Market Data Configuration
    public readonly int $maxOrderbookLimit;
    
    // Development settings
    public readonly bool $debug;
    
    private function __construct()
    {
        $this->loadEnvironmentVariables();
        
        // Initialize configuration values
        $this->binanceApiKey = $_ENV['BINANCE_API_KEY'] ?? null;
        $this->binanceSecretKey = $_ENV['BINANCE_SECRET_KEY'] ?? null;
        $this->firebaseConfigJson = $_ENV['FIREBASE_CONFIG_JSON'] ?? null;
        $this->apiV1Str = '/api/v1';
        $this->projectName = 'Trading Bot API';
        $this->maxOrderbookLimit = (int)($_ENV['MAX_ORDERBOOK_LIMIT'] ?? 5000);
        $this->debug = strtolower($_ENV['DEBUG'] ?? 'false') === 'true';
        
        $this->validateConfiguration();
    }
    
    public static function getInstance(): Config
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function loadEnvironmentVariables(): void
    {
        // Try multiple locations for .env file (matching Python version)
        $envPaths = [
            '.env',                    // Current directory
            '../.env',                 // Parent directory (if running from backend_php/)
            '../../.env',              // Grandparent directory (if running from backend_php/src/)
            __DIR__ . '/../../.env',   // Relative to this file
            __DIR__ . '/../../../.env' // Project root from this file
        ];
        
        $envLoaded = false;
        foreach ($envPaths as $envPath) {
            if (file_exists($envPath)) {
                $dotenv = Dotenv::createImmutable(dirname($envPath), basename($envPath));
                $dotenv->safeLoad();
                $envLoaded = true;
                error_log("Loaded environment variables from: {$envPath}");
                break;
            }
        }
        
        if (!$envLoaded) {
            error_log("Warning: No .env file found in expected locations");
        }
    }
    
    private function validateConfiguration(): void
    {
        if (empty($this->binanceApiKey)) {
            echo "Warning: BINANCE_API_KEY not found in environment variables\n";
        }
        if (empty($this->binanceSecretKey)) {
            echo "Warning: BINANCE_SECRET_KEY not found in environment variables\n";
        }
    }
    
    /**
     * Get configuration as array for debugging
     */
    public function toArray(): array
    {
        return [
            'binanceApiKey' => $this->binanceApiKey ? 'Set (****)' : 'Not set',
            'binanceSecretKey' => $this->binanceSecretKey ? 'Set (****)' : 'Not set',
            'firebaseConfigJson' => $this->firebaseConfigJson ? 'Set' : 'Not set',
            'apiV1Str' => $this->apiV1Str,
            'projectName' => $this->projectName,
            'maxOrderbookLimit' => $this->maxOrderbookLimit,
            'debug' => $this->debug
        ];
    }
}