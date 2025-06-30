<?php

declare(strict_types=1);

namespace OrderFox\Services;

use OrderFox\Core\Logger;

class SymbolService
{
    private \Monolog\Logger $logger;
    private ExchangeService $exchangeService;
    private array $symbolCache = [];
    private int $cacheExpiry = 3600; // 1 hour
    private int $cacheTimestamp = 0;

    public function __construct(?ExchangeService $exchangeService = null)
    {
        $this->logger = Logger::getLogger('symbol');
        $this->exchangeService = $exchangeService ?? new ExchangeService();
    }

    /**
     * Resolve and validate a symbol input
     * Supports various formats: BTC/USDT, BTCUSDT, btc/usdt, etc.
     */
    public function resolveSymbol(string $input): string
    {
        $this->logger->debug('Resolving symbol', ['input' => $input]);

        // Normalize input
        $normalized = strtoupper(trim($input));
        
        // Get available symbols
        $availableSymbols = $this->getAvailableSymbols();
        
        // Direct match
        if (isset($availableSymbols[$normalized])) {
            $this->logger->debug('Direct symbol match found', [
                'input' => $input,
                'resolved' => $normalized
            ]);
            return $normalized;
        }

        // Try adding slash if not present
        if (!str_contains($normalized, '/')) {
            $withSlash = $this->addSlashToSymbol($normalized);
            if ($withSlash && isset($availableSymbols[$withSlash])) {
                $this->logger->debug('Symbol match found with slash', [
                    'input' => $input,
                    'resolved' => $withSlash
                ]);
                return $withSlash;
            }
        }

        // Try removing slash if present
        if (str_contains($normalized, '/')) {
            $withoutSlash = str_replace('/', '', $normalized);
            $withSlash = $this->addSlashToSymbol($withoutSlash);
            if ($withSlash && isset($availableSymbols[$withSlash])) {
                $this->logger->debug('Symbol match found after slash processing', [
                    'input' => $input,
                    'resolved' => $withSlash
                ]);
                return $withSlash;
            }
        }

        // Fuzzy matching
        $suggestions = $this->findSimilarSymbols($normalized, $availableSymbols);
        
        if (!empty($suggestions)) {
            $bestMatch = $suggestions[0];
            $this->logger->info('Using fuzzy match for symbol', [
                'input' => $input,
                'resolved' => $bestMatch,
                'suggestions' => array_slice($suggestions, 0, 3)
            ]);
            return $bestMatch;
        }

        $this->logger->error('Symbol not found', [
            'input' => $input,
            'normalized' => $normalized
        ]);

        throw new \InvalidArgumentException("Symbol '{$input}' not found or not supported");
    }

    /**
     * Get list of available symbols with caching
     */
    private function getAvailableSymbols(): array
    {
        $now = time();
        
        // Check if cache is valid
        if (!empty($this->symbolCache) && ($now - $this->cacheTimestamp) < $this->cacheExpiry) {
            return $this->symbolCache;
        }

        try {
            $this->logger->debug('Refreshing symbol cache');
            
            $symbols = $this->exchangeService->fetchSymbols();
            
            // Create lookup array
            $lookup = [];
            foreach ($symbols as $symbol) {
                $lookup[$symbol['symbol']] = $symbol;
            }

            $this->symbolCache = $lookup;
            $this->cacheTimestamp = $now;

            $this->logger->info('Symbol cache refreshed', [
                'count' => count($lookup),
                'cache_expiry' => $this->cacheExpiry
            ]);

            return $this->symbolCache;

        } catch (\Exception $e) {
            $this->logger->error('Failed to refresh symbol cache', [
                'error' => $e->getMessage()
            ]);
            
            // Return existing cache if available, otherwise throw
            if (!empty($this->symbolCache)) {
                $this->logger->warning('Using stale symbol cache due to refresh failure');
                return $this->symbolCache;
            }
            
            throw $e;
        }
    }

    /**
     * Add slash to symbol in the most likely position
     * Tries common patterns like BTCUSDT -> BTC/USDT
     */
    private function addSlashToSymbol(string $symbol): ?string
    {
        // Common quote currencies in order of popularity
        $quoteCurrencies = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'BUSD', 'DAI', 'USD', 'EUR', 'GBP'];
        
        foreach ($quoteCurrencies as $quote) {
            if (str_ends_with($symbol, $quote)) {
                $base = substr($symbol, 0, -strlen($quote));
                if (strlen($base) >= 2) { // Ensure base currency is at least 2 characters
                    return $base . '/' . $quote;
                }
            }
        }

        // If no common quote currency found, try 3-4 character splits
        $len = strlen($symbol);
        if ($len >= 6) {
            // Try splitting at 3/4 character boundaries
            for ($split = 3; $split <= 4 && $split < $len - 2; $split++) {
                $base = substr($symbol, 0, $split);
                $quote = substr($symbol, $split);
                $candidate = $base . '/' . $quote;
                
                // Check if this looks reasonable (both parts 2+ chars)
                if (strlen($base) >= 2 && strlen($quote) >= 2) {
                    return $candidate;
                }
            }
        }

        return null;
    }

    /**
     * Find similar symbols using fuzzy matching
     */
    private function findSimilarSymbols(string $input, array $availableSymbols): array
    {
        $suggestions = [];
        $inputLen = strlen($input);

        foreach (array_keys($availableSymbols) as $symbol) {
            $similarity = 0;
            
            // Calculate Levenshtein distance
            $distance = levenshtein($input, $symbol);
            $maxLen = max($inputLen, strlen($symbol));
            
            if ($maxLen > 0) {
                $similarity = 1 - ($distance / $maxLen);
            }

            // Add bonus for partial matches
            if (str_contains($symbol, $input) || str_contains($input, $symbol)) {
                $similarity += 0.2;
            }

            // Add bonus for same starting characters
            $commonPrefix = 0;
            $minLen = min($inputLen, strlen($symbol));
            for ($i = 0; $i < $minLen; $i++) {
                if ($input[$i] === $symbol[$i]) {
                    $commonPrefix++;
                } else {
                    break;
                }
            }
            if ($commonPrefix > 0) {
                $similarity += ($commonPrefix / $minLen) * 0.1;
            }

            // Only consider symbols with reasonable similarity
            if ($similarity > 0.6) {
                $suggestions[] = [
                    'symbol' => $symbol,
                    'similarity' => $similarity
                ];
            }
        }

        // Sort by similarity (descending)
        usort($suggestions, function ($a, $b) {
            return $b['similarity'] <=> $a['similarity'];
        });

        // Return just the symbols
        return array_map(function ($item) {
            return $item['symbol'];
        }, array_slice($suggestions, 0, 5));
    }

    /**
     * Validate symbol format
     */
    public function isValidSymbolFormat(string $symbol): bool
    {
        // Must contain a slash and have valid base/quote parts
        if (!str_contains($symbol, '/')) {
            return false;
        }

        $parts = explode('/', $symbol);
        if (count($parts) !== 2) {
            return false;
        }

        [$base, $quote] = $parts;

        // Both parts must be at least 2 characters and contain only letters/numbers
        return strlen($base) >= 2 
            && strlen($quote) >= 2 
            && ctype_alnum($base) 
            && ctype_alnum($quote);
    }

    /**
     * Get symbol suggestions for autocomplete
     */
    public function getSymbolSuggestions(string $query, int $limit = 10): array
    {
        if (strlen($query) < 2) {
            return [];
        }

        $availableSymbols = $this->getAvailableSymbols();
        $suggestions = $this->findSimilarSymbols(strtoupper($query), $availableSymbols);

        return array_slice($suggestions, 0, $limit);
    }

    /**
     * Clear symbol cache (useful for testing)
     */
    public function clearCache(): void
    {
        $this->symbolCache = [];
        $this->cacheTimestamp = 0;
        $this->logger->debug('Symbol cache cleared');
    }

    /**
     * Get cache statistics
     */
    public function getCacheStats(): array
    {
        return [
            'cached_symbols' => count($this->symbolCache),
            'cache_age_seconds' => time() - $this->cacheTimestamp,
            'cache_expiry_seconds' => $this->cacheExpiry,
            'is_cache_valid' => (time() - $this->cacheTimestamp) < $this->cacheExpiry
        ];
    }
}