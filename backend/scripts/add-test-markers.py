#!/usr/bin/env python3
"""
Script to add pytest chunk markers to all test files.
Automatically categorizes test files into logical chunks following dependency order.
"""

import os
import re
from pathlib import Path

# Define test file categorization by chunks
TEST_CHUNKS = {
    'chunk1': {
        'description': 'Foundation tests - Database, config, utilities',
        'files': [
            'test_database.py',
            'test_database_integration.py', 
            'core/test_config.py',
            'test_error_handling.py',
            'utils/test_decimal_utils.py'
        ]
    },
    'chunk2': {
        'description': 'Core services - Symbol, exchange, formatting, caching',
        'files': [
            'services/test_symbol_service.py',
            'services/test_exchange_service.py',
            'services/test_formatting_service.py',
            'services/test_formatting_service_rounding.py',
            'services/test_caching_mechanism.py'
        ]
    },
    'chunk3': {
        'description': 'Business services - Bot, orderbook, chart data',
        'files': [
            'services/test_bot_service.py',
            'services/test_chart_data_service.py',
            'services/test_orderbook_manager.py', 
            'services/test_orderbook_aggregation_service.py'
        ]
    },
    'chunk4': {
        'description': 'Advanced services - Liquidation, trade, trading engine',
        'files': [
            'services/test_liquidation_service.py',
            'services/test_trade_service.py',
            'services/test_trading_engine_service.py',
            'services/test_data_stream_manager.py',
            'services/test_liquidation_cache_management.py',
            'services/test_connection_parameter_tracking.py'
        ]
    },
    'chunk5': {
        'description': 'REST API endpoints - Schema, bot, market data APIs',
        'files': [
            'api/v1/test_schemas.py',
            'api/v1/test_bots.py',
            'api/v1/test_market_data_http.py',
            'api/v1/test_liquidation_volume.py',
            'api/v1/test_trading.py'
        ]
    },
    'chunk6': {
        'description': 'WebSocket API endpoints - Connection manager, market data, liquidations WS',
        'files': [
            'api/v1/test_connection_manager.py',
            'api/v1/test_market_data_ws.py',
            'api/v1/test_liquidations_ws.py'
        ]
    },
    'chunk7': {
        'description': 'Integration tests - Bot flows, orderbook flows, formatting',
        'files': [
            'integration/test_bot_paper_trading_flow.py',
            'integration/test_orderbook_full_flow.py',
            'integration/test_orderbook_websocket_real.py',
            'integration/test_orderbook_e2e_formatting.py',
            'integration/test_liquidation_volume_flow.py'
        ]
    },
    'chunk8a': {
        'description': 'Integration & E2E Tests - End-to-end data flow validation',
        'files': [
            'integration/test_liquidation_volume_e2e.py'
        ]
    },
    'chunk8b': {
        'description': 'Performance Tests - Response times, throughput, memory efficiency',
        'files': [
            'integration/test_liquidation_volume_performance.py'
        ]
    },
    'chunk8d': {
        'description': 'Basic Load Tests - Aggregation latency, throughput, cache performance',
        'files': [
            'load/test_orderbook_performance.py'
        ]
    },
    'chunk8e': {
        'description': 'Connection & Memory Tests - Connection performance, memory scaling',
        'files': [
            'load/test_orderbook_performance.py'
        ]
    },
    'chunk8f': {
        'description': 'Scalability & Concurrency Tests - System limits, sustained load',
        'files': [
            'load/test_orderbook_performance.py'
        ]
    },
    'chunk8g': {
        'description': 'Extended Load Tests - High-volume scenarios, extended runtime',
        'files': [
            'load/test_liquidation_volume_load.py'
        ]
    }
}

def add_marker_to_file(file_path: Path, chunk_name: str, description: str) -> bool:
    """Add pytest marker to a test file if it doesn't already have one."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if marker already exists
        if f'pytestmark = pytest.mark.{chunk_name}' in content:
            print(f"  ✓ {file_path.name} already has {chunk_name} marker")
            return True
        
        # Find import pytest line
        import_match = re.search(r'^(import pytest)$', content, re.MULTILINE)
        if not import_match:
            print(f"  ✗ {file_path.name} - No 'import pytest' found")
            return False
        
        # Insert marker after import pytest
        marker_text = f"\n# {description}\npytestmark = pytest.mark.{chunk_name}\n"
        
        # Split content and insert marker
        lines = content.split('\n')
        new_lines = []
        marker_added = False
        
        for line in lines:
            new_lines.append(line)
            if line.strip() == 'import pytest' and not marker_added:
                new_lines.append('')
                new_lines.append(f'# {description}')
                new_lines.append(f'pytestmark = pytest.mark.{chunk_name}')
                marker_added = True
        
        if marker_added:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            print(f"  ✓ Added {chunk_name} marker to {file_path.name}")
            return True
        else:
            print(f"  ✗ {file_path.name} - Could not add marker")
            return False
            
    except Exception as e:
        print(f"  ✗ Error processing {file_path.name}: {e}")
        return False

def main():
    """Main function to add markers to all test files."""
    test_dir = Path(__file__).parent.parent / 'tests'
    
    print("🚀 Adding pytest chunk markers to test files...\n")
    
    total_files = 0
    processed_files = 0
    
    for chunk_name, chunk_info in TEST_CHUNKS.items():
        print(f"📁 {chunk_name.upper()}: {chunk_info['description']}")
        
        for file_path in chunk_info['files']:
            full_path = test_dir / file_path
            total_files += 1
            
            if full_path.exists():
                if add_marker_to_file(full_path, chunk_name, f"Chunk {chunk_name[-1]}: {chunk_info['description']}"):
                    processed_files += 1
            else:
                print(f"  ✗ File not found: {file_path}")
        
        print()
    
    print(f"📊 Summary: {processed_files}/{total_files} files processed successfully")
    
    if processed_files == total_files:
        print("🎉 All test files have been marked with chunk markers!")
    else:
        print("⚠️  Some files could not be processed. Check the output above.")

if __name__ == '__main__':
    main()