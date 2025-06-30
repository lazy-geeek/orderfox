<?php

declare(strict_types=1);

namespace OrderFox\Services;

use OrderFox\Core\Config;
use OrderFox\Core\Logger;
use React\EventLoop\Loop;
use React\Promise\Promise;
use React\Promise\PromiseInterface;
use ccxt\Exchange;
use ccxt\binance;

class AsyncExchangeService
{
    private \Monolog\Logger $logger;
    private Config $config;
    private Exchange $exchange;
    private \React\EventLoop\LoopInterface $loop;

    public function __construct()
    {
        $this->logger = Logger::getLogger('async_exchange');
        $this->config = Config::getInstance();
        $this->loop = Loop::get();
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

            $this->logger->info('Async exchange initialized successfully', [
                'exchange' => 'binance',
                'sandbox' => $exchangeConfig['sandbox'],
                'rateLimit' => $exchangeConfig['rateLimit']
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Failed to initialize async exchange', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            throw new \RuntimeException('Async exchange initialization failed: ' . $e->getMessage());
        }
    }

    /**
     * Fetch multiple tickers concurrently
     */
    public function fetchTickersAsync(array $symbols): PromiseInterface
    {
        return new Promise(function ($resolve, $reject) use ($symbols) {
            $promises = [];
            $results = [];
            $completed = 0;
            $total = count($symbols);

            if ($total === 0) {
                $resolve([]);
                return;
            }

            foreach ($symbols as $symbol) {
                $promises[$symbol] = $this->fetchTickerAsync($symbol);
                
                $promises[$symbol]->then(
                    function ($ticker) use ($symbol, &$results, &$completed, $total, $resolve) {
                        $results[$symbol] = $ticker;
                        $completed++;
                        
                        if ($completed === $total) {
                            $resolve($results);
                        }
                    },
                    function ($error) use ($symbol, &$results, &$completed, $total, $resolve, $reject) {
                        $this->logger->error('Failed to fetch ticker in batch', [
                            'symbol' => $symbol,
                            'error' => $error->getMessage()
                        ]);
                        
                        $results[$symbol] = null;
                        $completed++;
                        
                        if ($completed === $total) {
                            $resolve($results);
                        }
                    }
                );
            }
        });
    }

    /**
     * Fetch ticker data asynchronously for a specific symbol
     */
    public function fetchTickerAsync(string $symbol): PromiseInterface
    {
        return new Promise(function ($resolve, $reject) use ($symbol) {
            $this->loop->futureTick(function () use ($symbol, $resolve, $reject) {
                try {
                    $this->logger->debug('Fetching ticker async', ['symbol' => $symbol]);
                    
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

                    $this->logger->debug('Successfully fetched ticker async', [
                        'symbol' => $symbol,
                        'price' => $ticker['last']
                    ]);
                    
                    $resolve($formattedTicker);

                } catch (\Exception $e) {
                    $this->logger->error('Failed to fetch ticker async', [
                        'symbol' => $symbol,
                        'error' => $e->getMessage(),
                        'trace' => $e->getTraceAsString()
                    ]);
                    $reject(new \RuntimeException("Failed to fetch ticker for {$symbol}: " . $e->getMessage()));
                }
            });
        });
    }

    /**
     * Fetch multiple order books concurrently
     */
    public function fetchOrderBooksAsync(array $symbols, int $limit = 100): PromiseInterface
    {
        return new Promise(function ($resolve, $reject) use ($symbols, $limit) {
            $promises = [];
            $results = [];
            $completed = 0;
            $total = count($symbols);

            if ($total === 0) {
                $resolve([]);
                return;
            }

            foreach ($symbols as $symbol) {
                $promises[$symbol] = $this->fetchOrderBookAsync($symbol, $limit);
                
                $promises[$symbol]->then(
                    function ($orderBook) use ($symbol, &$results, &$completed, $total, $resolve) {
                        $results[$symbol] = $orderBook;
                        $completed++;
                        
                        if ($completed === $total) {
                            $resolve($results);
                        }
                    },
                    function ($error) use ($symbol, &$results, &$completed, $total, $resolve) {
                        $this->logger->error('Failed to fetch order book in batch', [
                            'symbol' => $symbol,
                            'error' => $error->getMessage()
                        ]);
                        
                        $results[$symbol] = null;
                        $completed++;
                        
                        if ($completed === $total) {
                            $resolve($results);
                        }
                    }
                );
            }
        });
    }

    /**
     * Fetch order book data asynchronously for a specific symbol
     */
    public function fetchOrderBookAsync(string $symbol, int $limit = 100): PromiseInterface
    {
        return new Promise(function ($resolve, $reject) use ($symbol, $limit) {
            $this->loop->futureTick(function () use ($symbol, $limit, $resolve, $reject) {
                try {
                    $this->logger->debug('Fetching order book async', [
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

                    $this->logger->debug('Successfully fetched order book async', [
                        'symbol' => $symbol,
                        'limit' => $limit,
                        'bids' => count($formattedOrderBook['bids']),
                        'asks' => count($formattedOrderBook['asks'])
                    ]);
                    
                    $resolve($formattedOrderBook);

                } catch (\Exception $e) {
                    $this->logger->error('Failed to fetch order book async', [
                        'symbol' => $symbol,
                        'limit' => $limit,
                        'error' => $e->getMessage(),
                        'trace' => $e->getTraceAsString()
                    ]);
                    $reject(new \RuntimeException("Failed to fetch order book for {$symbol}: " . $e->getMessage()));
                }
            });
        });
    }

    /**
     * Fetch OHLCV data asynchronously for a specific symbol and timeframe
     */
    public function fetchOHLCVAsync(string $symbol, string $timeframe = '1h', int $limit = 100): PromiseInterface
    {
        return new Promise(function ($resolve, $reject) use ($symbol, $timeframe, $limit) {
            $this->loop->futureTick(function () use ($symbol, $timeframe, $limit, $resolve, $reject) {
                try {
                    $this->logger->debug('Fetching OHLCV data async', [
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

                    $this->logger->debug('Successfully fetched OHLCV data async', [
                        'symbol' => $symbol,
                        'timeframe' => $timeframe,
                        'limit' => $limit,
                        'count' => count($formattedCandles)
                    ]);
                    
                    $resolve($formattedCandles);

                } catch (\Exception $e) {
                    $this->logger->error('Failed to fetch OHLCV data async', [
                        'symbol' => $symbol,
                        'timeframe' => $timeframe,
                        'limit' => $limit,
                        'error' => $e->getMessage(),
                        'trace' => $e->getTraceAsString()
                    ]);
                    $reject(new \RuntimeException("Failed to fetch OHLCV data for {$symbol}: " . $e->getMessage()));
                }
            });
        });
    }

    /**
     * Get the underlying CCXT exchange instance
     */
    public function getExchange(): Exchange
    {
        return $this->exchange;
    }

    /**
     * Get the ReactPHP event loop
     */
    public function getLoop(): \React\EventLoop\LoopInterface
    {
        return $this->loop;
    }

    /**
     * Check if exchange is in sandbox/paper trading mode
     */
    public function isSandbox(): bool
    {
        return $this->exchange->sandbox ?? false;
    }
}