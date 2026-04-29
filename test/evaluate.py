#!/usr/bin/env python3
"""
Test runner for EvalAI answer evaluation system.

This script runs comprehensive tests against the evaluation API and generates
detailed performance metrics and analysis reports.
"""

import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import numpy as np


class EvalAITester:
    """Test runner for EvalAI system."""
    
    def __init__(self, api_url: str = "http://localhost:8000", test_cases_file: str = "test_cases.json"):
        self.api_url = api_url.rstrip('/')
        self.test_cases_file = test_cases_file
        self.results = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "api_url": api_url,
                "total_cases": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0
            },
            "test_results": [],
            "performance_metrics": {},
            "analysis": {}
        }
    
    def load_test_cases(self) -> Dict[str, Any]:
        """Load test cases from JSON file."""
        try:
            with open(self.test_cases_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Test cases file '{self.test_cases_file}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in test cases file: {e}")
            sys.exit(1)
    
    def check_api_health(self) -> bool:
        """Check if the API is running and healthy."""
        try:
            response = requests.get(f"{self.api_url}/", timeout=400)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def evaluate_answer(self, question: str, answer: str) -> Optional[Dict[str, Any]]:
        """Send evaluation request to API."""
        try:
            payload = {
                "question": question,
                "answer": answer
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.api_url}/api/evaluate",
                json=payload,
                timeout=400,
                headers={"Content-Type": "application/json"}
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                result["response_time"] = end_time - start_time
                return result
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time": end_time - start_time
                }
                
        except requests.RequestException as e:
            return {
                "error": f"Request failed: {str(e)}",
                "response_time": 0
            }
    
    def evaluate_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single test case."""
        result = {
            "test_id": test_case["id"],
            "subject": test_case["subject"],
            "expected_rubric": test_case["expected_rubric"],
            "question": test_case["question"],
            "answer": test_case["answer"],
            "expected_marks_range": test_case["expected_marks_range"],
            "difficulty": test_case["difficulty"],
            "description": test_case["description"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Get evaluation from API
        api_result = self.evaluate_answer(test_case["question"], test_case["answer"])
        
        if "error" in api_result:
            result["status"] = "error"
            result["error"] = api_result["error"]
            result["response_time"] = api_result["response_time"]
            return result
        
        # Analyze results
        result["api_response"] = {
            "rubric_id": api_result.get("rubric_id"),
            "marks_awarded": api_result.get("marks_awarded"),
            "max_marks": api_result.get("max_marks"),
            "feedback": api_result.get("feedback"),
            "justification": api_result.get("justification"),
            "response_time": api_result["response_time"]
        }
        
        # Check if expected rubric matches
        rubric_match = api_result.get("rubric_id") == test_case["expected_rubric"]
        result["rubric_match"] = rubric_match
        
        # Check if marks are in expected range
        marks = api_result.get("marks_awarded", 0)
        min_expected, max_expected = test_case["expected_marks_range"]
        marks_in_range = min_expected <= marks <= max_expected
        result["marks_in_range"] = marks_in_range
        
        # Determine overall status
        if rubric_match and marks_in_range:
            result["status"] = "passed"
        elif rubric_match or marks_in_range:
            result["status"] = "partial"
        else:
            result["status"] = "failed"
        
        return result
    
    def calculate_performance_metrics(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics from test results."""
        metrics = {
            "response_time": {},
            "accuracy": {},
            "rubric_detection": {},
            "subject_performance": {},
            "difficulty_performance": {}
        }
        
        # Response time metrics
        response_times = [r["api_response"]["response_time"] for r in test_results 
                         if "api_response" in r and "response_time" in r["api_response"]]
        if response_times:
            metrics["response_time"] = {
                "mean": np.mean(response_times),
                "median": np.median(response_times),
                "min": np.min(response_times),
                "max": np.max(response_times),
                "std": np.std(response_times)
            }
        
        # Overall accuracy
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results if r["status"] == "passed"])
        partial_tests = len([r for r in test_results if r["status"] == "partial"])
        failed_tests = len([r for r in test_results if r["status"] == "failed"])
        error_tests = len([r for r in test_results if r["status"] == "error"])
        
        metrics["accuracy"] = {
            "pass_rate": passed_tests / total_tests * 100,
            "partial_rate": partial_tests / total_tests * 100,
            "fail_rate": failed_tests / total_tests * 100,
            "error_rate": error_tests / total_tests * 100,
            "total_tests": total_tests
        }
        
        # Rubric detection accuracy
        rubric_matches = [r for r in test_results if "rubric_match" in r]
        if rubric_matches:
            correct_rubrics = len([r for r in rubric_matches if r["rubric_match"]])
            metrics["rubric_detection"] = {
                "accuracy": correct_rubrics / len(rubric_matches) * 100,
                "total_evaluated": len(rubric_matches)
            }
        
        # Performance by subject
        subjects = {}
        for result in test_results:
            subject = result["subject"]
            if subject not in subjects:
                subjects[subject] = {"passed": 0, "total": 0}
            subjects[subject]["total"] += 1
            if result["status"] == "passed":
                subjects[subject]["passed"] += 1
        
        metrics["subject_performance"] = {
            subject: {
                "pass_rate": data["passed"] / data["total"] * 100,
                "total_tests": data["total"]
            }
            for subject, data in subjects.items()
        }
        
        # Performance by difficulty
        difficulties = {}
        for result in test_results:
            difficulty = result["difficulty"]
            if difficulty not in difficulties:
                difficulties[difficulty] = {"passed": 0, "total": 0}
            difficulties[difficulty]["total"] += 1
            if result["status"] == "passed":
                difficulties[difficulty]["passed"] += 1
        
        metrics["difficulty_performance"] = {
            difficulty: {
                "pass_rate": data["passed"] / data["total"] * 100,
                "total_tests": data["total"]
            }
            for difficulty, data in difficulties.items()
        }
        
        return metrics
    
    def run_tests(self) -> Dict[str, Any]:
        """Run all test cases and generate results."""
        print("Starting EvalAI test suite...")
        print(f"API URL: {self.api_url}")
        
        # Check API health
        if not self.check_api_health():
            print("Error: API is not responding. Please ensure the backend is running.")
            sys.exit(1)
        
        print("API health check passed.")
        
        # Load test cases
        test_data = self.load_test_cases()
        test_cases = test_data["test_cases"]
        
        print(f"Loaded {len(test_cases)} test cases.")
        
        # Update metadata
        self.results["test_run"]["total_cases"] = len(test_cases)
        
        # Run each test case
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nRunning test {i}/{len(test_cases)}: {test_case['id']}")
            print(f"  Description: {test_case['description']}")
            
            try:
                result = self.evaluate_test_case(test_case)
                self.results["test_results"].append(result)
                
                status_symbol = {
                    "passed": "✅",
                    "partial": "⚠️",
                    "failed": "❌",
                    "error": "💥"
                }.get(result["status"], "❓")
                
                print(f"  Status: {status_symbol} {result['status'].upper()}")
                
                if result["status"] == "error":
                    print(f"  Error: {result['error']}")
                else:
                    api_resp = result["api_response"]
                    print(f"  Rubric: {result['expected_rubric']} → {api_resp['rubric_id']}")
                    print(f"  Marks: {api_resp['marks_awarded']}/{api_resp['max_marks']}")
                    print(f"  Response time: {api_resp['response_time']:.2f}s")
                
                # Update counters
                if result["status"] == "passed":
                    self.results["test_run"]["passed"] += 1
                elif result["status"] == "failed":
                    self.results["test_run"]["failed"] += 1
                elif result["status"] == "error":
                    self.results["test_run"]["errors"] += 1
                    
            except Exception as e:
                print(f"  💥 UNEXPECTED ERROR: {str(e)}")
                error_result = {
                    "test_id": test_case["id"],
                    "status": "error",
                    "error": f"Test execution failed: {str(e)}",
                    "traceback": traceback.format_exc()
                }
                self.results["test_results"].append(error_result)
                self.results["test_run"]["errors"] += 1
        
        # Calculate performance metrics
        print("\nCalculating performance metrics...")
        self.results["performance_metrics"] = self.calculate_performance_metrics(
            self.results["test_results"]
        )
        
        # Add test metadata
        self.results["metadata"] = test_data.get("metadata", {})
        
        return self.results
    
    def save_results(self, output_file: str = "results.json"):
        """Save test results to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")
    
    def print_summary(self):
        """Print test summary to console."""
        run_data = self.results["test_run"]
        metrics = self.results["performance_metrics"]
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        print(f"Total Tests: {run_data['total_cases']}")
        print(f"Passed: {run_data['passed']} ({run_data['passed']/run_data['total_cases']*100:.1f}%)")
        print(f"Partial: {run_data['total_cases'] - run_data['passed'] - run_data['failed'] - run_data['errors']} ({(run_data['total_cases'] - run_data['passed'] - run_data['failed'] - run_data['errors'])/run_data['total_cases']*100:.1f}%)")
        print(f"Failed: {run_data['failed']} ({run_data['failed']/run_data['total_cases']*100:.1f}%)")
        print(f"Errors: {run_data['errors']} ({run_data['errors']/run_data['total_cases']*100:.1f}%)")
        
        if "response_time" in metrics and metrics["response_time"]:
            rt = metrics["response_time"]
            print(f"\nResponse Time Statistics:")
            print(f"  Mean: {rt['mean']:.2f}s")
            print(f"  Median: {rt['median']:.2f}s")
            print(f"  Min: {rt['min']:.2f}s")
            print(f"  Max: {rt['max']:.2f}s")
        
        if "rubric_detection" in metrics and metrics["rubric_detection"]:
            rd = metrics["rubric_detection"]
            print(f"\nRubric Detection Accuracy: {rd['accuracy']:.1f}%")
        
        if "subject_performance" in metrics:
            print(f"\nPerformance by Subject:")
            for subject, data in metrics["subject_performance"].items():
                print(f"  {subject}: {data['pass_rate']:.1f}% ({data['total_tests']} tests)")
        
        if "difficulty_performance" in metrics:
            print(f"\nPerformance by Difficulty:")
            for difficulty, data in metrics["difficulty_performance"].items():
                print(f"  {difficulty}: {data['pass_rate']:.1f}% ({data['total_tests']} tests)")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="EvalAI Test Runner")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--test-cases", default="test_cases.json",
                       help="Test cases JSON file (default: test_cases.json)")
    parser.add_argument("--output", default="results.json",
                       help="Results output file (default: results.json)")
    
    args = parser.parse_args()
    
    # Create and run tester
    tester = EvalAITester(args.api_url, args.test_cases)
    results = tester.run_tests()
    
    # Save and display results
    tester.save_results(args.output)
    tester.print_summary()


if __name__ == "__main__":
    main()
