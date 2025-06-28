import os
import argparse
import json

import psutil

from src import config_loader, utils
from src.tests import benchmark, stress

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


def run_test(test_type: str, mindsdb_pid: str):
    """Run benchmark test with provided data files"""

    console.print()
    console.print(
        Panel(
            "[bold blue]MindsDB Knowledge Base Test Suite[/bold blue]\n",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )

    console.print("Preparing test data....")
    try:
        papers_data_file_path = None
        queries_data_file_path = None
        if test_type == "benchmark":
            papers_data_file_path = config_loader.benchmark_test.test_data_path
            queries_data_file_path = config_loader.benchmark_test.queries_file_path
        elif test_type == "stress":
            papers_data_file_path = config_loader.stress_test.test_data_path
            queries_data_file_path = config_loader.stress_test.queries_file_path

        papers_data = load_json_file(papers_data_file_path)
        queries = load_json_file(queries_data_file_path)
        console.print(
            f"[green] Test data loaded succesfully for {test_type}. Papers Data - {config_loader.benchmark_test.test_data_path}, Queries - {config_loader.benchmark_test.queries_file_path}[/green]"
        )

    except Exception as e:
        console.log(f"[red] Error preparing test data: {str(e)}[/red]")
        return

    if test_type.lower() == "benchmark":
        test_suite = benchmark.BenchmarkTester(mindsdb_pid=mindsdb_pid)

    
    if test_type.lower() == "stress":
        test_suite = stress.ConcurrentTester(mindsdb_pid=mindsdb_pid)

    test_suite.start(papers_data, queries)
    test_suite.save_report()


def load_json_file(path: str):
    if 'new_data' in path:
        d = json.load(open(path, "r", encoding="utf-16"))
        return d
    return json.load(open(path))


def validate_pid(pid):
    pid = int(pid)
    psutil.Process(pid)
    return pid


def validate_yaml_file(path: str) -> str:
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f"File does not exist: '{path}'")
    if not path.lower().endswith((".yaml", ".yml")):
        raise argparse.ArgumentTypeError(f"File is not a YAML file: '{path}'")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MindsDB Benchmark and Stress Testing Suit"
    )

    parser.add_argument(
        "--benchmark", 
        default=False, 
        action="store_true", 
        help="Run benchmark tests"
    )
    parser.add_argument(
        "--mdb_pid", 
        type=validate_pid,
        required=True, 
        help="MindsDB pid. Run (ps -ef | grep mindsdb) to find the pid of mindsdb"
    )
    parser.add_argument(
        "--stress", default=False, action="store_true", help="Run stress tests"
    )
    parser.add_argument(
        "--path",
        type=validate_yaml_file,
        help="Path to configuration yaml file. If not specified, will default to default_config.yaml file in `src` directory",
    )

    args = parser.parse_args()

    if args.path:
        config_loader.set_config(args.path)

    if args.benchmark:
        run_test("benchmark", args.mdb_pid)

    if args.stress:
        run_test("stress", args.mdb_pid)
