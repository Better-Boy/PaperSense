from itertools import cycle
import argparse
import sys
from datetime import datetime
import gevent
from locust import HttpUser, between, task
from locust.env import Environment
from locust.stats import stats_history, stats_printer
from locust.log import setup_logging

from utils import *

# Global variables for test configuration
config = None
search_queries_cycle = None
records_cycle = None
api_errors = {
    'ingest': [],
    'search': []
}

class KBTestUser(HttpUser):
    weight = 1
    wait_time = between(1, 5)

    def log_api_error(self, endpoint_type, status_code, error_message, response_text=None):
        """Log API errors for detailed reporting"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'status_code': status_code,
            'error_message': error_message,
            'response_text': response_text[:500] if response_text else None,  # Truncate long responses
            'user_id': getattr(self, 'user_id', 'unknown')
        }
        api_errors[endpoint_type].append(error_entry)
    
    @task(3)
    def ingest_data(self):
        """Ingest data"""
        
        insert_query = next(records_cycle)
        
        with self.client.post(
            "/api/sql/query",
            json={'query': insert_query, 'context': {'db': 'mindsdb'}},
            catch_response=True,
            timeout=30,
            name="ingest"
        ) as response:
            if response.status_code == 200:
                res = response.json()
                if res["type"] == "error":
                    error_msg = f"Ingestion failed: {response.status_code}"
                    self.log_api_error('ingest', response.status_code, error_msg, response.text)
                    response.failure(error_msg)
                else: response.success()
            else:
                error_msg = f"Ingestion failed: {response.status_code}"
                self.log_api_error('ingest', response.status_code, error_msg, response.text)
                response.failure(error_msg)
    
    @task(2)
    def search(self):
        """Perform simple search operations"""
        
        query = next(search_queries_cycle)
        select_query = f"SELECT * from arxiv_test_kb where content = '{query}';"
        
        with self.client.post(
            "/api/sql/query",
            json={'query': select_query, 'context': {'db': 'mindsdb'}},
            catch_response=True,
            timeout=30,
            name="search"
        ) as response:
            if response.status_code == 200:
                res = response.json()
                if res["type"] == "error":
                    error_msg = f"Search failed: {response.status_code}"
                    self.log_api_error('search', response.status_code, error_msg, response.text)
                    response.failure(error_msg)
                else: response.success()
            else:
                error_msg = f"Search failed: {response.status_code}"
                self.log_api_error('search', response.status_code, error_msg, response.text)
                response.failure(error_msg)

def main():
    """Main function to run the test"""
    global config, search_queries_cycle, records_cycle, api_errors

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MindsDB Knowledge Base Test')
    parser.add_argument('--data-file-path', type=str, required=True, help='Path to the json data file to be ingested to KB')
    parser.add_argument('--search-query-file-path', type=str, required=True, help='Path to the json search queries file to be searched on KB')
    parser.add_argument('--data-size', type=int, default=1000, help='Total amount of data to process')
    parser.add_argument('--host', type=str, default='http://localhost:47334', help='MindsDB server host')
    parser.add_argument('--users', type=int, default=3, help='Number of concurrent users')
    parser.add_argument('--spawn-rate', type=int, default=2, help='Users spawned per second')
    parser.add_argument('--run-time', type=str, default='60', help='Test duration. Unit is in seconds')
    parser.add_argument('--mdb-pid', type=validate_pid, required=True, default=None, help='Mindsdb server pid')
    
    args = parser.parse_args()

    validate_args(parser=parser, args=args)
    
    config = {
        'data_size': args.data_size,
        'host': args.host,
        'users': args.users,
        'spawn_rate': args.spawn_rate,
        'run_time': args.run_time,
        'data_file_path': args.data_file_path,
        'search_queries_file_path': args.search_query_file_path,
        'mdb_pid': str(args.mdb_pid)
    }

    test_type = "stress"

    if config["users"] <= 10 and config["data_size"] <= 1000:
        test_type = "benchmark"

    ps_record_process = start_resource_monitor_process(args.mdb_pid, test_type)

    print(f"Loading test data files - {args.search_query_file_path} and {args.data_file_path}")

    records, data_size_mb = load_ingestion_data(args.data_file_path, config["data_size"])
    search_queries_cycle = cycle([q["query"] for q in load_search_queries(args.search_query_file_path)])
    records_cycle = cycle(records)

    
    print(f"Succesfully loaded test data files - {args.search_query_file_path} and {args.data_file_path}")

    print(f"Starting test with data size: {config["data_size"]}")
    
    print("Setting up knowledge base - arxiv_test_kb")
    status, kb_create_time_taken = setup_kb(config["host"])
    # Setup KB
    if not status:
        print("Failed to setup KB. Exiting.")
        sys.exit(1)
    
    # Setup Locust environment
    setup_logging("INFO", None)
    
    # Create environment
    env = Environment(user_classes=[KBTestUser], host=args.host)
    runner = env.create_local_runner()

    # Enable stats history for better reporting
    env.stats.reset_all()
    
    start_time = datetime.now()
    
    try:
        gevent.spawn(stats_printer(env.stats))

        # start a greenlet that save current stats to history
        gevent.spawn(stats_history, env.runner)

        # Start test
        runner.start(args.users, spawn_rate=args.spawn_rate)
        
        run_time_seconds = int(args.run_time)
        
        print(f"Running {test_type} test for {run_time_seconds} seconds...")
        print(f"Target: {args.host}")
        print(f"Users: {args.users}, Spawn Rate: {args.spawn_rate}/s")
        print("-" * 60)
        
        # Run the test
        gevent_timer = None
        
        gevent_timer = gevent.spawn_later(run_time_seconds, lambda: env.runner.quit())
        
        # Wait for test completion
        runner.greenlet.join()
        
        if gevent_timer:
            gevent_timer.kill()

            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        runner.stop()
    
    except Exception as e:
        print(f"Test error: {e}")
        runner.stop()
    
    finally:
        end_time = datetime.now()
        
        # Generate final stats
        print("\n" + "="*60)
        print("TEST COMPLETED")
        print("="*60)
        
        # Print summary stats
        stats = env.stats
        total_stats = stats.total
        kb_row_cnt = row_count_kb(config["host"])
        print(f"Test Duration: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"Total Requests: {total_stats.num_requests:,}")
        print(f"Total Failures: {total_stats.num_failures:,}")
        print(f"Success Rate: {((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0:.2f}%")
        print(f"Average Response Time: {total_stats.avg_response_time:.2f}ms")
        print(f"Requests per Second: {total_stats.total_rps:.2f}")
        print(f"Max Response Time: {total_stats.max_response_time:.2f}ms")
        print(f"95th Percentile: {total_stats.get_response_time_percentile(0.95):.2f}ms")
        
        status, kb_cleanup_time = cleanup_kb(config["host"])
        # Cleanup kb
        if not status:
            print("Warning: KB cleanup may have failed")
        
    ps_record_process.terminate()
    ps_record_process.wait()
    kb_times = {"create": kb_create_time_taken, "delete": kb_cleanup_time, "row_cnt": kb_row_cnt}
    # Generate comprehensive report
    import report
    report_file = report.Report().generate_report(stats, start_time, end_time, config, kb_times, data_size_mb, test_type, api_errors)
    print(f"\nDetailed report saved to: {report_file}")

    print(f"\n{test_type} test completed successfully!")

if __name__ == "__main__":
    main()

# Command to run -  python stress.py --data-file-path /home/abhi/latest/PaperSense/data/test_data.json --search-query-file-path /home/abhi/latest/PaperSense/data/queries.json --data-size 500 --host http://127.0.0.1:47334 --users 3 --spawn-rate 1  --run-time 5 --mdb-pid <pid>