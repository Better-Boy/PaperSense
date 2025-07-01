#!/usr/bin/env python3
"""
ArXiv Paper Text Extractor - Removes Mathematical Equations and Escapes for SQL
Extracts clean text from arXiv papers while filtering out equations and LaTeX formatting,
then escapes the text for safe SQL database insertion.

Enhanced with Rich module for beautiful console output.
"""

import argparse
import re
import PyPDF2
import string
from pathlib import Path
import json
from typing import Optional, Dict, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.traceback import install
from rich.logging import RichHandler
import logging

# Install rich traceback handler
install(show_locals=True)

# Setup logging with Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("arxiv_extractor")

class ArxivTextExtractor:
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
        # Patterns for different types of equations and LaTeX commands
        self.equation_patterns = [
            # Display equations ($$...$$, \[...\], \begin{equation}...\end{equation})
            r'\$\$.*?\$\$',
            r'\\\[.*?\\\]',
            r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}',
            r'\\begin\{align\*?\}.*?\\end\{align\*?\}',
            r'\\begin\{eqnarray\*?\}.*?\\end\{eqnarray\*?\}',
            r'\\begin\{gather\*?\}.*?\\end\{gather\*?\}',
            r'\\begin\{multline\*?\}.*?\\end\{multline\*?\}',
            r'\\begin\{split\}.*?\\end\{split\}',
            
            # Inline equations ($...$)
            r'\$[^$\n]+\$',
            
            # LaTeX math environments
            r'\\begin\{math\}.*?\\end\{math\}',
            r'\\begin\{displaymath\}.*?\\end\{displaymath\}',
            
            # Numbered equations
            r'\\begin\{equation\}.*?\\end\{equation\}',
            r'\\begin\{align\}.*?\\end\{align\}',
        ]
        
        # LaTeX commands to remove
        self.latex_commands = [
            r'\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})*',  # General LaTeX commands
            r'\\\\',  # Line breaks
            r'\\&',   # Alignment characters
            r'\{|\}', # Braces
            r'\\textbf\{([^}]+)\}',  # Bold text
            r'\\textit\{([^}]+)\}',  # Italic text
            r'\\emph\{([^}]+)\}',    # Emphasized text
            r'\\cite\{[^}]+\}',      # Citations
            r'\\ref\{[^}]+\}',       # References
            r'\\label\{[^}]+\}',     # Labels
        ]
        
        # Patterns for cleaning up formatting
        self.cleanup_patterns = [
            r'\n\s*\n\s*\n+',  # Multiple newlines
            r'^\s+|\s+$',       # Leading/trailing whitespace
            r'[ \t]+',          # Multiple spaces/tabs
            r'[^\x00-\x7F]+',   # Non-ASCII characters (optional)
        ]

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract raw text from PDF file."""
        text = ""
        try:
            if isinstance(pdf_file, (str, Path)):
                with open(pdf_file, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            else:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_file}: {e}")
            raise Exception(f"Failed to extract text from PDF: {e}")
        
        return text

    def remove_equations(self, text: str) -> str:
        """Remove mathematical equations from text."""
        # Remove equations (use DOTALL flag to match across newlines)
        for pattern in self.equation_patterns:
            text = re.sub(pattern, ' ', text, flags=re.DOTALL)
        
        return text

    def remove_latex_commands(self, text: str) -> str:
        """Remove LaTeX formatting commands."""
        for pattern in self.latex_commands:
            # For text formatting commands, keep the content
            if r'\{([^}]+)\}' in pattern:
                text = re.sub(pattern, r'\1', text)
            else:
                text = re.sub(pattern, ' ', text)
        
        return text

    def clean_text(self, text: str) -> str:
        """Clean up the text formatting."""
        # Remove extra whitespace and newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Leading/trailing whitespace
        
        # Remove common LaTeX artifacts
        text = re.sub(r'\\[a-zA-Z]+\*?', '', text)  # Remaining LaTeX commands
        text = re.sub(r'[{}]', '', text)  # Remaining braces
        text = re.sub(r'\\\\', '', text)  # Remaining line breaks
        
        # Clean up punctuation spacing
        text = re.sub(r'\s+([.,;:])', r'\1', text)  # Space before punctuation
        text = re.sub(r'([.,;:])\s*\n', r'\1\n', text)  # Punctuation at line end
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control chars
        translator = str.maketrans("", "", string.punctuation)
        text = text.strip().translate(translator)

        return text.strip()

    def escape_for_sql(self, text: str) -> str:
        """
        Escape text for SQL database insertion.
        
        Args:
            text (str): The text to escape
            
        Returns:
            str: SQL-escaped text
        """
        text = text.replace('\\', '\\\\')  # Escape backslashes first
        text = text.replace("'", "''")     # Escape single quotes
        text = text.replace('"', '""')     # Escape double quotes
        text = text.replace('\n', '\\n')   # Escape newlines
        text = text.replace('\r', '\\r')   # Escape carriage returns
        text = text.replace('\t', '\\t')   # Escape tabs
        text = text.replace('\0', '')   # Escape null bytes
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control chars
        return text

    def process_text(self, text: str, task_id: Optional[int] = None, progress: Optional[Progress] = None) -> str:
        """Main processing pipeline with progress tracking."""
        steps = [
            ("Removing equations", self.remove_equations),
            ("Removing LaTeX commands", self.remove_latex_commands),
            ("Cleaning text", self.clean_text)
        ]
        
        for step_name, step_func in steps:
            if progress and task_id is not None:
                progress.update(task_id, description=f"[cyan]{step_name}...")
            text = step_func(text)
        
        # Store processed text for parameterized queries
        self.processed_text = text
        
        return text

    def extract_from_arxiv(self, arxiv_id: str) -> str:
        """Extract text from arXiv paper by ID."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Processing arXiv paper: {arxiv_id}", total=None)
            
            progress.update(task, description=f"[yellow]Downloading arXiv paper: {arxiv_id}")
            pdf_file = self.download_arxiv_pdf(arxiv_id)
            
            progress.update(task, description="[blue]Extracting text from PDF...")
            raw_text = self.extract_text_from_pdf(pdf_file)
            
            progress.update(task, description="[green]Processing text...")
            return self.process_text(raw_text)
    
    def extract_from_file(self, pdf_file: Path, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Extract text from a single PDF file."""
        if not hasattr(self, 'metadata') or arxiv_id not in self.metadata:
            return None
            
        try:
            raw_text = self.extract_text_from_pdf(pdf_file)
            full_text = self.process_text(raw_text)
            return {"text": full_text}
        except Exception as e:
            logger.error(f"Error processing file {pdf_file}: {e}")
            return None

    def load_metadata(self, metadata_path: str) -> None:
        """Load metadata from JSON file."""
        try:
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            self.console.print(f"[green]✓[/green] Loaded metadata for {len(self.metadata)} papers")
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            raise

    def process_bulk_files(self, pdf_folder: str, metadata_file_path: str) -> None:
        """Process all PDF files in the folder with Rich progress tracking."""
        
        # Display header
        self.console.print()
        self.console.print(Panel.fit(
            "[bold blue]ArXiv Paper Text Extractor[/bold blue]\n"
            "[dim]Extracting clean text from academic papers[/dim]",
            border_style="blue"
        ))
        self.console.print()

        # Load metadata
        with self.console.status("[bold green]Loading metadata..."):
            self.load_metadata(metadata_file_path)

        # Get list of files
        path = Path(pdf_folder)
        files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        
        if not files:
            self.console.print("[red]No PDF files found in the specified folder![/red]")
            return

        # Display processing information
        info_table = Table(box=box.ROUNDED)
        info_table.add_column("Setting", style="cyan")
        info_table.add_column("Value", style="green")
        info_table.add_row("PDF Folder", str(path))
        info_table.add_row("Metadata File", metadata_file_path)
        info_table.add_row("Total Files", str(len(files)))
        info_table.add_row("Save Interval", "Every 1000 files")
        
        self.console.print(info_table)
        self.console.print()

        output = []
        processed_count = 0
        error_count = 0

        # Main processing loop with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[blue]{task.completed}/{task.total} files"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task("[green]Processing PDF files...", total=len(files))
            
            for i, file in enumerate(files):
                progress.update(main_task, description=f"[green]Processing: {file.name}")
                
                try:
                    arxiv_id = file.name.replace("v1.pdf", "")
                    text_json = self.extract_from_file(file, arxiv_id)
                    
                    if text_json is not None:
                        output.append(text_json | self.metadata.get(arxiv_id, {}))
                        processed_count += 1
                    
                    # Save intermediate results every 1000 files
                    if (i + 1) % 1000 == 0:
                        output_file = f"../processed_data_{i + 1}.json"
                        self._save_results(output, output_file)
                        progress.print(f"[yellow]💾 Saved intermediate results to {output_file}[/yellow]")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing {file.name}: {e}")
                
                progress.update(main_task, advance=1)

        # Save final results
        final_output_file = "processed_data.json"
        self._save_results(output, final_output_file)

        # Display final statistics
        self.console.print()
        stats_panel = Panel(
            f"[bold green]Processing Complete![/bold green]\n\n"
            f"[cyan]Files processed successfully:[/cyan] {processed_count}\n"
            f"[red]Files with errors:[/red] {error_count}\n"
            f"[yellow]Total files processed:[/yellow] {len(files)}\n"
            f"[blue]Final output saved to:[/blue] {final_output_file}",
            title="📊 Results Summary",
            border_style="green"
        )
        self.console.print(stats_panel)

    def _save_results(self, output: list, filename: str) -> None:
        """Save results to JSON file with error handling."""
        try:
            with open(filename, "w", encoding="utf-16", errors="ignore") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save results to {filename}: {e}")
            raise


def main():
    console = Console()
    
    parser = argparse.ArgumentParser(
        description='ArXiv bulk data processor with Rich UI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pdf-folder ./pdfs --metadata-file-path ./metadata.json
  %(prog)s --pdf-folder /path/to/arxiv/pdfs --metadata-file-path /path/to/metadata.json
        """
    )
    parser.add_argument(
        '--pdf-folder', 
        type=str, 
        required=True, 
        help='Path to the folder containing raw arxiv PDFs'
    )
    parser.add_argument(
        '--metadata-file-path', 
        type=str, 
        required=True, 
        help='Path to the metadata file. A sample is attached in this repo `data` folder.'
    )
    
    args = parser.parse_args()

    # Validate arguments
    pdf_path = Path(args.pdf_folder)
    metadata_path = Path(args.metadata_file_path)
    
    if not pdf_path.exists():
        console.print(f"[red]Error: PDF folder '{pdf_path}' does not exist![/red]")
        return 1
    
    if not metadata_path.exists():
        console.print(f"[red]Error: Metadata file '{metadata_path}' does not exist![/red]")
        return 1

    # Create extractor and process files
    try:
        arxiv_extractor = ArxivTextExtractor(console)
        arxiv_extractor.process_bulk_files(args.pdf_folder, args.metadata_file_path)
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Processing interrupted by user.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        return 1


if __name__ == "__main__":
    exit(main())