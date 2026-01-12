from datetime import datetime
from typing import Any, Dict, List, Optional


class TerminalFormatter:
    class Colors:
        HEADER = "\033[95m"
        OKBLUE = "\033[94m"
        OKCYAN = "\033[96m"
        OKGREEN = "\033[92m"
        WARNING = "\033[93m"
        FAIL = "\033[91m"
        ENDC = "\033[0m"
        BOLD = "\033[1m"
        UNDERLINE = "\033[4m"

        GRAY = "\033[90m"
        LIGHT_BLUE = "\033[94m"
        LIGHT_GREEN = "\033[92m"
        LIGHT_YELLOW = "\033[93m"
        LIGHT_RED = "\033[91m"
        PURPLE = "\033[95m"
        WHITE = "\033[97m"

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        if not use_colors:
            for attr in dir(self.Colors):
                if not attr.startswith("_"):
                    setattr(self.Colors, attr, "")

    def print_header(self, text: str, char: str = "=", color: Optional[str] = None) -> None:
        header_color = color if color is not None else self.Colors.HEADER
        line = char * len(text)
        print(f"\n{header_color}{self.Colors.BOLD}{line}")
        print(f"{text}")
        print(f"{line}{self.Colors.ENDC}")

    def print_subheader(self, text: str, color: Optional[str] = None) -> None:
        subheader_color = color if color is not None else self.Colors.OKBLUE
        print(f"\n{subheader_color}{self.Colors.BOLD}📊 {text}{self.Colors.ENDC}")
        print(f"{self.Colors.GRAY}{'─' * (len(text) + 3)}{self.Colors.ENDC}")

    def print_test_case_header(
        self, test_number: Optional[int] = None, total_tests: Optional[int] = None, query: str = ""
    ) -> None:
        query_preview = query[:100] + "..." if len(query) > 100 else query

        if test_number and total_tests:
            print(
                f"\n{self.Colors.HEADER}{self.Colors.BOLD}🧪 Test Case {test_number}/{total_tests}{self.Colors.ENDC}"
            )
        else:
            print(f"\n{self.Colors.HEADER}{self.Colors.BOLD}🧪 Test Case{self.Colors.ENDC}")

        print(f"{self.Colors.GRAY}{'─' * 60}{self.Colors.ENDC}")
        print(f"{self.Colors.OKBLUE}{self.Colors.BOLD}Query:{self.Colors.ENDC} {query_preview}")

    def print_processing_status(self, message: str) -> None:
        print(f"{self.Colors.GRAY}⏳ {message}{self.Colors.ENDC}")

    def print_evaluation_status(self) -> None:
        print(f"\n{self.Colors.GRAY}🔍 Evaluating response...{self.Colors.ENDC}")

    def print_test_result(self, status: str, reasoning: Optional[str] = None) -> None:
        if status == "passed":
            icon = "✅"
            color = self.Colors.OKGREEN
            status_text = "PASSED"
        elif status == "partial":
            icon = "🟡"
            color = self.Colors.WARNING
            status_text = "PARTIAL"
        else:
            icon = "❌"
            color = self.Colors.FAIL
            status_text = "FAILED"

        print(f"{color}{self.Colors.BOLD}{icon} {status_text}{self.Colors.ENDC}")
        if reasoning:
            print(f"{self.Colors.GRAY}   Reason: {reasoning}{self.Colors.ENDC}")

    def print_response_summary(
        self,
        final_response: str,
        datasets: List[str],
        sql_queries: List[str],
        tool_messages: List[str],
        visualization_results: Optional[List[str]] = None,
    ) -> None:
        response_preview = (
            final_response[:300] + "..." if len(final_response) > 300 else final_response
        )

        print(f"\n{self.Colors.OKCYAN}{self.Colors.BOLD}📝 Response Summary:{self.Colors.ENDC}")
        print(f"{self.Colors.GRAY}┌─ AI Response (preview):{self.Colors.ENDC}")
        print(f"{self.Colors.GRAY}│{self.Colors.ENDC} {response_preview}")

        print(
            f"{self.Colors.GRAY}├─ Datasets Used:{self.Colors.ENDC} {self.Colors.LIGHT_BLUE}{len(datasets)} dataset(s){self.Colors.ENDC}"
        )
        if datasets:
            for i, dataset in enumerate(datasets, 1):
                print(f"{self.Colors.GRAY}│  {i}. {dataset}{self.Colors.ENDC}")

        print(
            f"{self.Colors.GRAY}├─ SQL Queries:{self.Colors.ENDC} {self.Colors.LIGHT_GREEN}{len(sql_queries)} query(s){self.Colors.ENDC}"
        )
        if sql_queries:
            for i, query in enumerate(sql_queries, 1):
                query_preview = query[:80] + "..." if len(query) > 80 else query
                print(f"{self.Colors.GRAY}│  {i}. {query_preview}{self.Colors.ENDC}")

        # Check if we have visualization results to show
        if visualization_results:
            print(
                f"{self.Colors.GRAY}├─ Visualizations:{self.Colors.ENDC} {self.Colors.PURPLE}{len(visualization_results)} result(s){self.Colors.ENDC}"
            )
            for i, viz_result in enumerate(visualization_results, 1):
                viz_preview = viz_result[:80] + "..." if len(viz_result) > 80 else viz_result
                print(f"{self.Colors.GRAY}│  {i}. {viz_preview}{self.Colors.ENDC}")

            print(
                f"{self.Colors.GRAY}└─ Processing Steps:{self.Colors.ENDC} {self.Colors.LIGHT_YELLOW}{len(tool_messages)} step(s){self.Colors.ENDC}"
            )
        else:
            print(
                f"{self.Colors.GRAY}└─ Processing Steps:{self.Colors.ENDC} {self.Colors.LIGHT_YELLOW}{len(tool_messages)} step(s){self.Colors.ENDC}"
            )

        if tool_messages:
            for i, message in enumerate(tool_messages, 1):
                print(f"{self.Colors.GRAY}   {i}. {message}{self.Colors.ENDC}")

    def print_error(self, error_message: str, traceback_info: Optional[str] = None) -> None:
        print(f"\n{self.Colors.FAIL}{self.Colors.BOLD}❌ API Request Failed{self.Colors.ENDC}")
        print(f"{self.Colors.FAIL}Error: {error_message}{self.Colors.ENDC}")
        if traceback_info:
            print(f"{self.Colors.GRAY}Traceback:{self.Colors.ENDC}")
            print(f"{self.Colors.GRAY}{traceback_info}{self.Colors.ENDC}")

    def print_framework_header(self, start_time: datetime) -> None:
        self.print_header("🚀 E2E TESTING FRAMEWORK", "=", self.Colors.HEADER)
        print(
            f"{self.Colors.GRAY}Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}{self.Colors.ENDC}"
        )

    def print_test_suite_info(self, test_count: int, test_type: str, server_url: str) -> None:
        self.print_subheader(
            f"Running {test_count} {test_type} dataset test(s) against {server_url}"
        )

    def print_results_summary(
        self, results: List[Dict[str, Any]], test_type: str, server_url: str, start_time: datetime
    ) -> None:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate pass/partial/fail based on evaluation_score
        passed = sum(1 for r in results if r.get("evaluation_score", 0) >= 8)
        partial = sum(1 for r in results if 5 <= r.get("evaluation_score", 0) < 8)
        failed = sum(1 for r in results if r.get("evaluation_score", 0) < 5)

        self.print_header("📊 TEST RESULTS SUMMARY", "=", self.Colors.HEADER)

        print(
            f"{self.Colors.BOLD}🌐 Server:{self.Colors.ENDC} {self.Colors.OKCYAN}{server_url}{self.Colors.ENDC}"
        )
        print(
            f"{self.Colors.BOLD}📋 Test Type:{self.Colors.ENDC} {self.Colors.OKCYAN}{test_type.upper()}{self.Colors.ENDC}"
        )
        print(
            f"{self.Colors.BOLD}⏱️  Duration:{self.Colors.ENDC} {self.Colors.OKCYAN}{duration:.2f}s{self.Colors.ENDC}"
        )
        print(
            f"{self.Colors.BOLD}📊 Total Tests:{self.Colors.ENDC} {self.Colors.OKCYAN}{len(results)}{self.Colors.ENDC}"
        )

        print(f"\n{self.Colors.BOLD}📈 Results Breakdown:{self.Colors.ENDC}")
        total = len(results)
        if total == 0:
            print(f"  {self.Colors.WARNING}⚠️  No tests were executed{self.Colors.ENDC}")
        else:
            print(
                f"  {self.Colors.OKGREEN}✅ Passed:{self.Colors.ENDC}   {self.Colors.OKGREEN}{self.Colors.BOLD}{passed:2d}{self.Colors.ENDC} ({passed/total*100:.1f}%)"
            )
            print(
                f"  {self.Colors.WARNING}🟡 Partial:{self.Colors.ENDC}  {self.Colors.WARNING}{self.Colors.BOLD}{partial:2d}{self.Colors.ENDC} ({partial/total*100:.1f}%)"
            )
            print(
                f"  {self.Colors.FAIL}❌ Failed:{self.Colors.ENDC}   {self.Colors.FAIL}{self.Colors.BOLD}{failed:2d}{self.Colors.ENDC} ({failed/total*100:.1f}%)"
            )

        avg_duration = duration / len(results) if results else 0
        print(f"\n{self.Colors.BOLD}⚡ Performance Metrics:{self.Colors.ENDC}")
        print(f"  {self.Colors.GRAY}Average test duration: {avg_duration:.2f}s{self.Colors.ENDC}")

        if failed > 0 or partial > 0:
            self._print_detailed_failures(results)

    def _print_detailed_failures(self, results: List[Dict[str, Any]]) -> None:
        self.print_header("🔍 DETAILED FAILURES & PARTIALS", "-", self.Colors.WARNING)

        for i, test in enumerate(results, 1):
            score = test.get("evaluation_score", 0)
            if score < 8:
                status = "PARTIAL" if score >= 5 else "FAILED"
                status_color = self.Colors.WARNING if score >= 5 else self.Colors.FAIL
                icon = "🟡" if score >= 5 else "❌"

                print(
                    f"\n{status_color}{self.Colors.BOLD}{icon} Test {i}: {status} (Score: {score}/10){self.Colors.ENDC}"
                )
                print(f"{self.Colors.GRAY}Query:{self.Colors.ENDC} {test['query'][:100]}...")
                print(f"{self.Colors.GRAY}Reason:{self.Colors.ENDC} {test['reasoning']}")
                print(
                    f"{self.Colors.GRAY}Expected SQL Count:{self.Colors.ENDC} {test['expected_sql_count']}"
                )
                print(
                    f"{self.Colors.GRAY}Actual SQL Count:{self.Colors.ENDC} {test['sql_query_count']}"
                )
                print(
                    f"{self.Colors.GRAY}Expected Dataset:{self.Colors.ENDC} {test['expected_dataset']}"
                )
                print(f"{self.Colors.GRAY}Used Datasets:{self.Colors.ENDC} {test['used_datasets']}")

    def print_progress_bar(self, current: int, total: int, width: int = 50) -> None:
        progress = current / total
        filled_width = int(width * progress)
        bar = "█" * filled_width + "░" * (width - filled_width)
        percentage = progress * 100

        print(
            f"\r{self.Colors.OKCYAN}Progress: {self.Colors.ENDC}[{bar}] {percentage:.1f}% ({current}/{total})",
            end="",
            flush=True,
        )
        if current == total:
            print()

    def print_separator(self, char: str = "─", length: int = 60) -> None:
        print(f"{self.Colors.GRAY}{char * length}{self.Colors.ENDC}")

    def print_info(self, message: str, icon: str = "ℹ️") -> None:
        print(f"{self.Colors.OKCYAN}{icon} {message}{self.Colors.ENDC}")

    def print_warning(self, message: str, icon: str = "⚠️") -> None:
        print(f"{self.Colors.WARNING}{icon} {message}{self.Colors.ENDC}")

    def print_success(self, message: str, icon: str = "✅") -> None:
        print(f"{self.Colors.OKGREEN}{icon} {message}{self.Colors.ENDC}")
