import time
import psutil
import concurrent.futures
from typing import List, Dict, Any
import statistics
import traceback

from abc import ABC, abstractmethod
from dataclasses import asdict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import box

from ..models.metrics import BatchMetrics, FileMetrics
from .system_monitor import SystemMonitor
from ..mindsdb import knowledge_base, mdb_server
from .. import utils, config_loader as config

console = Console()

class MindsDBKnowledgeBaseTest(ABC):
    """Main test suite class"""
    
    def __init__(self):
        self.monitor = SystemMonitor()
        self._mdb = mdb_server.MDBServer()
        self._kb = knowledge_base.KnowledgeBase(self._mdb)
        self.kb_name = config.kb.name
    
    @abstractmethod
    def save_report(self):
        pass

    @abstractmethod
    def start(self, files_data: List[Dict[str, Any]], queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass
            
    def create_knowledge_base(self) -> bool:
        """Create knowledge base for testing"""
        try:
            if self.kb_name in self._kb.list_knowledge_bases():
                    self._kb.drop(self.kb_name)
                    console.print(f"Dropped existing knowledge base: {self.kb_name}")

            start_time = time.time()
            self._kb.create(self.kb_name)
            creation_time = time.time() - start_time
            
            # self.test_results['metadata']['kb_creation_time'] = creation_time
            console.print(f"[green]✓ Knowledge base '{self.kb_name}' created in {creation_time:.2f}s[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Failed to create knowledge base: {e}[/red]")
            return False
            
    def cleanup_knowledge_base(self):
        """Cleanup knowledge base after testing"""
        try:
            self._kb.drop(self.kb_name)
            console.print(f"[green]✓ Knowledge base '{self.kb_name}' cleaned up[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to cleanup knowledge base: {e}[/red]")

    def process_chunks_batch(self, chunks: List[Dict[str, Any]]) -> BatchMetrics:
        """Process a batch of chunks and return metrics"""
        
        for chunk in chunks:
            del chunk["size_bytes"]
        
        batch_start_time = time.time()
        # memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        errors = 0
        try:
            if not self._kb.insert_batch(self.kb_name, chunks):
                raise Exception("Batch processing failed")
        except Exception as e:
            errors += len(chunks)
            console.print(f"[red]✗ Error processing chunk for {chunk.get('article_id')}: {e}[/red]")
            traceback.print_exc()
                
        batch_total_time = (time.time() - batch_start_time) * 1000
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        
        return BatchMetrics(
            batch_id=id(chunks),
            batch_size=len(chunks),
            total_time_ms=batch_total_time,
            chunks_processed=len(chunks),
            avg_chunk_time_ms=batch_total_time/len(chunks),
            memory_peak_mb=memory_after,
            errors=errors
        )

    def break_file_into_chunks(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        metadata = {k: v for k, v in file_data.items() if k != "text"}
        chunks = utils.chunk_text(file_data["text"])
        for chunk in chunks:
            chunk.update(metadata)
            chunk["size_bytes"] = len(chunk["text"].encode('utf-8'))
        return chunks

    def ingest_data(self, files_data: List[Dict[str, Any]], batch_size: int) -> Dict[str, Any]:
        """Ingest data with specified batch size and collect metrics"""


        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            main_task = progress.add_task(f"[cyan]Ingesting data (batch size: {batch_size})", total=len(files_data))
        
            ingestion_start_time = time.time()
            self.monitor.start_monitoring()
        
            all_chunks = []
            file_metrics = []
            batch_metrics = []

            for i, file_data in enumerate(files_data):
                file_start_time = time.time()
                
                chunks = self.break_file_into_chunks(file_data)
                all_chunks.extend(chunks)
                
                file_processing_time = (time.time() - file_start_time) * 1000
                file_metrics.append(FileMetrics(
                    file_id=f"{file_data.get('article_id')}.pdf",
                    total_chunks=len(chunks),
                    processing_time_ms=file_processing_time,
                    avg_chunks_per_second=len(chunks) / (file_processing_time / 1000) if file_processing_time > 0 else 0,
                    total_size_bytes=sum(chunk['size_bytes'] for chunk in chunks),
                    memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024
                ))
                
                progress.update(main_task, advance=1)

            batch_task = progress.add_task("[blue]Processing chunks in batches", total=len(all_chunks))

            
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i+batch_size]
                batch_metric = self.process_chunks_batch(batch)
                batch_metrics.append(batch_metric)
                
                progress.update(batch_task, advance=len(batch))
                
            self.monitor.stop_monitoring()
            total_ingestion_time = time.time() - ingestion_start_time
            system_metrics = self.monitor.get_peak_metrics()
            
            # Calculate aggregate metrics
            total_chunks = len(all_chunks)
            successful_chunks = sum(bm.chunks_processed for bm in batch_metrics)
            total_errors = sum(bm.errors for bm in batch_metrics)

            table = Table(title="Ingestion Summary", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Batch Size", str(batch_size))
            table.add_row("Total Files", str(len(files_data)))
            table.add_row("Total Chunks", str(total_chunks))
            table.add_row("Successful Chunks", str(successful_chunks))
            table.add_row("Total Errors", str(total_errors))
            table.add_row("Ingestion Time", f"{total_ingestion_time:.2f}s")
            table.add_row("Chunks/Second", f"{total_chunks / total_ingestion_time if total_ingestion_time > 0 else 0:.2f}")
            
            console.print(table)

            avg_time_per_chunk_ms = statistics.mean([bm.avg_chunk_time_ms for bm in batch_metrics]) if batch_metrics else 0

            return {
                'batch_size': batch_size,
                'total_files': len(files_data),
                'total_chunks': total_chunks,
                'successful_chunks': successful_chunks,
                'total_errors': total_errors,
                'total_ingestion_time_s': total_ingestion_time,
                'chunks_per_second': total_chunks / total_ingestion_time if total_ingestion_time > 0 else 0,
                'avg_chunks_per_file': statistics.mean([fm.total_chunks for fm in file_metrics]),
                'avg_time_per_chunk_ms': avg_time_per_chunk_ms,
                'avg_time_per_1000_chunks_ms': avg_time_per_chunk_ms * 1000,
                'avg_time_per_batch_ms': statistics.mean([bm.total_time_ms for bm in batch_metrics]) if batch_metrics else 0,
                'system_metrics': system_metrics,
                'file_metrics': [asdict(fm) for fm in file_metrics],
                'batch_metrics': [asdict(bm) for bm in batch_metrics]
            }

    def execute_queries(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute queries and collect latency metrics"""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task(f"[green]Executing {len(queries)} queries", total=len(queries))
        
            query_results = []
            query_start_time = time.time()

            for i, query in enumerate(queries):
                single_query_start = time.time()
                
                try:
                    _ = self._kb.search(self.kb_name, query["query"], {})
                    
                    query_latency = (time.time() - single_query_start) * 1000
                    query_results.append({
                        'query_id': i,
                        'query_type': query.get('type', 'unknown'),
                        'latency_ms': query_latency,
                        'success': True
                    })
                    
                except Exception as e:
                    query_latency = (time.time() - single_query_start) * 1000
                    query_results.append({
                        'query_id': i,
                        'query_type': query.get('type', 'unknown'),
                        'latency_ms': query_latency,
                        'success': False,
                        'error': str(e)
                    })
                
                progress.update(task, advance=1)
                    
            total_query_time = time.time() - query_start_time

            # Calculate latency statistics
            successful_queries = [qr for qr in query_results if qr['success']]
            latencies = [qr['latency_ms'] for qr in successful_queries]
            
            if latencies:
                latency_stats = {
                    'avg_latency_ms': statistics.mean(latencies),
                    'median_latency_ms': statistics.median(latencies),
                    'p95_latency_ms': self._percentile(latencies, 95),
                    'p99_latency_ms': self._percentile(latencies, 99),
                    'min_latency_ms': min(latencies),
                    'max_latency_ms': max(latencies)
                }
            else:
                latency_stats = {k: 0 for k in ['avg_latency_ms', 'median_latency_ms', 'p95_latency_ms', 'p99_latency_ms', 'min_latency_ms', 'max_latency_ms']}
            
            # Display query results table
            table = Table(title="Query Performance Summary", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Queries", str(len(queries)))
            table.add_row("Successful Queries", str(len(successful_queries)))
            table.add_row("Failed Queries", str(len(queries) - len(successful_queries)))
            table.add_row("Avg Latency", f"{latency_stats['avg_latency_ms']:.2f}ms")
            table.add_row("P95 Latency", f"{latency_stats['p95_latency_ms']:.2f}ms")
            table.add_row("Queries/Second", f"{len(queries) / total_query_time if total_query_time > 0 else 0:.2f}")
            
            console.print(table)


            return {
                'total_queries': len(queries),
                'successful_queries': len(successful_queries),
                'failed_queries': len(queries) - len(successful_queries),
                'total_query_time_s': total_query_time,
                'queries_per_second': len(queries) / total_query_time if total_query_time > 0 else 0,
                'latency_stats': latency_stats,
                'query_results': query_results
            }

    def run_concurrent_queries(self, queries: List[Dict[str, Any]], concurrent_users: int) -> Dict[str, Any]:
        """Execute queries with concurrent users"""
        console.print(Panel(f"[bold blue]Running concurrent queries with {concurrent_users} users[/bold blue]", box=box.ROUNDED))
        
        def execute_query_batch(query_batch):
            results = []
            for query in query_batch:
                start_time = time.time()
                try:
                    _ = self._kb.search(self.kb_name, query["query"], {})
                    latency = (time.time() - start_time) * 1000
                    results.append({'latency_ms': latency, 'success': True})
                    time.sleep(0.5)
                except Exception as e:
                    latency = (time.time() - start_time) * 1000
                    results.append({'latency_ms': latency, 'success': False, 'error': str(e)})
            return results
            
        # Distribute queries among concurrent users
        queries_per_user = len(queries) // concurrent_users
        query_batches = [queries[i:i+queries_per_user] for i in range(0, len(queries), queries_per_user)]
        
        concurrent_start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(f"[yellow]Concurrent execution ({concurrent_users} users)", total=len(query_batches))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                future_to_batch = {executor.submit(execute_query_batch, batch): batch for batch in query_batches}
                all_results = []
                
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    progress.update(task, advance=1)
                    
        total_concurrent_time = time.time() - concurrent_start_time
        
        # Calculate metrics
        successful_results = [r for r in all_results if r['success']]
        latencies = [r['latency_ms'] for r in successful_results]
        
        return {
            'concurrent_users': concurrent_users,
            'total_queries': len(all_results),
            'successful_queries': len(successful_results),
            'total_time_s': total_concurrent_time,
            'throughput_qps': len(all_results) / total_concurrent_time if total_concurrent_time > 0 else 0,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'p95_latency_ms': self._percentile(latencies, 95) if latencies else 0,
            'p99_latency_ms': self._percentile(latencies, 99) if latencies else 0
        }

    def _calculate_average_metrics(self, results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate average metrics across multiple test iterations"""
        if not results_list:
            return {}
            
        avg_metrics = {}
        numeric_keys = ['total_ingestion_time_s', 'chunks_per_second', 'avg_time_per_chunk_ms', 'avg_time_per_1000_chunks_ms']
        
        for key in numeric_keys:
            values = [r.get(key, 0) for r in results_list if key in r]
            if values:
                avg_metrics[key] = statistics.mean(values)
                avg_metrics[f'{key}_std'] = statistics.stdev(values) if len(values) > 1 else 0
                
        return avg_metrics

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def load_baseline_metrics(self):
        return None