<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\DTOs;

abstract class BaseDTO
{
    /**
     * Convert DTO to array
     */
    public function toArray(): array
    {
        return get_object_vars($this);
    }

    /**
     * Convert DTO to JSON string
     */
    public function toJson(): string
    {
        return json_encode($this->toArray(), JSON_PRETTY_PRINT);
    }

    /**
     * Create DTO from array
     */
    public static function fromArray(array $data): static
    {
        $instance = new static();
        
        foreach ($data as $key => $value) {
            if (property_exists($instance, $key)) {
                $instance->$key = $value;
            }
        }
        
        return $instance;
    }
}