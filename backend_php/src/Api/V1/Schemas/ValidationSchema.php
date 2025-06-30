<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\Schemas;

abstract class ValidationSchema
{
    protected array $errors = [];

    /**
     * Validate the given data against the schema
     */
    abstract public function validate(array $data): bool;

    /**
     * Get validation errors
     */
    public function getErrors(): array
    {
        return $this->errors;
    }

    /**
     * Clear validation errors
     */
    public function clearErrors(): void
    {
        $this->errors = [];
    }

    /**
     * Add a validation error
     */
    protected function addError(string $field, string $message): void
    {
        if (!isset($this->errors[$field])) {
            $this->errors[$field] = [];
        }
        $this->errors[$field][] = $message;
    }

    /**
     * Validate required field
     */
    protected function validateRequired(array $data, string $field): bool
    {
        if (!isset($data[$field]) || $data[$field] === null || $data[$field] === '') {
            $this->addError($field, "Field '{$field}' is required");
            return false;
        }
        return true;
    }

    /**
     * Validate string field
     */
    protected function validateString(array $data, string $field, ?int $minLength = null, ?int $maxLength = null): bool
    {
        if (!isset($data[$field])) {
            return true; // Skip validation if field is not present
        }

        if (!is_string($data[$field])) {
            $this->addError($field, "Field '{$field}' must be a string");
            return false;
        }

        $length = strlen($data[$field]);

        if ($minLength !== null && $length < $minLength) {
            $this->addError($field, "Field '{$field}' must be at least {$minLength} characters long");
            return false;
        }

        if ($maxLength !== null && $length > $maxLength) {
            $this->addError($field, "Field '{$field}' must be no more than {$maxLength} characters long");
            return false;
        }

        return true;
    }

    /**
     * Validate integer field
     */
    protected function validateInteger(array $data, string $field, ?int $min = null, ?int $max = null): bool
    {
        if (!isset($data[$field])) {
            return true; // Skip validation if field is not present
        }

        if (!is_int($data[$field]) && !is_numeric($data[$field])) {
            $this->addError($field, "Field '{$field}' must be an integer");
            return false;
        }

        $value = (int) $data[$field];

        if ($min !== null && $value < $min) {
            $this->addError($field, "Field '{$field}' must be at least {$min}");
            return false;
        }

        if ($max !== null && $value > $max) {
            $this->addError($field, "Field '{$field}' must be no more than {$max}");
            return false;
        }

        return true;
    }

    /**
     * Validate field is in allowed values
     */
    protected function validateInArray(array $data, string $field, array $allowedValues): bool
    {
        if (!isset($data[$field])) {
            return true; // Skip validation if field is not present
        }

        if (!in_array($data[$field], $allowedValues, true)) {
            $this->addError($field, "Field '{$field}' must be one of: " . implode(', ', $allowedValues));
            return false;
        }

        return true;
    }

    /**
     * Validate symbol format (BASE/QUOTE)
     */
    protected function validateSymbolFormat(array $data, string $field): bool
    {
        if (!isset($data[$field])) {
            return true; // Skip validation if field is not present
        }

        $symbol = $data[$field];

        if (!is_string($symbol)) {
            $this->addError($field, "Field '{$field}' must be a string");
            return false;
        }

        if (!preg_match('/^[A-Z0-9]+\/[A-Z0-9]+$/', $symbol)) {
            $this->addError($field, "Field '{$field}' must be in format BASE/QUOTE (e.g., BTC/USDT)");
            return false;
        }

        $parts = explode('/', $symbol);
        if (count($parts) !== 2) {
            $this->addError($field, "Field '{$field}' must contain exactly one slash");
            return false;
        }

        [$base, $quote] = $parts;

        if (strlen($base) < 2 || strlen($quote) < 2) {
            $this->addError($field, "Both base and quote currencies must be at least 2 characters long");
            return false;
        }

        return true;
    }
}