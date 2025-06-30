<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\DTOs;

class TickerDTO extends BaseDTO
{
    public string $symbol;
    public ?int $timestamp;
    public ?string $datetime;
    public ?float $high;
    public ?float $low;
    public ?float $bid;
    public ?float $bidVolume;
    public ?float $ask;
    public ?float $askVolume;
    public ?float $vwap;
    public ?float $open;
    public ?float $close;
    public ?float $last;
    public ?float $previousClose;
    public ?float $change;
    public ?float $percentage;
    public ?float $average;
    public ?float $baseVolume;
    public ?float $quoteVolume;
    public ?array $info;

    public function __construct(
        string $symbol = '',
        ?int $timestamp = null,
        ?string $datetime = null,
        ?float $high = null,
        ?float $low = null,
        ?float $bid = null,
        ?float $bidVolume = null,
        ?float $ask = null,
        ?float $askVolume = null,
        ?float $vwap = null,
        ?float $open = null,
        ?float $close = null,
        ?float $last = null,
        ?float $previousClose = null,
        ?float $change = null,
        ?float $percentage = null,
        ?float $average = null,
        ?float $baseVolume = null,
        ?float $quoteVolume = null,
        ?array $info = null
    ) {
        $this->symbol = $symbol;
        $this->timestamp = $timestamp;
        $this->datetime = $datetime;
        $this->high = $high;
        $this->low = $low;
        $this->bid = $bid;
        $this->bidVolume = $bidVolume;
        $this->ask = $ask;
        $this->askVolume = $askVolume;
        $this->vwap = $vwap;
        $this->open = $open;
        $this->close = $close;
        $this->last = $last;
        $this->previousClose = $previousClose;
        $this->change = $change;
        $this->percentage = $percentage;
        $this->average = $average;
        $this->baseVolume = $baseVolume;
        $this->quoteVolume = $quoteVolume;
        $this->info = $info;
    }
}