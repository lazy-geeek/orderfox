<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\Controllers;

use OrderFox\Core\Logger;
use OrderFox\Services\ExchangeService;
use OrderFox\Services\SymbolService;
use OrderFox\Api\V1\Schemas\TickerRequestSchema;
use OrderFox\Api\V1\Schemas\OrderBookRequestSchema;
use OrderFox\Api\V1\Schemas\CandlesRequestSchema;
use OrderFox\Api\V1\Formatters\ResponseFormatter;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;

class MarketDataController
{
    private \Monolog\Logger $logger;
    private ExchangeService $exchangeService;
    private SymbolService $symbolService;

    public function __construct()
    {
        $this->logger = Logger::getLogger('market_data');
        $this->exchangeService = new ExchangeService();
        $this->symbolService = new SymbolService();
    }

    /**
     * GET /api/v1/symbols
     * Returns list of available trading symbols
     */
    public function getSymbols(Request $request, Response $response): Response
    {
        try {
            $this->logger->info('Fetching available symbols');
            
            $symbols = $this->exchangeService->fetchSymbols();
            
            $this->logger->info('Successfully fetched symbols', ['count' => count($symbols)]);
            
            return ResponseFormatter::symbolsList($response, $symbols);
                
        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch symbols', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return ResponseFormatter::exchangeError($response, 'Failed to fetch symbols: ' . $e->getMessage(), $e);
        }
    }

    /**
     * GET /api/v1/ticker/{symbol}
     * Returns ticker data for a specific symbol
     */
    public function getTicker(Request $request, Response $response, array $args): Response
    {
        try {
            $symbol = $args['symbol'] ?? '';
            
            // Validate request
            $schema = new TickerRequestSchema();
            $requestData = ['symbol' => $symbol];
            
            if (!$schema->validate($requestData)) {
                return ResponseFormatter::validationError($response, $schema->getErrors());
            }
            
            $this->logger->info('Fetching ticker data', ['symbol' => $symbol]);
            
            // Validate and resolve symbol
            $resolvedSymbol = $this->symbolService->resolveSymbol($symbol);
            
            $ticker = $this->exchangeService->fetchTicker($resolvedSymbol);
            
            $this->logger->info('Successfully fetched ticker', ['symbol' => $resolvedSymbol]);
            
            return ResponseFormatter::ticker($response, $ticker);
                
        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch ticker', [
                'symbol' => $symbol ?? 'unknown',
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return ResponseFormatter::exchangeError($response, 'Failed to fetch ticker: ' . $e->getMessage(), $e);
        }
    }

    /**
     * GET /api/v1/orderbook/{symbol}
     * Returns order book data for a specific symbol
     */
    public function getOrderBook(Request $request, Response $response, array $args): Response
    {
        try {
            $symbol = $args['symbol'] ?? '';
            $queryParams = $request->getQueryParams();
            $limit = isset($queryParams['limit']) ? (int) $queryParams['limit'] : 100;
            
            // Validate request
            $schema = new OrderBookRequestSchema();
            $requestData = ['symbol' => $symbol, 'limit' => $limit];
            
            if (!$schema->validate($requestData)) {
                return ResponseFormatter::validationError($response, $schema->getErrors());
            }
            
            $this->logger->info('Fetching order book', [
                'symbol' => $symbol,
                'limit' => $limit
            ]);
            
            // Validate and resolve symbol
            $resolvedSymbol = $this->symbolService->resolveSymbol($symbol);
            
            $orderBook = $this->exchangeService->fetchOrderBook($resolvedSymbol, $limit);
            
            $this->logger->info('Successfully fetched order book', [
                'symbol' => $resolvedSymbol,
                'limit' => $limit,
                'bids' => count($orderBook['bids'] ?? []),
                'asks' => count($orderBook['asks'] ?? [])
            ]);
            
            return ResponseFormatter::orderBook($response, $orderBook);
                
        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch order book', [
                'symbol' => $symbol ?? 'unknown',
                'limit' => $limit ?? 'unknown',
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return ResponseFormatter::exchangeError($response, 'Failed to fetch order book: ' . $e->getMessage(), $e);
        }
    }

    /**
     * GET /api/v1/candles/{symbol}/{timeframe}
     * Returns candlestick data for a specific symbol and timeframe
     */
    public function getCandles(Request $request, Response $response, array $args): Response
    {
        try {
            $symbol = $args['symbol'] ?? '';
            $timeframe = $args['timeframe'] ?? '';
            $queryParams = $request->getQueryParams();
            $limit = isset($queryParams['limit']) ? (int) $queryParams['limit'] : 100;
            
            // Validate request
            $schema = new CandlesRequestSchema();
            $requestData = ['symbol' => $symbol, 'timeframe' => $timeframe, 'limit' => $limit];
            
            if (!$schema->validate($requestData)) {
                return ResponseFormatter::validationError($response, $schema->getErrors());
            }
            
            $this->logger->info('Fetching candles', [
                'symbol' => $symbol,
                'timeframe' => $timeframe,
                'limit' => $limit
            ]);
            
            // Validate and resolve symbol
            $resolvedSymbol = $this->symbolService->resolveSymbol($symbol);
            
            $candles = $this->exchangeService->fetchOHLCV($resolvedSymbol, $timeframe, $limit);
            
            $this->logger->info('Successfully fetched candles', [
                'symbol' => $resolvedSymbol,
                'timeframe' => $timeframe,
                'limit' => $limit,
                'count' => count($candles)
            ]);
            
            return ResponseFormatter::candles($response, $candles);
                
        } catch (\Exception $e) {
            $this->logger->error('Failed to fetch candles', [
                'symbol' => $symbol ?? 'unknown',
                'timeframe' => $timeframe ?? 'unknown',
                'limit' => $limit ?? 'unknown',
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return ResponseFormatter::exchangeError($response, 'Failed to fetch candles: ' . $e->getMessage(), $e);
        }
    }
}