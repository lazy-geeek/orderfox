<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\Schemas;

class CandlesRequestSchema extends ValidationSchema
{
    private const VALID_TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'];

    public function validate(array $data): bool
    {
        $this->clearErrors();
        $isValid = true;

        // Validate symbol (required)
        if (!$this->validateRequired($data, 'symbol')) {
            $isValid = false;
        } elseif (!$this->validateString($data, 'symbol', 3, 20)) {
            $isValid = false;
        }

        // Validate timeframe (required)
        if (!$this->validateRequired($data, 'timeframe')) {
            $isValid = false;
        } elseif (!$this->validateInArray($data, 'timeframe', self::VALID_TIMEFRAMES)) {
            $isValid = false;
        }

        // Validate limit (optional)
        if (isset($data['limit'])) {
            if (!$this->validateInteger($data, 'limit', 1, 1000)) {
                $isValid = false;
            }
        }

        return $isValid;
    }

    public function getValidTimeframes(): array
    {
        return self::VALID_TIMEFRAMES;
    }
}