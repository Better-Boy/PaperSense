import os
import argparse
import json

from src import config_loader, utils
from src.tests import benchmark, stress

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

def run_test(test_type: str):
    """Run benchmark test with provided data files"""

    console.print()
    console.print(Panel(
        "[bold blue]MindsDB Knowledge Base Test Suite[/bold blue]\n",
        box=box.DOUBLE,
        padding=(1, 2)
    ))

    console.print("Preparing test data....")
    try:
        papers_data_file_path = None
        queries_data_file_path = None
        if test_type == 'benchmark':
            papers_data_file_path = config_loader.benchmark_test.test_data_path
            queries_data_file_path = config_loader.benchmark_test.queries_file_path
        elif test_type == 'stress':
            papers_data_file_path = config_loader.stress_test.test_data_path
            queries_data_file_path = config_loader.stress_test.queries_file_path

        papers_data = load_json_file(papers_data_file_path)
        queries = load_json_file(queries_data_file_path)
        console.print(f"[green] Test data loaded succesfully for {test_type}. Papers Data - {config_loader.benchmark_test.test_data_path}, Queries - {config_loader.benchmark_test.queries_file_path}[/green]")

        for paper in papers_data:
            paper["text"] = utils.escape_text(paper["text"])
            paper["summary"] = utils.escape_text(paper["summary"])
            paper["title"] = utils.escape_text(paper["title"])

    except Exception as e:
        console.log(f"[red] Error preparing test data: {str(e)}[/red]")
        return

    papers_data = papers_data[:1]
    
    if test_type.lower() == 'benchmark':
        test_suite = benchmark.BenchmarkTest()

    if test_type.lower() == 'stress':
        test_suite = stress.StressTest()

    test_suite.start(papers_data, queries)
    test_suite.save_report()

def load_json_file(path: str):
    return json.load(open(path))


def validate_yaml_file(path: str) -> str:
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f"File does not exist: '{path}'")
    if not path.lower().endswith(('.yaml', '.yml')):
        raise argparse.ArgumentTypeError(f"File is not a YAML file: '{path}'")
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MindsDB Benchmark and Stress Testing Suit")

    parser.add_argument('--benchmark', default=False, action='store_true', help='Run benchmark tests')
    parser.add_argument('--stress', default=False, action='store_true', help='Run stress tests')
    parser.add_argument('--path', type=validate_yaml_file, help='Path to configuration yaml file. If not specified, will default to default_config.yaml file in `src` directory')

    args = parser.parse_args()

    if args.path:
        config_loader.set_config(args.path)

    if args.benchmark: 
        run_test("benchmark")

    if args.stress: 
        run_test("stress")
