#!/usr/bin/env python3
"""
Results Analysis and Visualization for EvalAI Test Suite

This script analyzes test results from the EvalAI evaluation system and generates
comprehensive reports with charts and visualizations.
"""

import json
import sys
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd

# Set up matplotlib for better plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class ResultsAnalyzer:
    """Analyzer for EvalAI test results."""
    
    def __init__(self, results_file: str = "results.json"):
        self.results_file = results_file
        self.results = None
        self.df = None
        self.load_results()
    
    def load_results(self):
        """Load results from JSON file."""
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                self.results = json.load(f)
            self.create_dataframe()
        except FileNotFoundError:
            print(f"Error: Results file '{self.results_file}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in results file: {e}")
            sys.exit(1)
    
    def create_dataframe(self):
        """Create pandas DataFrame from test results."""
        data = []
        for result in self.results["test_results"]:
            if "api_response" in result:
                row = {
                    "test_id": result["test_id"],
                    "subject": result["subject"],
                    "difficulty": result["difficulty"],
                    "description": result["description"],
                    "status": result["status"],
                    "rubric_match": result.get("rubric_match", False),
                    "marks_in_range": result.get("marks_in_range", False),
                    "expected_rubric": result["expected_rubric"],
                    "actual_rubric": result["api_response"].get("rubric_id"),
                    "marks_awarded": result["api_response"].get("marks_awarded", 0),
                    "max_marks": result["api_response"].get("max_marks", 0),
                    "response_time": result["api_response"].get("response_time", 0),
                    "expected_min": result["expected_marks_range"][0],
                    "expected_max": result["expected_marks_range"][1]
                }
            else:
                # Error case
                row = {
                    "test_id": result["test_id"],
                    "subject": result["subject"],
                    "difficulty": result["difficulty"],
                    "description": result["description"],
                    "status": result["status"],
                    "rubric_match": False,
                    "marks_in_range": False,
                    "expected_rubric": result["expected_rubric"],
                    "actual_rubric": None,
                    "marks_awarded": 0,
                    "max_marks": 0,
                    "response_time": 0,
                    "expected_min": result["expected_marks_range"][0],
                    "expected_max": result["expected_marks_range"][1]
                }
            data.append(row)
        
        self.df = pd.DataFrame(data)
    
    def generate_summary_report(self) -> str:
        """Generate text summary report."""
        report = []
        report.append("=" * 80)
        report.append("EVALAI TEST RESULTS ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Test Run: {self.results['test_run']['timestamp']}")
        report.append(f"API URL: {self.results['test_run']['api_url']}")
        report.append("")
        
        # Overall statistics
        run_data = self.results["test_run"]
        report.append("OVERALL STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Tests: {run_data['total_cases']}")
        report.append(f"Passed: {run_data['passed']} ({run_data['passed']/run_data['total_cases']*100:.1f}%)")
        partial = run_data['total_cases'] - run_data['passed'] - run_data['failed'] - run_data['errors']
        report.append(f"Partial: {partial} ({partial/run_data['total_cases']*100:.1f}%)")
        report.append(f"Failed: {run_data['failed']} ({run_data['failed']/run_data['total_cases']*100:.1f}%)")
        report.append(f"Errors: {run_data['errors']} ({run_data['errors']/run_data['total_cases']*100:.1f}%)")
        report.append("")
        
        # Performance metrics
        metrics = self.results["performance_metrics"]
        if "response_time" in metrics and metrics["response_time"]:
            rt = metrics["response_time"]
            report.append("RESPONSE TIME ANALYSIS")
            report.append("-" * 40)
            report.append(f"Mean: {rt['mean']:.2f}s")
            report.append(f"Median: {rt['median']:.2f}s")
            report.append(f"Min: {rt['min']:.2f}s")
            report.append(f"Max: {rt['max']:.2f}s")
            report.append(f"Std Dev: {rt['std']:.2f}s")
            report.append("")
        
        # Rubric detection
        if "rubric_detection" in metrics and metrics["rubric_detection"]:
            rd = metrics["rubric_detection"]
            report.append("RUBRIC DETECTION ACCURACY")
            report.append("-" * 40)
            report.append(f"Accuracy: {rd['accuracy']:.1f}%")
            report.append(f"Total Evaluated: {rd['total_evaluated']}")
            report.append("")
        
        # Subject performance
        if "subject_performance" in metrics:
            report.append("PERFORMANCE BY SUBJECT")
            report.append("-" * 40)
            for subject, data in sorted(metrics["subject_performance"].items()):
                report.append(f"{subject:12}: {data['pass_rate']:5.1f}% ({data['total_tests']:2d} tests)")
            report.append("")
        
        # Difficulty performance
        if "difficulty_performance" in metrics:
            report.append("PERFORMANCE BY DIFFICULTY")
            report.append("-" * 40)
            for difficulty, data in sorted(metrics["difficulty_performance"].items()):
                report.append(f"{difficulty:8}: {data['pass_rate']:5.1f}% ({data['total_tests']:2d} tests)")
            report.append("")
        
        # Failed tests analysis
        failed_tests = self.df[self.df["status"] == "failed"]
        if not failed_tests.empty:
            report.append("FAILED TESTS ANALYSIS")
            report.append("-" * 40)
            for _, test in failed_tests.iterrows():
                report.append(f"• {test['test_id']}: {test['description']}")
                report.append(f"  Expected: {test['expected_rubric']}, Got: {test['actual_rubric']}")
                report.append(f"  Marks: {test['marks_awarded']}/{test['max_marks']} (expected {test['expected_min']}-{test['expected_max']})")
            report.append("")
        
        # Error tests analysis
        error_tests = self.df[self.df["status"] == "error"]
        if not error_tests.empty:
            report.append("ERROR TESTS ANALYSIS")
            report.append("-" * 40)
            for _, test in error_tests.iterrows():
                result = next(r for r in self.results["test_results"] if r["test_id"] == test["test_id"])
                report.append(f"• {test['test_id']}: {test['description']}")
                report.append(f"  Error: {result.get('error', 'Unknown error')}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        
        if metrics.get("rubric_detection", {}).get("accuracy", 0) < 80:
            report.append("• Improve rubric detection algorithm - accuracy below 80%")
        
        if rt.get("mean", 0) > 15:
            report.append("• Optimize response time - average above 15 seconds")
        
        subject_perf = metrics.get("subject_performance", {})
        low_subjects = [s for s, d in subject_perf.items() if d["pass_rate"] < 50]
        if low_subjects:
            report.append(f"• Focus on improving performance for: {', '.join(low_subjects)}")
        
        diff_perf = metrics.get("difficulty_performance", {})
        if diff_perf.get("hard", {}).get("pass_rate", 0) < 50:
            report.append("• Improve handling of difficult test cases")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def create_visualizations(self, output_dir: str = "charts"):
        """Create visualization charts."""
        Path(output_dir).mkdir(exist_ok=True)
        
        # 1. Test Status Distribution
        plt.figure(figsize=(10, 6))
        status_counts = self.df["status"].value_counts()
        colors = {'passed': 'green', 'partial': 'orange', 'failed': 'red', 'error': 'darkred'}
        status_colors = [colors.get(status, 'gray') for status in status_counts.index]
        
        plt.pie(status_counts.values, labels=status_counts.index, colors=status_colors, autopct='%1.1f%%')
        plt.title("Test Status Distribution")
        plt.savefig(f"{output_dir}/test_status_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Response Time Distribution
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        plt.hist(self.df["response_time"], bins=15, alpha=0.7, color='skyblue', edgecolor='black')
        plt.xlabel("Response Time (seconds)")
        plt.ylabel("Frequency")
        plt.title("Response Time Distribution")
        
        plt.subplot(1, 2, 2)
        plt.boxplot(self.df["response_time"])
        plt.ylabel("Response Time (seconds)")
        plt.title("Response Time Box Plot")
        plt.tight_layout()
        plt.savefig(f"{output_dir}/response_time_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Performance by Subject
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 2, 1)
        subject_counts = self.df["subject"].value_counts()
        plt.bar(subject_counts.index, subject_counts.values, color='lightcoral')
        plt.title("Tests by Subject")
        plt.ylabel("Number of Tests")
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 2)
        subject_pass_rates = []
        subjects = []
        for subject in subject_counts.index:
            subject_data = self.df[self.df["subject"] == subject]
            pass_rate = (subject_data["status"] == "passed").sum() / len(subject_data) * 100
            subject_pass_rates.append(pass_rate)
            subjects.append(subject)
        
        colors = ['green' if rate >= 70 else 'orange' if rate >= 40 else 'red' for rate in subject_pass_rates]
        plt.bar(subjects, subject_pass_rates, color=colors)
        plt.title("Pass Rate by Subject")
        plt.ylabel("Pass Rate (%)")
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 3)
        rubric_accuracy = []
        for subject in subjects:
            subject_data = self.df[self.df["subject"] == subject]
            accuracy = subject_data["rubric_match"].sum() / len(subject_data) * 100
            rubric_accuracy.append(accuracy)
        
        plt.bar(subjects, rubric_accuracy, color='mediumpurple')
        plt.title("Rubric Detection Accuracy by Subject")
        plt.ylabel("Accuracy (%)")
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 4)
        avg_response_times = []
        for subject in subjects:
            subject_data = self.df[self.df["subject"] == subject]
            avg_time = subject_data["response_time"].mean()
            avg_response_times.append(avg_time)
        
        plt.bar(subjects, avg_response_times, color='gold')
        plt.title("Average Response Time by Subject")
        plt.ylabel("Response Time (seconds)")
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/subject_performance.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. Performance by Difficulty
        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 3, 1)
        difficulty_counts = self.df["difficulty"].value_counts()
        plt.bar(difficulty_counts.index, difficulty_counts.values, color='lightblue')
        plt.title("Tests by Difficulty")
        plt.ylabel("Number of Tests")
        
        plt.subplot(1, 3, 2)
        difficulty_pass_rates = []
        difficulties = []
        for difficulty in difficulty_counts.index:
            diff_data = self.df[self.df["difficulty"] == difficulty]
            pass_rate = (diff_data["status"] == "passed").sum() / len(diff_data) * 100
            difficulty_pass_rates.append(pass_rate)
            difficulties.append(difficulty)
        
        colors = ['green' if rate >= 70 else 'orange' if rate >= 40 else 'red' for rate in difficulty_pass_rates]
        plt.bar(difficulties, difficulty_pass_rates, color=colors)
        plt.title("Pass Rate by Difficulty")
        plt.ylabel("Pass Rate (%)")
        
        plt.subplot(1, 3, 3)
        avg_marks_by_difficulty = []
        for difficulty in difficulties:
            diff_data = self.df[self.df["difficulty"] == difficulty]
            avg_marks = diff_data["marks_awarded"].sum() / diff_data["max_marks"].sum() * 100
            avg_marks_by_difficulty.append(avg_marks)
        
        plt.bar(difficulties, avg_marks_by_difficulty, color='lightgreen')
        plt.title("Average Score % by Difficulty")
        plt.ylabel("Score %")
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/difficulty_performance.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 5. Marks Analysis
        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 2, 1)
        marks_comparison = self.df[["marks_awarded", "max_marks"]].dropna()
        x = range(len(marks_comparison))
        width = 0.35
        
        plt.bar([i - width/2 for i in x], marks_comparison["marks_awarded"], width, label="Awarded", color='orange', alpha=0.7)
        plt.bar([i + width/2 for i in x], marks_comparison["max_marks"], width, label="Maximum", color='blue', alpha=0.7)
        plt.xlabel("Test Case")
        plt.ylabel("Marks")
        plt.title("Awarded vs Maximum Marks")
        plt.legend()
        plt.xticks(x, marks_comparison.index, rotation=45)
        
        plt.subplot(1, 2, 2)
        score_percentages = (marks_comparison["marks_awarded"] / marks_comparison["max_marks"] * 100)
        plt.hist(score_percentages, bins=10, alpha=0.7, color='green', edgecolor='black')
        plt.xlabel("Score Percentage")
        plt.ylabel("Frequency")
        plt.title("Score Percentage Distribution")
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/marks_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 6. Rubric Matching Analysis
        plt.figure(figsize=(10, 6))
        
        rubric_data = self.df[self.df["actual_rubric"].notna()]
        if not rubric_data.empty:
            # Create confusion matrix data
            expected_rubrics = sorted(rubric_data["expected_rubric"].unique())
            actual_rubrics = sorted(rubric_data["actual_rubric"].unique())
            
            confusion_matrix = np.zeros((len(expected_rubrics), len(actual_rubrics)))
            
            for _, row in rubric_data.iterrows():
                exp_idx = expected_rubrics.index(row["expected_rubric"])
                act_idx = actual_rubrics.index(row["actual_rubric"])
                confusion_matrix[exp_idx, act_idx] += 1
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(confusion_matrix, annot=True, fmt='g', cmap='Blues',
                       xticklabels=actual_rubrics, yticklabels=expected_rubrics)
            plt.xlabel("Predicted Rubric")
            plt.ylabel("Expected Rubric")
            plt.title("Rubric Prediction Confusion Matrix")
            plt.savefig(f"{output_dir}/rubric_confusion_matrix.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        print(f"Charts saved to {output_dir}/ directory")
    
    def export_detailed_csv(self, output_file: str = "detailed_results.csv"):
        """Export detailed results to CSV."""
        # Add additional analysis columns
        df_export = self.df.copy()
        df_export["score_percentage"] = (df_export["marks_awarded"] / df_export["max_marks"] * 100).round(1)
        df_export["within_expected_range"] = df_export["marks_in_range"]
        df_export["rubric_correct"] = df_export["rubric_match"]
        
        # Add performance categories
        def categorize_performance(row):
            if row["status"] == "passed":
                return "Excellent"
            elif row["status"] == "partial":
                if row["rubric_match"] and row["marks_in_range"]:
                    return "Good"
                elif row["rubric_match"] or row["marks_in_range"]:
                    return "Fair"
                else:
                    return "Poor"
            else:
                return "Failed"
        
        df_export["performance_category"] = df_export.apply(categorize_performance, axis=1)
        
        df_export.to_csv(output_file, index=False)
        print(f"Detailed results exported to {output_file}")
    
    def generate_html_report(self, output_file: str = "test_report.html"):
        """Generate HTML report with embedded charts."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>EvalAI Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background-color: #e8f4f8; border-radius: 5px; }}
        .chart {{ text-align: center; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .passed {{ color: green; }}
        .partial {{ color: orange; }}
        .failed {{ color: red; }}
        .error {{ color: darkred; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>EvalAI Test Results Analysis Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Test Run: {self.results['test_run']['timestamp']}</p>
        <p>API URL: {self.results['test_run']['api_url']}</p>
    </div>
    
    <div class="section">
        <h2>Overall Statistics</h2>
        <div class="metric">
            <h3>{self.results['test_run']['total_cases']}</h3>
            <p>Total Tests</p>
        </div>
        <div class="metric">
            <h3 class="passed">{self.results['test_run']['passed']}</h3>
            <p>Passed ({self.results['test_run']['passed']/self.results['test_run']['total_cases']*100:.1f}%)</p>
        </div>
        <div class="metric">
            <h3 class="partial">{self.results['test_run']['total_cases'] - self.results['test_run']['passed'] - self.results['test_run']['failed'] - self.results['test_run']['errors']}</h3>
            <p>Partial</p>
        </div>
        <div class="metric">
            <h3 class="failed">{self.results['test_run']['failed']}</h3>
            <p>Failed</p>
        </div>
        <div class="metric">
            <h3 class="error">{self.results['test_run']['errors']}</h3>
            <p>Errors</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Performance Metrics</h2>
"""
        
        metrics = self.results["performance_metrics"]
        if "response_time" in metrics and metrics["response_time"]:
            rt = metrics["response_time"]
            html += f"""
        <div class="metric">
            <h3>{rt['mean']:.2f}s</h3>
            <p>Avg Response Time</p>
        </div>
        <div class="metric">
            <h3>{rt['median']:.2f}s</h3>
            <p>Median Response Time</p>
        </div>
"""
        
        if "rubric_detection" in metrics and metrics["rubric_detection"]:
            rd = metrics["rubric_detection"]
            html += f"""
        <div class="metric">
            <h3>{rd['accuracy']:.1f}%</h3>
            <p>Rubric Detection Accuracy</p>
        </div>
"""
        
        html += """
    </div>
    
    <div class="section">
        <h2>Detailed Test Results</h2>
        <table>
            <tr>
                <th>Test ID</th>
                <th>Subject</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Expected Rubric</th>
                <th>Actual Rubric</th>
                <th>Marks</th>
                <th>Response Time</th>
                <th>Description</th>
            </tr>
"""
        
        for _, row in self.df.iterrows():
            status_class = row["status"]
            html += f"""
            <tr>
                <td>{row['test_id']}</td>
                <td>{row['subject']}</td>
                <td>{row['difficulty']}</td>
                <td class="{status_class}">{row['status'].upper()}</td>
                <td>{row['expected_rubric']}</td>
                <td>{row['actual_rubric'] or 'N/A'}</td>
                <td>{row['marks_awarded']}/{row['max_marks']}</td>
                <td>{row['response_time']:.2f}s</td>
                <td>{row['description']}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>Charts</h2>
        <div class="chart">
            <h3>Test Status Distribution</h3>
            <img src="charts/test_status_distribution.png" alt="Test Status Distribution">
        </div>
        <div class="chart">
            <h3>Response Time Analysis</h3>
            <img src="charts/response_time_analysis.png" alt="Response Time Analysis">
        </div>
        <div class="chart">
            <h3>Subject Performance</h3>
            <img src="charts/subject_performance.png" alt="Subject Performance">
        </div>
        <div class="chart">
            <h3>Difficulty Performance</h3>
            <img src="charts/difficulty_performance.png" alt="Difficulty Performance">
        </div>
        <div class="chart">
            <h3>Marks Analysis</h3>
            <img src="charts/marks_analysis.png" alt="Marks Analysis">
        </div>
"""
        
        if Path("charts/rubric_confusion_matrix.png").exists():
            html += """
        <div class="chart">
            <h3>Rubric Confusion Matrix</h3>
            <img src="charts/rubric_confusion_matrix.png" alt="Rubric Confusion Matrix">
        </div>
"""
        
        html += """
    </div>
    
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML report generated: {output_file}")
    
    def run_full_analysis(self, output_dir: str = "analysis"):
        """Run complete analysis and generate all reports."""
        Path(output_dir).mkdir(exist_ok=True)
        
        print("Generating comprehensive analysis...")
        
        # Text report
        report = self.generate_summary_report()
        report_file = f"{output_dir}/analysis_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Text report: {report_file}")
        
        # Visualizations
        self.create_visualizations(f"{output_dir}/charts")
        
        # CSV export
        self.export_detailed_csv(f"{output_dir}/detailed_results.csv")
        
        # HTML report
        self.generate_html_report(f"{output_dir}/test_report.html")
        
        print(f"\nAnalysis complete! All files saved to {output_dir}/ directory")
        return report


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="EvalAI Results Analyzer")
    parser.add_argument("--results", default="results.json",
                       help="Results JSON file (default: results.json)")
    parser.add_argument("--output", default="analysis",
                       help="Output directory (default: analysis)")
    
    args = parser.parse_args()
    
    # Create analyzer and run analysis
    analyzer = ResultsAnalyzer(args.results)
    report = analyzer.run_full_analysis(args.output)
    
    # Print summary to console
    print("\n" + "="*80)
    print(report)
    print("="*80)


if __name__ == "__main__":
    main()
