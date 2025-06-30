<?php

namespace App\WebSocket;

use App\Core\Logger;
use App\Services\ConnectionManager;
use App\WebSocket\Handlers\OrderBookHandler;
use App\WebSocket\Handlers\TickerHandler;
use App\WebSocket\Handlers\CandleHandler;
use Ratchet\MessageComponentInterface;
use Ratchet\ConnectionInterface;
use Ratchet\Http\HttpServer;
use Ratchet\Http\Router;
use Ratchet\Server\IoServer;
use Ratchet\WebSocket\WsServer;
use React\EventLoop\Loop;
use React\Socket\Server as ReactServer;
use Symfony\Component\Routing\Route;
use Symfony\Component\Routing\RouteCollection;
use Symfony\Component\Routing\Matcher\UrlMatcher;
use Symfony\Component\Routing\RequestContext;

class WebSocketServer implements MessageComponentInterface
{
    private Logger $logger;
    private ConnectionManager $connectionManager;
    private array $handlers = [];
    private UrlMatcher $urlMatcher;

    public function __construct()
    {
        $this->logger = new Logger();
        $this->connectionManager = new ConnectionManager();
        $this->setupRoutes();
        $this->setupHandlers();

        $this->logger->info("WebSocket server initialized");
    }

    private function setupRoutes(): void
    {
        $routes = new RouteCollection();

        // Add WebSocket routes
        $routes->add('orderbook', new Route('/ws/orderbook/{symbol}', [], ['symbol' => '[A-Z]+']));
        $routes->add('ticker', new Route('/ws/ticker/{symbol}', [], ['symbol' => '[A-Z]+']));
        $routes->add('candles', new Route('/ws/candles/{symbol}/{timeframe}', [], [
            'symbol' => '[A-Z]+',
            'timeframe' => '1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w|1M'
        ]));

        $context = new RequestContext();
        $this->urlMatcher = new UrlMatcher($routes, $context);

        $this->logger->info("WebSocket routes configured");
    }

    private function setupHandlers(): void
    {
        $this->handlers = [
            'orderbook' => new OrderBookHandler($this->connectionManager, $this->logger),
            'ticker' => new TickerHandler($this->connectionManager, $this->logger),
            'candles' => new CandleHandler($this->connectionManager, $this->logger)
        ];

        $this->logger->info("WebSocket handlers configured");
    }

    public function onOpen(ConnectionInterface $conn): void
    {
        $this->logger->info("New WebSocket connection", [
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);

        // Parse the WebSocket path to determine the handler
        try {
            $path = $conn->httpRequest->getUri()->getPath();
            $this->logger->info("WebSocket connection path: {$path}");

            $match = $this->urlMatcher->match($path);
            $routeName = $match['_route'];
            unset($match['_route']);

            if (!isset($this->handlers[$routeName])) {
                $this->logger->error("No handler found for route: {$routeName}");
                $this->sendError($conn, "Invalid endpoint");
                $conn->close();
                return;
            }

            // Store connection info for later use
            $conn->orderFoxRoute = $routeName;
            $conn->orderFoxParams = $match;

            // Initialize the handler
            $this->handlers[$routeName]->onOpen($conn, $match);

        } catch (\Exception $e) {
            $this->logger->error("Error handling WebSocket connection", [
                'error' => $e->getMessage(),
                'remote_address' => $conn->remoteAddress
            ]);
            $this->sendError($conn, "Invalid request");
            $conn->close();
        }
    }

    public function onMessage(ConnectionInterface $from, $msg): void
    {
        try {
            $data = json_decode($msg, true);
            
            if ($data === null) {
                $this->logger->warning("Invalid JSON received", [
                    'message' => $msg,
                    'resource_id' => $from->resourceId
                ]);
                return;
            }

            // Handle ping/pong messages
            if (isset($data['type']) && $data['type'] === 'ping') {
                $from->send(json_encode(['type' => 'pong']));
                return;
            }

            // Delegate to appropriate handler
            if (isset($from->orderFoxRoute) && isset($this->handlers[$from->orderFoxRoute])) {
                $this->handlers[$from->orderFoxRoute]->onMessage($from, $data);
            }

        } catch (\Exception $e) {
            $this->logger->error("Error processing WebSocket message", [
                'error' => $e->getMessage(),
                'message' => $msg,
                'resource_id' => $from->resourceId
            ]);
        }
    }

    public function onClose(ConnectionInterface $conn): void
    {
        $this->logger->info("WebSocket connection closed", [
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);

        // Delegate to appropriate handler
        if (isset($conn->orderFoxRoute) && isset($this->handlers[$conn->orderFoxRoute])) {
            $this->handlers[$conn->orderFoxRoute]->onClose($conn);
        }
    }

    public function onError(ConnectionInterface $conn, \Exception $e): void
    {
        $this->logger->error("WebSocket error", [
            'error' => $e->getMessage(),
            'remote_address' => $conn->remoteAddress,
            'resource_id' => $conn->resourceId
        ]);

        // Delegate to appropriate handler
        if (isset($conn->orderFoxRoute) && isset($this->handlers[$conn->orderFoxRoute])) {
            $this->handlers[$conn->orderFoxRoute]->onError($conn, $e);
        }

        $conn->close();
    }

    private function sendError(ConnectionInterface $conn, string $message): void
    {
        $errorData = [
            'type' => 'error',
            'message' => $message
        ];

        try {
            $conn->send(json_encode($errorData));
        } catch (\Exception $e) {
            $this->logger->error("Failed to send error message", [
                'error' => $e->getMessage(),
                'original_message' => $message
            ]);
        }
    }

    public static function start(int $port = 8080): void
    {
        $logger = new Logger();
        $logger->info("Starting WebSocket server on port {$port}");

        $loop = Loop::get();
        $webSocketServer = new self();

        // Create the WebSocket server
        $server = new IoServer(
            new HttpServer(
                new Router([
                    '/ws' => new WsServer($webSocketServer)
                ])
            ),
            new ReactServer("0.0.0.0:{$port}", $loop),
            $loop
        );

        $logger->info("WebSocket server started successfully on port {$port}");
        $server->run();
    }
}