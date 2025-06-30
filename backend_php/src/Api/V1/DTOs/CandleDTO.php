<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\DTOs;

class CandleDTO extends BaseDTO
{
    public int $timestamp;
    public string $datetime;
    public float $open;
    public float $high;
    public float $low;
    public float $close;
    public float $volume;

    public function __construct(
        int $timestamp = 0,
        string $datetime = '',
        float $open = 0.0,
        float $high = 0.0,
        float $low = 0.0,
        float $close = 0.0,
        float $volume = 0.0
    ) {
        $this->timestamp = $timestamp;
        $this->datetime = $datetime;
        $this->open = $open;
        $this->high = $high;
        $this->low = $low;
        $this->close = $close;
        $this->volume = $volume;
    }
}