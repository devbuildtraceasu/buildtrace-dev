#!/usr/bin/env python3
"""
Batch processing script to run attempt1_captioning.py for all PDFs in the Evals folder.

Output structure:
    timestamp/
        drawing_name/
            gemini/
                [all gemini outputs]
            gpt/
                [all gpt outputs]
        drawing_name2/
            ...
"""

import argparse
import subprocess
import sys
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import time


def setup_logging(log_file: Path) -> logging.Logger:
    """Setup logging to both file and console."""
    logger = logging.getLogger("batch_processor")
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler - detailed logging
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - info and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def find_pdfs(root_dir: Path) -> List[Path]:
    """Find all PDF files recursively in the directory, filtering for _new and _old only."""
    pdfs = []
    for pdf_path in root_dir.rglob("*.pdf"):
        # Only include PDFs ending with _new.pdf or _old.pdf
        # Exclude _overlay.pdf and any other suffixes
        pdf_name = pdf_path.stem.lower()
        if pdf_name.endswith("_new") or pdf_name.endswith("_old"):
            pdfs.append(pdf_path)
        else:
            # Log skipped files at debug level
            pass
    return sorted(pdfs)


def run_captioning(
    pdf_path: Path,
    output_base: Path,
    logger: logging.Logger,
    model: str = "both",
    page: int = 0,
    dpi: int = 300
) -> Dict[str, Any]:
    """Run the captioning script for a single PDF with detailed logging."""
    script_path = Path(__file__).parent.parent / "attempt1_captioning.py"
    
    if not script_path.exists():
        error_msg = f"Captioning script not found: {script_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    cmd = [
        sys.executable,
        str(script_path),
        "--pdf", str(pdf_path),
        "--page", str(page),
        "--dpi", str(dpi),
        "--output", str(output_base),
        "--model", model
    ]
    
    logger.info("="*80)
    logger.info(f"Processing: {pdf_path.name}")
    logger.info(f"Full path: {pdf_path}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info(f"Output base: {output_base}")
    logger.info("="*80)
    
    result = {
        "pdf_path": str(pdf_path),
        "pdf_name": pdf_path.name,
        "status": "unknown",
        "error": None,
        "output_dir": str(output_base),
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_seconds": None,
        "stdout": "",
        "stderr": ""
    }
    
    start_time = time.time()
    
    try:
        logger.info(f"Starting subprocess for {pdf_path.name}...")
        
        # Run with real-time output streaming
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time using threads
        stdout_lines = []
        stderr_lines = []
        stdout_lock = threading.Lock()
        stderr_lock = threading.Lock()
        
        def read_stdout():
            """Read stdout line by line"""
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.rstrip()
                    with stdout_lock:
                        stdout_lines.append(line)
                    logger.debug(f"[STDOUT] {line}")
                    # Log important lines to info level
                    if any(keyword in line.lower() for keyword in [
                        'error', 'failed', 'success', 'complete', 'step', 
                        'caption', 'synthesis', 'gemini', 'gpt', 'processing'
                    ]):
                        logger.info(f"[PROCESS] {line}")
            process.stdout.close()
        
        def read_stderr():
            """Read stderr line by line"""
            for line in iter(process.stderr.readline, ''):
                if line:
                    line = line.rstrip()
                    with stderr_lock:
                        stderr_lines.append(line)
                    logger.warning(f"[STDERR] {line}")
            process.stderr.close()
        
        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Wait for threads to finish reading
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        result["end_time"] = datetime.now().isoformat()
        result["duration_seconds"] = round(duration, 2)
        result["stdout"] = "\n".join(stdout_lines)
        result["stderr"] = "\n".join(stderr_lines)
        
        logger.info(f"Process completed with return code: {return_code}")
        logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
        if return_code == 0:
            result["status"] = "success"
            logger.info(f"✅ Successfully processed {pdf_path.name}")
        else:
            result["status"] = "error"
            result["error"] = result["stderr"] or f"Process exited with code {return_code}"
            logger.error(f"❌ Error processing {pdf_path.name} (exit code: {return_code})")
            if result["stderr"]:
                logger.error(f"STDERR: {result['stderr']}")
            if result["stdout"]:
                logger.debug(f"STDOUT (last 20 lines):\n" + "\n".join(stdout_lines[-20:]))
                
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        result["end_time"] = datetime.now().isoformat()
        result["duration_seconds"] = round(duration, 2)
        result["status"] = "exception"
        result["error"] = str(e)
        logger.exception(f"❌ Exception processing {pdf_path.name}: {e}")
    
    return result


def create_summary(
    results: List[Dict[str, Any]],
    summary_path: Path,
    timestamp: str
) -> None:
    """Create a summary file for analysis."""
    summary = {
        "timestamp": timestamp,
        "total_pdfs": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] != "success"),
        "results": results
    }
    
    # Write JSON summary
    summary_path.write_text(json.dumps(summary, indent=2))
    
    # Write human-readable summary
    human_summary_path = summary_path.parent / f"{summary_path.stem}_human_readable.txt"
    with human_summary_path.open("w") as f:
        f.write("="*80 + "\n")
        f.write(f"BATCH PROCESSING SUMMARY\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total PDFs processed: {summary['total_pdfs']}\n")
        f.write(f"Successful: {summary['successful']}\n")
        f.write(f"Failed: {summary['failed']}\n\n")
        
        f.write("-"*80 + "\n")
        f.write("DETAILED RESULTS:\n")
        f.write("-"*80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"{i}. {result['pdf_name']}\n")
            f.write(f"   Status: {result['status']}\n")
            f.write(f"   Output: {result['output_dir']}\n")
            if result['error']:
                f.write(f"   Error: {result['error'][:200]}...\n" if len(result['error']) > 200 else f"   Error: {result['error']}\n")
            f.write("\n")
        
        f.write("="*80 + "\n")
        f.write("OUTPUT STRUCTURE:\n")
        f.write("="*80 + "\n")
        f.write("timestamp/\n")
        f.write("  drawing_name/\n")
        f.write("    gemini/\n")
        f.write("      - legend_caption.txt\n")
        f.write("      - q1_top_left_caption.txt\n")
        f.write("      - q2_top_right_caption.txt\n")
        f.write("      - q3_bottom_left_caption.txt\n")
        f.write("      - q4_bottom_right_caption.txt\n")
        f.write("      - quadrant_synthesis.txt\n")
        f.write("      - final_full_drawing_caption.txt\n")
        f.write("      - results.json\n")
        f.write("    gpt/\n")
        f.write("      - [same files as gemini]\n")
        f.write("\n")
        f.write("For detailed analysis, compare outputs in gemini/ and gpt/ folders.\n")
    
    print(f"\n📊 Summary saved to:")
    print(f"   - {summary_path}")
    print(f"   - {human_summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch process all PDFs in Evals folder with captioning script"
    )
    parser.add_argument(
        "--evals-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory containing PDFs to process (default: Evals folder)"
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=None,
        help="Base output directory (default: Evals/outputs/timestamp)"
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["gemini", "gpt", "both"],
        default="both",
        help="Model to use (default: both)"
    )
    parser.add_argument(
        "--page",
        type=int,
        default=0,
        help="Page number to process (0-indexed, default: 0)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PDF conversion (default: 300)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually running"
    )
    
    args = parser.parse_args()
    
    # Create timestamp-based output directory early for logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output_base is None:
        output_base = args.evals_dir / "outputs" / timestamp
    else:
        output_base = args.output_base / timestamp
    
    output_base.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file = output_base / "batch_processing.log"
    logger = setup_logging(log_file)
    
    logger.info("="*80)
    logger.info("BATCH PDF PROCESSING STARTED")
    logger.info("="*80)
    logger.info(f"Timestamp: {timestamp}")
    logger.info(f"Evals directory: {args.evals_dir}")
    logger.info(f"Output directory: {output_base}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Page: {args.page}")
    logger.info(f"DPI: {args.dpi}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*80)
    
    # Find all PDFs (filtered for _new and _old only)
    logger.info(f"🔍 Searching for PDFs in: {args.evals_dir}")
    logger.info("   Filter: Only processing PDFs ending with '_new.pdf' or '_old.pdf'")
    logger.info("   Excluding: PDFs ending with '_overlay.pdf' or other suffixes")
    
    pdfs = find_pdfs(args.evals_dir)
    
    if not pdfs:
        logger.error(f"❌ No PDF files found in {args.evals_dir}")
        logger.error(f"   Searched recursively for *_new.pdf and *_old.pdf files")
        return 1
    
    logger.info(f"✅ Found {len(pdfs)} PDF file(s) to process:")
    for i, pdf in enumerate(pdfs, 1):
        logger.info(f"   {i}. {pdf.relative_to(args.evals_dir)}")
    
    if args.dry_run:
        logger.info("")
        logger.info("🔍 DRY RUN - Would process the above PDFs")
        logger.info("   (No actual processing performed)")
        return 0
    
    # Calculate estimated time (rough estimate: 5-10 minutes per PDF)
    estimated_minutes = len(pdfs) * 7
    logger.info(f"\n⏱️  Estimated processing time: ~{estimated_minutes} minutes ({estimated_minutes/60:.1f} hours)")
    logger.info(f"   Starting batch processing at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    batch_start_time = time.time()
    
    # Process each PDF
    results = []
    for i, pdf_path in enumerate(pdfs, 1):
        logger.info("")
        logger.info("#"*80)
        logger.info(f"Processing PDF {i}/{len(pdfs)}: {pdf_path.name}")
        logger.info(f"Progress: {i}/{len(pdfs)} ({i/len(pdfs)*100:.1f}%)")
        logger.info("#"*80)
        
        # Extract drawing name from PDF path
        drawing_name = pdf_path.stem
        
        # The captioning script will create: output_base/drawing_name/gemini/ and output_base/drawing_name/gpt/
        result = run_captioning(
            pdf_path=pdf_path,
            output_base=output_base,
            logger=logger,
            model=args.model,
            page=args.page,
            dpi=args.dpi
        )
        results.append(result)
        
        # Log progress summary
        successful_so_far = sum(1 for r in results if r["status"] == "success")
        failed_so_far = sum(1 for r in results if r["status"] != "success")
        elapsed_time = time.time() - batch_start_time
        avg_time_per_pdf = elapsed_time / i
        remaining_pdfs = len(pdfs) - i
        estimated_remaining = avg_time_per_pdf * remaining_pdfs
        
        logger.info(f"📊 Progress Summary:")
        logger.info(f"   Completed: {i}/{len(pdfs)}")
        logger.info(f"   Successful: {successful_so_far}")
        logger.info(f"   Failed: {failed_so_far}")
        logger.info(f"   Elapsed: {elapsed_time/60:.1f} minutes")
        logger.info(f"   Avg time per PDF: {avg_time_per_pdf/60:.1f} minutes")
        logger.info(f"   Estimated remaining: {estimated_remaining/60:.1f} minutes")
    
    batch_end_time = time.time()
    total_duration = batch_end_time - batch_start_time
    
    # Create summary
    logger.info("")
    logger.info("="*80)
    logger.info("Creating summary files...")
    logger.info("="*80)
    
    summary_path = output_base / "batch_summary.json"
    create_summary(results, summary_path, timestamp)
    
    # Final summary
    logger.info("")
    logger.info("="*80)
    logger.info("✅ BATCH PROCESSING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total PDFs processed: {len(pdfs)}")
    logger.info(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    logger.info(f"Failed: {sum(1 for r in results if r['status'] != 'success')}")
    logger.info(f"Total duration: {total_duration/60:.1f} minutes ({total_duration/3600:.2f} hours)")
    logger.info(f"Average time per PDF: {total_duration/len(pdfs)/60:.1f} minutes")
    logger.info(f"\n📁 All outputs saved to: {output_base}")
    logger.info(f"📊 Summary: {summary_path}")
    logger.info(f"📝 Detailed log: {log_file}")
    logger.info(f"\n💡 Next steps:")
    logger.info(f"   1. Review outputs in: {output_base}")
    logger.info(f"   2. Compare gemini/ and gpt/ outputs for each drawing")
    logger.info(f"   3. Analyze using the summary file")
    logger.info(f"   4. Check detailed log: {log_file}")
    
    # Print summary to console as well
    print(f"\n{'='*80}")
    print(f"✅ BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Processed: {len(pdfs)} PDF(s)")
    print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"Failed: {sum(1 for r in results if r['status'] != 'success')}")
    print(f"Total duration: {total_duration/60:.1f} minutes")
    print(f"\n📁 Outputs: {output_base}")
    print(f"📝 Log: {log_file}")
    
    return 0 if all(r["status"] == "success" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
