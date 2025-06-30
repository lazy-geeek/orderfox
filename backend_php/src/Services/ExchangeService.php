<?php

declare(strict_types=1);

namespace OrderFox\Services;

use OrderFox\Core\Config;
use OrderFox\Core\Logger;
use ccxt\Exchange;
use ccxt\binance;

class ExchangeService
{
    private \Monolog\Logger $logger;
    private Config $config;
    private Exchange $exchange;

    public function __construct()
    {
        $this->logger = Logger::getLogger('exchange');
        $this->config = Config::getInstance();
        $this->initializeExchange();
    }

    private function initializeExchange(): void
    {
        try {
            $exchangeConfig = [
                'apiKey' => $this->config->binanceApiKey,
                'secret' => $this->config->binanceSecretKey,
                'timeout' => 30000,
                'rateLimit' => 1200,
                'enableRateLimit' => true,
                'options' => [
                    'adjustForTimeDifference' => true,
                ],
            ];

            // Enable sandbox/paper trading mode if no API keys provided
            if (empty($this->config->binanceApiKey) || empty($this->config->binanceSecretKey)) {
                $this->logger->info('No API keys provided, enabling paper trading mode');
                $exchangeConfig['sandbox'] = true;
            } else {
                $this->logger->info('API keys provided, using live mode');
                $exchangeConfig['sandbox'] = false;
            }

            $this->exchange = new binance($exchangeConfig);

            $this->logger->info('Exchange initialized successfully', [
                'exchange' => 'binance',
                'sandbox' => $exchangeConfig['sandbox'],
                'rateLimit' => $exchangeConfig['rateLimit']
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Failed to initialize exchange', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            throw new \RuntimeException('Exchange initialization failed: ' . $e->getMessage());
        }
    }

    /**
     * Fetch all available trading symbols
     */
    public function fetchSymbols(): array
    {
        try {
            $this->logger->debug('Fetching markets from exchange');
            
            $markets = $this->exchange->load_markets();
            
            $symbols = [];
            foreach ($markets as $market) {
                if ($market['active'] && $market['spot']) {
                    $symbols[] = [
                        'symbol' => $market['symbol'],
                        'base' => $market['base'],
                        'quote' => $market['quote'],
                        'active' => $market['active'],
                        'spot' => $market['spot'],
                        'margin' => $market['margin'] ?? false,
                        'future' => $market['future'] ?? false,
                        'option' => $market['option'] ?? false,
                        'contract' => $market['contract'] ?? false,
                        'precision' => [
                            'amount' => $market['precision']['amount'] ?? null,
                            'price' => $market['precision']['price'] ?? null,
                        ],
                        'limits' => [
                            'amount' => [
                                'min' => $market['limits']['amount']['min'] ?? null,
                                'max' => $market['limits']['amount']['max'] ?? null,
                            ],
                            'price' => [
                                'min' => $market['limits']['price']['min'] ?? null,
                                'max' => $market['limits']['price']['max'] ?? null,
                            ],
                            'cost' => [
                                'min' => $market['limits']['cost']['min'] ?? null,
                                'max' => $market['limits']['cost']['max'] ?? null,
                            ],
                        ],
                    ];
                }
            }

            $this->logger->info('Successfully fetched symbols', ['count' => count($symbols)]);
            
            return $symbols;

        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch symbols', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            throw new \RuntimeException('Failed to fetch symbols: ' . $e->getMessage());
        }
    }

    /**
     * Fetch ticker data for a specific symbol
     */
    public function fetchTicker(string $symbol): array
    {
        try {
            $this->logger->debug('Fetching ticker', ['symbol' => $symbol]);
            
            $ticker = $this->exchange->fetch_ticker($symbol);
            
            $formattedTicker = [
                'symbol' => $ticker['symbol'],
                'timestamp' => $ticker['timestamp'],
                'datetime' => $ticker['datetime'],
                'high' => $ticker['high'],
                'low' => $ticker['low'],
                'bid' => $ticker['bid'],
                'bidVolume' => $ticker['bidVolume'],
                'ask' => $ticker['ask'],
                'askVolume' => $ticker['askVolume'],
                'vwap' => $ticker['vwap'],
                'open' => $ticker['open'],
                'close' => $ticker['close'],
                'last' => $ticker['last'],
                'previousClose' => $ticker['previousClose'],
                'change' => $ticker['change'],
                'percentage' => $ticker['percentage'],
                'average' => $ticker['average'],
                'baseVolume' => $ticker['baseVolume'],
                'quoteVolume' => $ticker['quoteVolume'],
                'info' => $ticker['info'] ?? null,
            ];

            $this->logger->debug('Successfully fetched ticker', [
                'symbol' => $symbol,
                'price' => $ticker['last']
            ]);
            
            return $formattedTicker;

        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch ticker', [
                'symbol' => $symbol,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            throw new \RuntimeException("Failed to fetch ticker for {$symbol}: " . $e->getMessage());
        }
    }

    /**
     * Fetch order book data for a specific symbol
     */
    public function fetchOrderBook(string $symbol, int $limit = 100): array
    {
        try {
            $this->logger->debug('Fetching order book', [
                'symbol' => $symbol,
                'limit' => $limit
            ]);
            
            $orderBook = $this->exchange->fetch_order_book($symbol, $limit);
            
            $formattedOrderBook = [
                'symbol' => $symbol,
                'timestamp' => $orderBook['timestamp'],
                'datetime' => $orderBook['datetime'],
                'nonce' => $orderBook['nonce'] ?? null,
                'bids' => $orderBook['bids'] ?? [],
                'asks' => $orderBook['asks'] ?? [],
                'info' => $orderBook['info'] ?? null,
            ];

            $this->logger->debug('Successfully fetched order book', [
                'symbol' => $symbol,
                'limit' => $limit,
                'bids' => count($formattedOrderBook['bids']),
                'asks' => count($formattedOrderBook['asks'])
            ]);
            
            return $formattedOrderBook;

        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch order book', [
                'symbol' => $symbol,
                'limit' => $limit,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            throw new \RuntimeException("Failed to fetch order book for {$symbol}: " . $e->getMessage());
        }
    }

    /**
     * Fetch OHLCV (candlestick) data for a specific symbol and timeframe
     */
    public function fetchOHLCV(string $symbol, string $timeframe = '1h', int $limit = 100): array
    {
        try {
            $this->logger->debug('Fetching OHLCV data', [
                'symbol' => $symbol,
                'timeframe' => $timeframe,
                'limit' => $limit
            ]);
            
            $ohlcv = $this->exchange->fetch_ohlcv($symbol, $timeframe, null, $limit);
            
            $formattedCandles = [];
            foreach ($ohlcv as $candle) {
                $formattedCandles[] = [
                    'timestamp' => $candle[0],
                    'datetime' => date('c', $candle[0] / 1000),
                    'open' => $candle[1],
                    'high' => $candle[2],
                    'low' => $candle[3],
                    'close' => $candle[4],
                    'volume' => $candle[5],
                ];
            }

            $this->logger->debug('Successfully fetched OHLCV data', [
                'symbol' => $symbol,
                'timeframe' => $timeframe,
                'limit' => $limit,
                'count' => count($formattedCandles)
            ]);
            
            return $formattedCandles;

        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch OHLCV data', [
                'symbol' => $symbol,
                'timeframe' => $timeframe,
                'limit' => $limit,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            throw new \RuntimeException("Failed to fetch OHLCV data for {$symbol}: " . $e->getMessage());
        }
    }

    /**
     * Get the underlying CCXT exchange instance
     */
    public function getExchange(): Exchange
    {
        return $this->exchange;
    }

    /**
     * Check if exchange is in sandbox/paper trading mode
     */
    public function isSandbox(): bool
    {
        return $this->exchange->sandbox ?? false;
    }
}