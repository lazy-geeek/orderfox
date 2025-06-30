<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\Formatters;

use Psr\Http\Message\ResponseInterface as Response;

class ResponseFormatter
{
    /**
     * Format successful response
     */
    public static function success(Response $response, $data, int $statusCode = 200): Response
    {
        $responseData = [
            'success' => true,
            'data' => $data,
            'timestamp' => date('c')
        ];

        $response->getBody()->write(json_encode($responseData, JSON_PRETTY_PRINT));
        return $response
            ->withHeader('Content-Type', 'application/json')
            ->withStatus($statusCode);
    }

    /**
     * Format error response
     */
    public static function error(Response $response, string $type, string $message, int $statusCode = 500, ?array $details = null): Response
    {
        $errorData = [
            'success' => false,
            'error' => [
                'type' => $type,
                'message' => $message,
                'timestamp' => date('c')
            ]
        ];

        if ($details !== null) {
            $errorData['error']['details'] = $details;
        }

        $response->getBody()->write(json_encode($errorData, JSON_PRETTY_PRINT));
        return $response
            ->withHeader('Content-Type', 'application/json')
            ->withStatus($statusCode);
    }

    /**
     * Format validation error response
     */
    public static function validationError(Response $response, array $errors): Response
    {
        return self::error(
            $response,
            'validation_error',
            'Request validation failed',
            400,
            ['validation_errors' => $errors]
        );
    }

    /**
     * Format exchange error response
     */
    public static function exchangeError(Response $response, string $message, ?\Exception $exception = null): Response
    {
        $details = null;
        
        if ($exception !== null) {
            $details = [
                'exception_class' => get_class($exception),
                'exception_message' => $exception->getMessage()
            ];
        }

        return self::error(
            $response,
            'exchange_error',
            $message,
            500,
            $details
        );
    }

    /**
     * Format not found error response
     */
    public static function notFound(Response $response, string $resource): Response
    {
        return self::error(
            $response,
            'not_found',
            "Resource '{$resource}' not found",
            404
        );
    }

    /**
     * Format rate limit error response
     */
    public static function rateLimitError(Response $response): Response
    {
        return self::error(
            $response,
            'rate_limit_exceeded',
            'Too many requests. Please try again later.',
            429
        );
    }

    /**
     * Format symbols list response
     */
    public static function symbolsList(Response $response, array $symbols): Response
    {
        $data = [
            'symbols' => $symbols,
            'count' => count($symbols),
            'timestamp' => date('c')
        ];

        return self::success($response, $data);
    }

    /**
     * Format ticker response
     */
    public static function ticker(Response $response, array $ticker): Response
    {
        return self::success($response, $ticker);
    }

    /**
     * Format order book response
     */
    public static function orderBook(Response $response, array $orderBook): Response
    {
        return self::success($response, $orderBook);
    }

    /**
     * Format candles response
     */
    public static function candles(Response $response, array $candles): Response
    {
        $data = [
            'candles' => $candles,
            'count' => count($candles),
            'timestamp' => date('c')
        ];

        return self::success($response, $data);
    }
}