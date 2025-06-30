<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\Schemas;

class OrderBookRequestSchema extends ValidationSchema
{
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

        // Validate limit (optional)
        if (isset($data['limit'])) {
            if (!$this->validateInteger($data, 'limit', 5, 5000)) {
                $isValid = false;
            }
        }

        return $isValid;
    }
}