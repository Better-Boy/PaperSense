import os
import platform
import statistics
import sys
import time
from typing import List, Dict, Any

from abc import ABC, abstractmethod
import psutil
from rich.console import Console

from src import utils, config_loader
from src.tests.models import ExecutionResult, ResourceSnapshot

from .system_monitor import ResourceMonitor
from src.MindsDBMiddleware import knowledge_base, manager
from .. import config_loader as config

console = Console()


class MindsDBKnowledgeBaseTest(ABC):
    """Main test suite class"""

    def __init__(self, mindsdb_pid: str):
        self.test_script_monitor = ResourceMonitor(os.getpid())
        self.mindsdb_server_monitor = ResourceMonitor(mindsdb_pid)
        self._mdb = manager.MindsDBManager()
        self._kb = knowledge_base.KnowledgeBase(self._mdb)
        self.kb_name = config.kb.name
        self.results: List[ExecutionResult] = []

    @abstractmethod
    def save_report(self):
        pass

    @abstractmethod
    def start(
        self, files_data: List[Dict[str, Any]], queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
            console.print(
                f"[green]✓ Knowledge base '{self.kb_name}' created in {creation_time:.2f}s[/green]"
            )
            return True
        except Exception as e:
            console.print(f"[red]✗ Failed to create knowledge base: {e}[/red]")
            return False

    def cleanup_knowledge_base(self):
        """Cleanup knowledge base after testing"""
        try:
            self._kb.drop(self.kb_name)
            console.print(
                f"[green]✓ Knowledge base '{self.kb_name}' cleaned up[/green]"
            )
        except Exception as e:
            console.print(f"[red]✗ Failed to cleanup knowledge base: {e}[/red]")

    def break_file_into_chunks(self, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        metadata = {k: v for k, v in file_data.items() if k != "text"}
        chunks = utils.chunk_text(file_data["text"])
        for chunk in chunks:
            chunk.update(metadata)
        return chunks
    
    def clear_results(self):
        """Clear all benchmark results"""
        self.results.clear()

    def test_environment_info(self):
        software = {}
        hardware = {}

        # OS and Python
        software['OS'] = platform.platform()
        software['Python Version'] = sys.version.split()[0]
        software['MindsDB Version'] = '25.6.3.1'
        software['Knowledge Base Embedding Model'] = config_loader.kb.embedding_model
        software['Knowledge Base ReRanking Model'] = config_loader.kb.reranking_model
        hardware['Machine'] = platform.machine()
        hardware['Processor'] = platform.processor()
        hardware['CPU Cores'] = psutil.cpu_count()
        hardware['RAM (GB)'] = round(psutil.virtual_memory().total / (1024**3), 2)
        
        # Disk info
        disk = psutil.disk_usage('/')
        hardware['Disk Total (GB)'] = round(disk.total / (1024**3), 2)
        
        md = ""

        md += "## Test Environment\n"
        md += "---"
        md += "### Software Specs\n"
        for key, value in software.items():
            md += f"- **{key}**: {value}\n"
        md += "### Hardware Specs\n"
        for key, value in hardware.items():
            md += f"- **{key}**: {value}\n"

        return md
    

