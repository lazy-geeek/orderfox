<?php

declare(strict_types=1);

namespace OrderFox\Api\V1\DTOs;

class OrderBookDTO extends BaseDTO
{
    public string $symbol;
    public ?int $timestamp;
    public ?string $datetime;
    public ?int $nonce;
    public array $bids;
    public array $asks;
    public ?array $info;

    public function __construct(
        string $symbol = '',
        ?int $timestamp = null,
        ?string $datetime = null,
        ?int $nonce = null,
        array $bids = [],
        array $asks = [],
        ?array $info = null
    ) {
        $this->symbol = $symbol;
        $this->timestamp = $timestamp;
        $this->datetime = $datetime;
        $this->nonce = $nonce;
        $this->bids = $bids;
        $this->asks = $asks;
        $this->info = $info;
    }
}