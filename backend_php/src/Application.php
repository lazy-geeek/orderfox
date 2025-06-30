<?php

declare(strict_types=1);

namespace OrderFox;

use OrderFox\Core\Config;
use OrderFox\Core\Logger;
use OrderFox\Api\V1\Controllers\MarketDataController;
use Slim\Factory\AppFactory;
use Slim\App;
use Slim\Middleware\ErrorMiddleware;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Psr\Http\Server\RequestHandlerInterface as RequestHandler;

class Application
{
    private App $app;
    private Config $config;
    private \Monolog\Logger $logger;

    public function __construct()
    {
        $this->config = Config::getInstance();
        $this->logger = Logger::setup($this->config->debug ? 'DEBUG' : 'INFO');
        Logger::configureExternalLoggers();

        $this->logger->info('Initializing OrderFox PHP Backend', $this->config->toArray());

        $this->app = AppFactory::create();
        $this->setupMiddleware();
        $this->setupRoutes();
    }

    private function setupMiddleware(): void
    {
        // Add error middleware with proper error handling
        $errorMiddleware = $this->app->addErrorMiddleware($this->config->debug, true, true);
        
        // Custom error handler
        $errorHandler = $errorMiddleware->getDefaultErrorHandler();
        $errorHandler->registerErrorRenderer('application/json', function (\Throwable $exception, bool $displayErrorDetails) {
            $this->logger->error('Application error', [
                'message' => $exception->getMessage(),
                'file' => $exception->getFile(),
                'line' => $exception->getLine(),
                'trace' => $displayErrorDetails ? $exception->getTraceAsString() : null
            ]);

            $error = [
                'error' => [
                    'type' => 'internal_error',
                    'message' => $displayErrorDetails ? $exception->getMessage() : 'Internal server error',
                    'timestamp' => date('c')
                ]
            ];

            if ($displayErrorDetails) {
                $error['error']['details'] = [
                    'file' => $exception->getFile(),
                    'line' => $exception->getLine(),
                    'trace' => $exception->getTraceAsString()
                ];
            }

            return json_encode($error, JSON_PRETTY_PRINT);
        });

        // Request/Response logging middleware
        $this->app->add(function (Request $request, RequestHandler $handler) {
            $start = microtime(true);
            $method = $request->getMethod();
            $uri = (string) $request->getUri();
            
            $this->logger->info('Request started', [
                'method' => $method,
                'uri' => $uri,
                'user_agent' => $request->getHeaderLine('User-Agent')
            ]);

            $response = $handler->handle($request);
            
            $duration = round((microtime(true) - $start) * 1000, 2);
            $status = $response->getStatusCode();
            
            $this->logger->info('Request completed', [
                'method' => $method,
                'uri' => $uri,
                'status' => $status,
                'duration_ms' => $duration
            ]);

            return $response;
        });

        // CORS middleware - allow all origins for development
        $this->app->add(function (Request $request, RequestHandler $handler) {
            $response = $handler->handle($request);
            
            return $response
                ->withHeader('Access-Control-Allow-Origin', '*')
                ->withHeader('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept, Origin, Authorization')
                ->withHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
                ->withHeader('Access-Control-Max-Age', '3600');
        });

        // Handle preflight OPTIONS requests
        $this->app->options('/{routes:.+}', function (Request $request, Response $response) {
            return $response->withStatus(204);
        });
    }

    private function setupRoutes(): void
    {
        // Basic health check endpoint
        $this->app->get('/health', function (Request $request, Response $response) {
            $data = [
                'status' => 'healthy',
                'timestamp' => date('c'),
                'service' => 'OrderFox PHP Backend',
                'version' => '1.0.0'
            ];
            
            $response->getBody()->write(json_encode($data));
            return $response
                ->withHeader('Content-Type', 'application/json')
                ->withStatus(200);
        });

        // API v1 routes
        $this->app->group('/api/v1', function ($group) {
            // Status endpoint
            $group->get('/status', function (Request $request, Response $response) {
                $data = [
                    'api_version' => 'v1',
                    'status' => 'ready',
                    'timestamp' => date('c'),
                    'environment' => $this->config->debug ? 'development' : 'production'
                ];
                
                $response->getBody()->write(json_encode($data));
                return $response
                    ->withHeader('Content-Type', 'application/json')
                    ->withStatus(200);
            });

            // Market data routes
            $group->group('/market-data', function ($marketGroup) {
                $controller = new MarketDataController();
                
                $marketGroup->get('/symbols', [$controller, 'getSymbols']);
                $marketGroup->get('/ticker/{symbol}', [$controller, 'getTicker']);
                $marketGroup->get('/orderbook/{symbol}', [$controller, 'getOrderBook']);
                $marketGroup->get('/candles/{symbol}/{timeframe}', [$controller, 'getCandles']);
            });

            // WebSocket routes placeholder  
            $group->group('/ws', function ($wsGroup) {
                // Will be implemented in Phase 3
            });
        });

        $this->logger->info('Application routes configured');
    }

    public function getApp(): App
    {
        return $this->app;
    }

    public function run(): void
    {
        try {
            $this->app->run();
        } catch (\Exception $e) {
            $this->logger->error('Application failed to start', ['error' => $e->getMessage()]);
            throw $e;
        }
    }
}