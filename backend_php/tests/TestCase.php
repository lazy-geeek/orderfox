<?php

declare(strict_types=1);

namespace Tests;

use PHPUnit\Framework\TestCase as BaseTestCase;
use Psr\Container\ContainerInterface;
use Slim\App;
use Slim\Factory\AppFactory;
use DI\Container;
use DI\ContainerBuilder;

abstract class TestCase extends BaseTestCase
{
    protected App $app;
    protected ContainerInterface $container;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Create container for dependency injection
        $containerBuilder = new ContainerBuilder();
        $this->container = $containerBuilder->build();
        
        // Create Slim app with test container
        AppFactory::setContainer($this->container);
        $this->app = AppFactory::create();
        
        // Set up test environment variables
        $_ENV['APP_ENV'] = 'testing';
        $_ENV['BINANCE_API_KEY'] = 'test_api_key';
        $_ENV['BINANCE_SECRET_KEY'] = 'test_secret_key';
        $_ENV['DEBUG'] = 'false';
    }

    protected function tearDown(): void
    {
        parent::tearDown();
        
        // Clean up environment variables
        unset($_ENV['APP_ENV']);
        unset($_ENV['BINANCE_API_KEY']);
        unset($_ENV['BINANCE_SECRET_KEY']);
        unset($_ENV['DEBUG']);
    }

    /**
     * Create a mock request for testing
     */
    protected function createRequest(string $method, string $uri, array $headers = [], array $cookies = [], array $serverParams = []): \Psr\Http\Message\ServerRequestInterface
    {
        $request = $this->app->getContainer()->get(\Psr\Http\Message\ServerRequestInterface::class);
        return $request->withMethod($method)->withUri(new \Slim\Psr7\Uri($uri));
    }

    /**
     * Create a response for testing
     */
    protected function createResponse(): \Psr\Http\Message\ResponseInterface
    {
        return $this->app->getContainer()->get(\Psr\Http\Message\ResponseInterface::class);
    }
}