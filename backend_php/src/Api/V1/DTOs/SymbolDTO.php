<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\DTOs;

class SymbolDTO extends BaseDTO
{
    public string $symbol;
    public string $base;
    public string $quote;
    public bool $active;
    public bool $spot;
    public bool $margin;
    public bool $future;
    public bool $option;
    public bool $contract;
    public array $precision;
    public array $limits;

    public function __construct(
        string $symbol = '',
        string $base = '',
        string $quote = '',
        bool $active = true,
        bool $spot = true,
        bool $margin = false,
        bool $future = false,
        bool $option = false,
        bool $contract = false,
        array $precision = [],
        array $limits = []
    ) {
        $this->symbol = $symbol;
        $this->base = $base;
        $this->quote = $quote;
        $this->active = $active;
        $this->spot = $spot;
        $this->margin = $margin;
        $this->future = $future;
        $this->option = $option;
        $this->contract = $contract;
        $this->precision = $precision;
        $this->limits = $limits;
    }
}