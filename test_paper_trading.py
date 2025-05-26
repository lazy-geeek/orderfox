#!/usr/bin/env python3
"""
Paper Trading API Test Script

This script tests the paper trading functionality of the backend API
by executing various trading scenarios and documenting the results.
"""

import requests
import json
import time
from typing import Dict, Any, List

# API Configuration
BASE_URL = "http://localhost:8000/api/v1/trading"
HEADERS = {"Content-Type": "application/json"}


class PaperTradingTester:
    def __init__(self):
        self.test_results = []
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def log_test(
        self, scenario: str, request_data: Dict[str, Any], response: requests.Response
    ):
        """Log test results for documentation"""
        result = {
            "scenario": scenario,
            "request": {
                "method": request_data.get("method", "GET"),
                "url": request_data.get("url", ""),
                "body": request_data.get("body", {}),
            },
            "response": {
                "status_code": response.status_code,
                "body": (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else response.text
                ),
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.test_results.append(result)

        # Print immediate feedback
        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario}")
        print(f"{'='*60}")
        print(f"Request: {request_data['method']} {request_data['url']}")
        if request_data.get("body"):
            print(f"Body: {json.dumps(request_data['body'], indent=2)}")
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(result['response']['body'], indent=2)}")

        return result

    def test_set_trading_mode_paper(self):
        """Scenario 1: Set Trading Mode to Paper"""
        url = f"{BASE_URL}/set_trading_mode"
        body = {"mode": "paper"}

        response = self.session.post(url, json=body)
        return self.log_test(
            "Set Trading Mode to Paper",
            {"method": "POST", "url": url, "body": body},
            response,
        )

    def test_open_long_position(self):
        """Scenario 2: Open a Long Paper Position"""
        url = f"{BASE_URL}/trade"
        body = {
            "symbol": "BTC/USDT:USDT",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }

        response = self.session.post(url, json=body)
        return self.log_test(
            "Open Long BTC Position",
            {"method": "POST", "url": url, "body": body},
            response,
        )

    def test_get_positions_after_long(self):
        """Check positions after opening long position"""
        url = f"{BASE_URL}/positions"

        response = self.session.get(url)
        return self.log_test(
            "Get Positions After Long BTC", {"method": "GET", "url": url}, response
        )

    def test_open_short_position(self):
        """Scenario 3: Open a Short Paper Position"""
        url = f"{BASE_URL}/trade"
        body = {
            "symbol": "ETH/USDT:USDT",
            "side": "short",
            "amount": 1.0,
            "type": "market",
        }

        response = self.session.post(url, json=body)
        return self.log_test(
            "Open Short ETH Position",
            {"method": "POST", "url": url, "body": body},
            response,
        )

    def test_get_positions_after_short(self):
        """Check positions after opening short position"""
        url = f"{BASE_URL}/positions"

        response = self.session.get(url)
        return self.log_test(
            "Get Positions After Short ETH", {"method": "GET", "url": url}, response
        )

    def test_partial_close_long(self):
        """Scenario 4: Close Part of a Long Paper Position"""
        url = f"{BASE_URL}/trade"
        body = {
            "symbol": "BTC/USDT:USDT",
            "side": "short",  # Short to close long position
            "amount": 0.05,
            "type": "market",
        }

        response = self.session.post(url, json=body)
        return self.log_test(
            "Partial Close Long BTC Position",
            {"method": "POST", "url": url, "body": body},
            response,
        )

    def test_get_positions_after_partial_close(self):
        """Check positions after partial close"""
        url = f"{BASE_URL}/positions"

        response = self.session.get(url)
        return self.log_test(
            "Get Positions After Partial Close", {"method": "GET", "url": url}, response
        )

    def test_close_entire_short(self):
        """Scenario 5: Close an Entire Short Paper Position"""
        url = f"{BASE_URL}/trade"
        body = {
            "symbol": "ETH/USDT:USDT",
            "side": "long",  # Long to close short position
            "amount": 1.0,
            "type": "market",
        }

        response = self.session.post(url, json=body)
        return self.log_test(
            "Close Entire Short ETH Position",
            {"method": "POST", "url": url, "body": body},
            response,
        )

    def test_get_positions_after_close(self):
        """Check positions after closing short position"""
        url = f"{BASE_URL}/positions"

        response = self.session.get(url)
        return self.log_test(
            "Get Positions After Close ETH", {"method": "GET", "url": url}, response
        )

    def test_invalid_trade(self):
        """Scenario 6: Attempt Invalid Paper Trade"""
        url = f"{BASE_URL}/trade"
        body = {
            "symbol": "INVALID/SYMBOL",
            "side": "long",
            "amount": 0.1,
            "type": "market",
        }

        response = self.session.post(url, json=body)
        return self.log_test(
            "Invalid Trade Test", {"method": "POST", "url": url, "body": body}, response
        )

    def test_limit_order(self):
        """Test limit order functionality"""
        url = f"{BASE_URL}/trade"
        body = {
            "symbol": "BTC/USDT:USDT",
            "side": "long",
            "amount": 0.05,
            "type": "limit",
            "price": 45000.0,
        }

        response = self.session.post(url, json=body)
        return self.log_test(
            "Limit Order Test", {"method": "POST", "url": url, "body": body}, response
        )

    def run_all_tests(self):
        """Execute all test scenarios"""
        print("Starting Paper Trading API Tests...")
        print(f"Testing against: {BASE_URL}")

        # Test scenarios in order
        test_methods = [
            self.test_set_trading_mode_paper,
            self.test_open_long_position,
            self.test_get_positions_after_long,
            self.test_open_short_position,
            self.test_get_positions_after_short,
            self.test_partial_close_long,
            self.test_get_positions_after_partial_close,
            self.test_close_entire_short,
            self.test_get_positions_after_close,
            self.test_invalid_trade,
            self.test_limit_order,
        ]

        for test_method in test_methods:
            try:
                test_method()
                time.sleep(0.5)  # Small delay between tests
            except Exception as e:
                print(f"Error in {test_method.__name__}: {e}")
                self.test_results.append(
                    {
                        "scenario": test_method.__name__,
                        "error": str(e),
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

        self.generate_report()

    def generate_report(self):
        """Generate a comprehensive test report"""
        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len(
                    [
                        r
                        for r in self.test_results
                        if r.get("response", {}).get("status_code") in [200, 201]
                    ]
                ),
                "failed_tests": len(
                    [
                        r
                        for r in self.test_results
                        if r.get("response", {}).get("status_code")
                        not in [200, 201, None]
                    ]
                ),
                "errors": len([r for r in self.test_results if "error" in r]),
            },
            "test_results": self.test_results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Save to file
        with open("paper_trading_test_report.json", "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {report['test_summary']['total_tests']}")
        print(f"Successful: {report['test_summary']['successful_tests']}")
        print(f"Failed: {report['test_summary']['failed_tests']}")
        print(f"Errors: {report['test_summary']['errors']}")
        print(f"\nDetailed report saved to: paper_trading_test_report.json")


if __name__ == "__main__":
    tester = PaperTradingTester()
    tester.run_all_tests()
