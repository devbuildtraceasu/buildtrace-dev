#!/usr/bin/env python3
"""
Chunked Page-by-Page Processing for BuildTrace
Handles both small (sync) and large (async) document processing
"""

import os
import tempfile
import logging
import time
from pathlib import Path
from typing import List, Dict, Tuple
import pdf2image
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # Remove PIL decompression bomb limit
import cv2
import numpy as np
from extract_drawing import extract_drawing_names
from drawing_comparison import compare_pdf_drawing_sets, create_drawing_overlay
from openai_change_analyzer import OpenAIChangeAnalyzer

# Optional psutil import for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("psutil not available - memory monitoring disabled")

logger = logging.getLogger(__name__)

class ChunkedProcessor:
    def __init__(self, max_sync_pages=10, dpi=300, use_ai_analysis=True, memory_limit_gb=10.0, session_id=None):
        self.max_sync_pages = max_sync_pages
        self.dpi = dpi  # Reduced from 300 to 150 for memory efficiency
        self.use_ai_analysis = use_ai_analysis
        self.memory_limit_gb = memory_limit_gb
        self.session_id = session_id
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def should_process_sync(self, old_pdf_path: str, new_pdf_path: str) -> bool:
        """Determine if files should be processed synchronously"""
        try:
            # Quick page count check without loading full PDFs
            old_pages = self._count_pdf_pages(old_pdf_path)
            new_pages = self._count_pdf_pages(new_pdf_path)
            max_pages = max(old_pages, new_pages)

            logger.info(f"Page counts: old={old_pages}, new={new_pages}, max={max_pages}")
            return max_pages <= self.max_sync_pages

        except Exception as e:
            logger.error(f"Error counting pages: {e}")
            # Default to async processing if unsure
            return False

    def _count_pdf_pages(self, pdf_path: str) -> int:
        """Quickly count PDF pages without loading images"""
        try:
            import PyMuPDF as fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except ImportError:
            # Fallback to pdf2image if PyMuPDF not available
            from pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(pdf_path)
            return info.get('Pages', 0)

    def process_sync(self, old_pdf_path: str, new_pdf_path: str, session_id: str = None) -> Dict:
        """Process small documents synchronously using complete AI pipeline"""
        logger.info("Starting synchronous AI-powered processing")
        start_time = time.time()

        results = {
            'success': False,
            'pages_processed': 0,
            'comparisons': [],
            'summary': {
                'total_time': 0,
                'processing_time': 0,
                'overlays_created': 0,
                'analyses_completed': 0
            },
            'processing_type': 'sync'
        }

        # Create a persistent directory for session results
        if session_id:
            results_dir = f"uploads/sessions/{session_id}/results"
            os.makedirs(results_dir, exist_ok=True)
        else:
            results_dir = None

        try:
            # Check memory limit - if we're close, use lightweight processing
            if not self.use_ai_analysis:
                logger.info("Using lightweight processing mode (AI analysis disabled)")
                return self._process_lightweight(old_pdf_path, new_pdf_path, session_id, results_dir)

            # Try AI pipeline with memory monitoring
            logger.info("Attempting AI-powered processing with memory management")

            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    # Extract drawing names from both PDFs for matching (memory optimized)
                    old_drawing_data = self._extract_drawing_names_efficient(old_pdf_path)
                    new_drawing_data = self._extract_drawing_names_efficient(new_pdf_path)

                    # Create mapping of drawing names to page data for proper matching
                    old_drawing_map = {d.get('drawing_name'): {'data': d, 'page_index': d.get('page_number', 1) - 1}
                                     for d in old_drawing_data if d.get('drawing_name')}
                    new_drawing_map = {d.get('drawing_name'): {'data': d, 'page_index': d.get('page_number', 1) - 1}
                                     for d in new_drawing_data if d.get('drawing_name')}

                    # Find matching drawing names between old and new
                    matching_drawings = set(old_drawing_map.keys()).intersection(set(new_drawing_map.keys()))

                    logger.info(f"Found {len(matching_drawings)} matching drawings: {list(matching_drawings)}")
                    logger.info(f"Old drawings: {list(old_drawing_map.keys())}")
                    logger.info(f"New drawings: {list(new_drawing_map.keys())}")

                    # Process page by page with AI analysis for memory efficiency
                    processed_results = []

                    # Convert PDFs to page images in small batches
                    old_pages = self._pdf_to_pages(old_pdf_path, temp_dir, 'old')
                    new_pages = self._pdf_to_pages(new_pdf_path, temp_dir, 'new')

                    # Decide on processing strategy based on environment and matching drawing count
                    use_parallel = (os.getenv('ENVIRONMENT') == 'production' and
                                  len(matching_drawings) > 3)  # Enable parallel for all multi-page documents in production

                    if use_parallel:
                        logger.info(f"Using parallel processing for {len(matching_drawings)} matching drawings")
                        processed_results = self._process_matching_drawings_parallel(
                            old_pages, new_pages, matching_drawings, old_drawing_map, new_drawing_map,
                            temp_dir, results_dir, session_id
                        )
                    else:
                        logger.info(f"Using sequential processing for {len(matching_drawings)} matching drawings")
                        for page_num, drawing_name in enumerate(sorted(matching_drawings), 1):
                            try:
                                # Check memory before processing each page
                                if not self._check_memory_usage():
                                    logger.error("Memory limit exceeded, stopping processing")
                                    break

                                # Get the correct page indices for this drawing name
                                old_page_index = old_drawing_map[drawing_name]['page_index']
                                new_page_index = new_drawing_map[drawing_name]['page_index']

                                # Ensure page indices are within bounds
                                if old_page_index >= len(old_pages) or new_page_index >= len(new_pages):
                                    logger.error(f"Page index out of bounds for {drawing_name}: old={old_page_index}, new={new_page_index}")
                                    continue

                                logger.info(f"Processing {drawing_name}: old page {old_page_index+1}, new page {new_page_index+1}")

                                # Process this single drawing pair with AI using correct page indices
                                page_result = self._process_single_drawing_with_ai(
                                    old_pages[old_page_index], new_pages[new_page_index],
                                    drawing_name, page_num, temp_dir, results_dir, session_id
                                )
                                processed_results.append(page_result)

                                # Force memory cleanup after each page
                                self._cleanup_page_memory()

                            except Exception as e:
                                logger.error(f"Error processing drawing {drawing_name}: {e}")
                                processed_results.append({
                                    'page_number': page_num,
                                    'drawing_name': drawing_name,
                                    'success': False,
                                    'error': str(e)
                                })

                    results['comparisons'] = processed_results
                    results['pages_processed'] = len(processed_results)
                    results['success'] = True

                    processing_time = time.time() - start_time
                    successful_analyses = len([r for r in processed_results if r.get('success', False) and r.get('ai_analysis_success', False)])

                    results['summary'] = {
                        'total_pages': len(processed_results),
                        'successful_pages': len([c for c in processed_results if c.get('success', False)]),
                        'processing_time': processing_time,
                        'total_time': processing_time,  # Add total_time for compatibility
                        'overlays_created': len([r for r in processed_results if r.get('success', False)]),
                        'analyses_completed': successful_analyses
                    }

                except MemoryError as e:
                    logger.warning(f"Memory limit reached, falling back to lightweight processing: {e}")
                    return self._process_lightweight(old_pdf_path, new_pdf_path, session_id, results_dir)

        except Exception as e:
            logger.error(f"Sync processing failed: {e}")
            results['error'] = str(e)

        # Save results to JSON file for frontend consumption
        self._save_results_to_json(results, session_id)
        return results

    def _process_lightweight(self, old_pdf_path: str, new_pdf_path: str, session_id: str = None, results_dir: str = None) -> Dict:
        """Lightweight processing mode without AI analysis for memory constraints"""
        logger.info("Starting lightweight processing mode")
        start_time = time.time()

        results = {
            'success': False,
            'pages_processed': 0,
            'comparisons': [],
            'summary': {
                'total_time': 0,
                'processing_time': 0,
                'overlays_created': 0,
                'analyses_completed': 0
            },
            'processing_type': 'lightweight'
        }

        try:
            # Extract drawing names from both PDFs (memory optimized)
            try:
                old_drawing_data = self._extract_drawing_names_efficient(old_pdf_path)
                new_drawing_data = self._extract_drawing_names_efficient(new_pdf_path)

                # Create mapping of drawing names to page data for proper matching
                old_drawing_map = {d.get('drawing_name'): {'data': d, 'page_index': d.get('page_number', 1) - 1}
                                 for d in old_drawing_data if d.get('drawing_name')}
                new_drawing_map = {d.get('drawing_name'): {'data': d, 'page_index': d.get('page_number', 1) - 1}
                                 for d in new_drawing_data if d.get('drawing_name')}

                # Find matching drawing names between old and new
                matching_drawings = set(old_drawing_map.keys()).intersection(set(new_drawing_map.keys()))

                logger.info(f"Lightweight: Found {len(matching_drawings)} matching drawings: {list(matching_drawings)}")
                logger.info(f"Lightweight: Old drawings: {list(old_drawing_map.keys())}")
                logger.info(f"Lightweight: New drawings: {list(new_drawing_map.keys())}")
            except Exception as e:
                logger.warning(f"Failed to extract drawing names: {e}, using page numbers")
                old_drawing_map = {}
                new_drawing_map = {}
                matching_drawings = set()

            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDFs to page images
                old_pages = self._pdf_to_pages(old_pdf_path, temp_dir, 'old')
                new_pages = self._pdf_to_pages(new_pdf_path, temp_dir, 'new')

                # Process matching drawings with proper name-based pairing
                if matching_drawings:
                    for page_num, drawing_name in enumerate(sorted(matching_drawings), 1):
                        try:
                            # Check memory before processing each page
                            if not self._check_memory_usage():
                                logger.error("Memory limit exceeded in lightweight processing, stopping")
                                break

                            # Get the correct page indices for this drawing name
                            old_page_index = old_drawing_map[drawing_name]['page_index']
                            new_page_index = new_drawing_map[drawing_name]['page_index']

                            # Ensure page indices are within bounds
                            if old_page_index >= len(old_pages) or new_page_index >= len(new_pages):
                                logger.error(f"Page index out of bounds for {drawing_name}: old={old_page_index}, new={new_page_index}")
                                continue

                            logger.info(f"Lightweight: Processing {drawing_name}: old page {old_page_index+1}, new page {new_page_index+1}")

                            # Use the full AI-enabled processing method even in lightweight mode
                            page_result = self._process_single_drawing_with_ai(
                                old_pages[old_page_index], new_pages[new_page_index], drawing_name, page_num, temp_dir, results_dir, session_id
                            )
                            results['comparisons'].append(page_result)
                            results['pages_processed'] = page_num

                            # Memory cleanup after each page
                            self._cleanup_page_memory()

                        except Exception as e:
                            logger.error(f"Error processing drawing {drawing_name}: {e}")
                            results['comparisons'].append({
                                'page_number': page_num,
                                'drawing_name': drawing_name,
                                'success': False,
                                'error': str(e)
                            })

                # Process "added drawings" - new drawings that don't have matches in old set
                added_drawings = set(new_drawing_map.keys()) - set(old_drawing_map.keys())
                if added_drawings:
                    logger.info(f"Found {len(added_drawings)} added drawings: {list(added_drawings)}")
                    for drawing_name in sorted(added_drawings):
                        try:
                            # Get the page index for this new drawing
                            new_page_index = new_drawing_map[drawing_name]['page_index']

                            if new_page_index >= len(new_pages):
                                logger.error(f"Page index out of bounds for added drawing {drawing_name}: {new_page_index}")
                                continue

                            logger.info(f"Processing added drawing: {drawing_name} (new page {new_page_index+1})")

                            # For added drawings, we just save the new drawing info without overlay
                            results['comparisons'].append({
                                'page_number': len(results['comparisons']) + 1,
                                'drawing_name': drawing_name,
                                'success': True,
                                'type': 'added',
                                'new_image_path': new_pages[new_page_index],
                                'changes_detected': True,
                                'is_new_drawing': True
                            })
                        except Exception as e:
                            logger.error(f"Error processing added drawing {drawing_name}: {e}")

                # If no matching drawings found at all, fallback to index-based processing
                if not matching_drawings and not added_drawings:
                    logger.warning("No drawing names found, falling back to index-based processing")
                    min_pages = min(len(old_pages), len(new_pages))
                    for i in range(min_pages):
                        try:
                            if not self._check_memory_usage():
                                logger.error("Memory limit exceeded in lightweight processing, stopping")
                                break

                            drawing_name = f"Page_{i+1:03d}"
                            page_result = self._process_page_pair_simple(
                                old_pages[i], new_pages[i], i + 1, temp_dir, results_dir, drawing_name
                            )
                            results['comparisons'].append(page_result)
                            results['pages_processed'] = i + 1
                            self._cleanup_page_memory()

                        except Exception as e:
                            logger.error(f"Error processing page {i+1}: {e}")
                            results['comparisons'].append({
                                'page_number': i + 1,
                                'success': False,
                                'error': str(e)
                            })

                results['success'] = True
                processing_time = time.time() - start_time

                # Calculate statistics correctly
                successful_comparisons = [c for c in results['comparisons'] if c.get('success', False)]
                overlays_created = len([c for c in successful_comparisons if c.get('type') != 'added'])  # Don't count added drawings as overlays
                added_drawings_count = len([c for c in successful_comparisons if c.get('type') == 'added'])
                analyses_completed = len([c for c in successful_comparisons if c.get('ai_analysis_success', False)])

                results['summary'] = {
                    'total_pages': len(matching_drawings) + added_drawings_count,
                    'successful_pages': len(successful_comparisons),
                    'processing_time': processing_time,
                    'total_time': processing_time,  # Add total_time for compatibility
                    'overlays_created': overlays_created,
                    'analyses_completed': analyses_completed,
                    'added_drawings': added_drawings_count
                }

        except Exception as e:
            logger.error(f"Lightweight processing failed: {e}")
            results['error'] = str(e)

        # Save results to JSON file for frontend consumption
        self._save_results_to_json(results, session_id)
        return results

    def _process_single_drawing_with_ai(self, old_page_path: str, new_page_path: str,
                                      drawing_name: str, page_number: int, temp_dir: str,
                                      results_dir: str = None, session_id: str = None) -> Dict:
        """Process a single drawing with AI analysis for memory efficiency"""
        try:
            # First create overlay with SIFT feature matching
            overlay_path, alignment_score = self._create_simple_overlay(old_page_path, new_page_path, drawing_name, temp_dir)

            if not overlay_path:
                return {
                    'page_number': page_number,
                    'drawing_name': drawing_name,
                    'success': False,
                    'error': 'Failed to create overlay'
                }

            # Try to run AI analysis on this single overlay
            ai_analysis_success = False
            analysis_result = None

            try:
                if self.use_ai_analysis:
                    logger.info(f"Running AI analysis for {drawing_name}")
                    analysis_result = self._run_ai_analysis(overlay_path, old_page_path, new_page_path, drawing_name)
                    ai_analysis_success = analysis_result.success if analysis_result else False

                    if ai_analysis_success:
                        logger.info(f"AI analysis completed successfully for {drawing_name}")
                    else:
                        logger.warning(f"AI analysis failed for {drawing_name}")

            except Exception as e:
                logger.warning(f"AI analysis setup failed for {drawing_name}: {e}")

            # Upload images to cloud storage and save to database
            final_overlay_path = overlay_path
            final_old_path = old_page_path
            final_new_path = new_page_path

            if results_dir and session_id:
                try:
                    page_dir = os.path.join(results_dir, drawing_name)
                    os.makedirs(page_dir, exist_ok=True)

                    # Upload to cloud storage
                    final_overlay_path = self._copy_and_upload_image(
                        overlay_path, page_dir, f"{drawing_name}_overlay.png", session_id, drawing_name
                    )
                    final_old_path = self._copy_and_upload_image(
                        old_page_path, page_dir, f"{drawing_name}_old.png", session_id, drawing_name
                    )
                    final_new_path = self._copy_and_upload_image(
                        new_page_path, page_dir, f"{drawing_name}_new.png", session_id, drawing_name
                    )

                    # Save comparison to database
                    comparison_id = self._save_comparison_to_db(
                        session_id=session_id,
                        drawing_name=drawing_name,
                        old_image_path=final_old_path,
                        new_image_path=final_new_path,
                        overlay_path=final_overlay_path,
                        alignment_score=alignment_score,
                        changes_detected=True
                    )
                    logger.info(f"Saved comparison {comparison_id} to database")

                    # Save AI analysis to database if available
                    if analysis_result and comparison_id:
                        analysis_id = self._save_ai_analysis_to_db(comparison_id, analysis_result)
                        logger.info(f"Saved AI analysis {analysis_id} to database")

                        # Also save AI analysis as JSON file for chatbot service compatibility
                        try:
                            import json
                            json_filename = f"change_analysis_{drawing_name}.json"
                            json_path = os.path.join(page_dir, json_filename)

                            # Prepare JSON data matching the expected format
                            json_data = {
                                "drawing_name": drawing_name,
                                "overlay_folder": page_dir,
                                "analysis_timestamp": analysis_result.analysis_summary[:100] + "..." if len(analysis_result.analysis_summary) > 100 else analysis_result.analysis_summary,
                                "success": analysis_result.success,
                                "changes_found": analysis_result.changes_found,
                                "critical_change": analysis_result.critical_change,
                                "analysis_summary": analysis_result.analysis_summary,
                                "recommendations": analysis_result.recommendations if hasattr(analysis_result, 'recommendations') else [],
                                "error_message": analysis_result.error_message if hasattr(analysis_result, 'error_message') else None
                            }

                            # Add optional fields if they exist
                            if hasattr(analysis_result, 'confidence_score'):
                                json_data["confidence_score"] = analysis_result.confidence_score
                            if hasattr(analysis_result, 'key_observations'):
                                json_data["key_observations"] = analysis_result.key_observations
                            if hasattr(analysis_result, 'change_type'):
                                json_data["change_type"] = analysis_result.change_type
                            if hasattr(analysis_result, 'change_impact'):
                                json_data["change_impact"] = analysis_result.change_impact
                            if hasattr(analysis_result, 'analysis_date'):
                                json_data["analysis_date"] = analysis_result.analysis_date.isoformat()

                            # Save JSON locally
                            with open(json_path, 'w') as f:
                                json.dump(json_data, f, indent=2)

                            # Upload JSON to cloud storage
                            from gcp.storage import storage_service
                            if hasattr(storage_service, 'bucket') and storage_service.bucket:
                                cloud_json_path = f"sessions/{session_id}/results/{drawing_name}/{json_filename}"
                                gcs_json_url = storage_service.upload_from_filename(json_path, cloud_json_path)
                                logger.info(f"Uploaded AI analysis JSON to {gcs_json_url}")

                        except Exception as json_e:
                            logger.warning(f"Could not save/upload AI analysis JSON for {drawing_name}: {json_e}")

                except Exception as e:
                    logger.warning(f"Could not save comparison for {drawing_name}: {e}")

            # Build result entry
            result_entry = {
                'page_number': page_number,
                'drawing_name': drawing_name,
                'success': True,
                'ai_analysis_success': ai_analysis_success,
                'overlay_path': final_overlay_path,
                'old_image_path': final_old_path,
                'new_image_path': final_new_path,
                'changes_detected': True,
                'ai_analysis': {
                    'success': ai_analysis_success,
                    'changes_found': analysis_result.changes_found if analysis_result else [],
                    'critical_change': analysis_result.critical_change if analysis_result else None,
                    'summary': analysis_result.analysis_summary if analysis_result else None,
                    'recommendations': analysis_result.recommendations if analysis_result else []
                }
            }

            # Add AI analysis results if available
            if analysis_result and ai_analysis_success:
                result_entry.update({
                    'differences_found': len(analysis_result.changes_found) if analysis_result.changes_found else 1,
                    'analysis': analysis_result.analysis_summary or f"AI analysis completed for {drawing_name}",
                    'critical_change': analysis_result.critical_change,
                    'changes_found': analysis_result.changes_found,
                    'recommendations': analysis_result.recommendations,
                })
            else:
                result_entry.update({
                    'differences_found': 1,
                    'analysis': f"Visual comparison completed for {drawing_name}"
                })

            return result_entry

        except Exception as e:
            logger.error(f"Error processing single drawing {drawing_name}: {e}")
            return {
                'page_number': page_number,
                'drawing_name': drawing_name,
                'success': False,
                'error': str(e)
            }

    def _create_simple_overlay(self, old_page_path: str, new_page_path: str,
                             drawing_name: str, temp_dir: str) -> Tuple[str, float]:
        """Create overlay using SIFT feature matching and return alignment score"""
        try:
            # Use the proper create_drawing_overlay function from drawing_comparison
            overlay_path = create_drawing_overlay(
                old_image_path=old_page_path,
                new_image_path=new_page_path,
                output_folder=temp_dir,
                filename=drawing_name,
                debug=False
            )

            # Try to get alignment score from the alignment process
            alignment_score = self._calculate_alignment_score(old_page_path, new_page_path)

            return overlay_path, alignment_score

        except Exception as e:
            logger.error(f"Error creating overlay for {drawing_name}: {e}")
            return None, 0.0

    def _calculate_alignment_score(self, old_image_path: str, new_image_path: str) -> float:
        """Calculate alignment score using SIFT feature matching"""
        try:
            from align_drawings import AlignDrawings
            from image_utils import load_image, image_to_grayscale
            import cv2

            # Load images
            old_img = load_image(old_image_path)
            new_img = load_image(new_image_path)

            if old_img is None or new_img is None:
                return 0.0

            # Convert to grayscale
            old_gray = image_to_grayscale(old_img)
            new_gray = image_to_grayscale(new_img)

            # Initialize aligner with environment-appropriate settings
            if os.getenv('ENVIRONMENT') == 'production':
                # High-compute settings for production
                config = AlignDrawings.Config(
                    n_features=20000,  # More features for better matching
                    ransac_reproj_threshold=10.0,  # Tighter threshold
                    max_iters=10000,   # More iterations
                    confidence=0.99    # Higher confidence
                )
                aligner = AlignDrawings(config=config, debug=False)
            else:
                # Standard settings for development
                aligner = AlignDrawings(debug=False)

            # Extract SIFT features
            kp1, desc1 = aligner.extract_features_sift(old_gray)
            kp2, desc2 = aligner.extract_features_sift(new_gray)

            if desc1 is None or desc2 is None or len(desc1) == 0 or len(desc2) == 0:
                return 0.0

            # Match features
            matches = aligner.match_features_ratio_test(desc1, desc2)

            if len(matches) == 0:
                return 0.0

            # Calculate alignment score based on number of good matches
            # More matches = better alignment
            total_features = min(len(kp1), len(kp2))
            if total_features == 0:
                return 0.0

            score = min(1.0, len(matches) / (total_features * 0.1))  # Normalize to 0-1

            logger.info(f"Alignment score: {score:.3f} ({len(matches)} matches out of {total_features} features)")
            return score

        except Exception as e:
            logger.warning(f"Failed to calculate alignment score: {e}")
            return 0.5  # Default moderate score

    def _process_page_pair_simple(self, old_page_path: str, new_page_path: str,
                                page_number: int, temp_dir: str, results_dir: str = None,
                                drawing_name: str = None) -> Dict:
        """Process a single page comparison with simple analysis"""
        try:
            # Use provided drawing name or fallback to Page_XXX
            if not drawing_name:
                drawing_name = f"Page_{page_number:03d}"

            # Create overlay with SIFT feature matching
            overlay_path, alignment_score = self._create_simple_overlay(old_page_path, new_page_path, drawing_name, temp_dir)

            if not overlay_path:
                return {
                    'page_number': page_number,
                    'drawing_name': drawing_name,
                    'success': False,
                    'error': 'Failed to create overlay'
                }

            # Upload to cloud storage and save to database if session_id is provided
            final_overlay_path = overlay_path
            final_old_path = old_page_path
            final_new_path = new_page_path

            if results_dir:
                try:
                    import shutil
                    page_dir = os.path.join(results_dir, drawing_name)
                    os.makedirs(page_dir, exist_ok=True)

                    if hasattr(self, 'session_id') and self.session_id:
                        # Upload to cloud storage with database integration
                        final_overlay_path = self._copy_and_upload_image(
                            overlay_path, page_dir, f"{drawing_name}_overlay.png", self.session_id, drawing_name
                        )
                        final_old_path = self._copy_and_upload_image(
                            old_page_path, page_dir, f"{drawing_name}_old.png", self.session_id, drawing_name
                        )
                        final_new_path = self._copy_and_upload_image(
                            new_page_path, page_dir, f"{drawing_name}_new.png", self.session_id, drawing_name
                        )

                        # Save comparison to database
                        comparison_id = self._save_comparison_to_db(
                            session_id=self.session_id,
                            drawing_name=drawing_name,
                            old_image_path=final_old_path,
                            new_image_path=final_new_path,
                            overlay_path=final_overlay_path,
                            alignment_score=alignment_score,
                            changes_detected=True
                        )
                        logger.info(f"Saved simple comparison {comparison_id} to database")
                    else:
                        # Fallback to local file copying
                        final_overlay_path = os.path.join(page_dir, f"{drawing_name}_overlay.png")
                        final_old_path = os.path.join(page_dir, f"{drawing_name}_old.png")
                        final_new_path = os.path.join(page_dir, f"{drawing_name}_new.png")

                        shutil.copy2(overlay_path, final_overlay_path)
                        shutil.copy2(old_page_path, final_old_path)
                        shutil.copy2(new_page_path, final_new_path)

                except Exception as e:
                    logger.warning(f"Could not save images: {e}")

            return {
                'page_number': page_number,
                'drawing_name': drawing_name,
                'success': True,
                'differences_found': 1,
                'overlay_path': final_overlay_path,
                'old_image_path': final_old_path,
                'new_image_path': final_new_path,
                'changes_detected': True,
                'analysis': f"Basic comparison completed for {drawing_name}"
            }

        except Exception as e:
            logger.error(f"Error processing page {page_number}: {e}")
            return {
                'page_number': page_number,
                'success': False,
                'error': str(e)
            }



    def _convert_pipeline_results(self, comparison_results: Dict, analysis_results: List,
                                results_dir: str = None, session_id: str = None) -> List[Dict]:
        """Convert complete pipeline results to app-compatible format"""
        processed_results = []

        # Get overlay folder info
        new_pdf_path = comparison_results.get('new_pdf_path', '')
        new_pdf_name = Path(new_pdf_path).stem if new_pdf_path else 'unknown'
        base_overlay_dir = f"{new_pdf_name}_overlays"

        # Create a mapping of analysis results by drawing name
        analysis_map = {}
        if analysis_results:
            for result in analysis_results:
                analysis_map[result.drawing_name] = result

        # Process each successful overlay
        overlay_folders = comparison_results.get('overlay_folders', [])
        for i, overlay_folder in enumerate(overlay_folders):
            try:
                # Extract drawing name from folder path
                drawing_name = Path(overlay_folder).name
                logger.info(f"Processing overlay result for: {drawing_name}")

                # Find overlay image
                overlay_image_path = None
                old_image_path = None
                new_image_path = None

                overlay_dir_path = Path(overlay_folder)
                if overlay_dir_path.exists():
                    # Look for overlay image
                    for ext in ['png', 'jpg', 'jpeg']:
                        overlay_candidate = overlay_dir_path / f"{drawing_name}_overlay.{ext}"
                        if overlay_candidate.exists():
                            overlay_image_path = str(overlay_candidate)
                            break

                    # Look for old and new images
                    for ext in ['png', 'jpg', 'jpeg']:
                        old_candidate = overlay_dir_path / f"{drawing_name}_old.{ext}"
                        new_candidate = overlay_dir_path / f"{drawing_name}_new.{ext}"
                        if old_candidate.exists():
                            old_image_path = str(old_candidate)
                        if new_candidate.exists():
                            new_image_path = str(new_candidate)

                # Get AI analysis results for this drawing
                analysis_result = analysis_map.get(drawing_name)

                # Copy images to session results directory if available
                final_overlay_path = overlay_image_path
                final_old_path = old_image_path
                final_new_path = new_image_path

                if results_dir and session_id:
                    try:
                        from gcp.storage import storage_service

                        # Create subdirectory for this drawing
                        page_dir = os.path.join(results_dir, drawing_name)
                        os.makedirs(page_dir, exist_ok=True)

                        # Copy and potentially upload to cloud storage
                        if overlay_image_path and os.path.exists(overlay_image_path):
                            final_overlay_path = self._copy_and_upload_image(
                                overlay_image_path, page_dir, f"{drawing_name}_overlay.png",
                                session_id, drawing_name
                            )

                        if old_image_path and os.path.exists(old_image_path):
                            final_old_path = self._copy_and_upload_image(
                                old_image_path, page_dir, f"{drawing_name}_old.png",
                                session_id, drawing_name
                            )

                        if new_image_path and os.path.exists(new_image_path):
                            final_new_path = self._copy_and_upload_image(
                                new_image_path, page_dir, f"{drawing_name}_new.png",
                                session_id, drawing_name
                            )

                    except Exception as e:
                        logger.warning(f"Could not copy/upload images for {drawing_name}: {e}")

                # Create result entry
                result_entry = {
                    'page_number': i + 1,
                    'drawing_name': drawing_name,
                    'success': overlay_image_path is not None,
                    'overlay_path': final_overlay_path,
                    'old_image_path': final_old_path,
                    'new_image_path': final_new_path,
                    'changes_detected': True,  # Assume changes if overlay was created
                }

                # Add AI analysis results if available
                if analysis_result and analysis_result.success:
                    result_entry.update({
                        'differences_found': len(analysis_result.changes_found) if analysis_result.changes_found else 1,
                        'analysis': analysis_result.analysis_summary or f"AI analysis completed for {drawing_name}",
                        'critical_change': analysis_result.critical_change,
                        'changes_found': analysis_result.changes_found,
                        'recommendations': analysis_result.recommendations,
                        'cost_estimate': getattr(analysis_result, 'cost_estimate', None),
                        'timeline_impact': getattr(analysis_result, 'timeline_impact', None)
                    })
                else:
                    result_entry.update({
                        'differences_found': 1,
                        'analysis': f"Overlay created for {drawing_name} - AI analysis pending or failed"
                    })

                processed_results.append(result_entry)

            except Exception as e:
                logger.error(f"Error processing overlay result {i}: {e}")
                processed_results.append({
                    'page_number': i + 1,
                    'success': False,
                    'error': str(e)
                })

        return processed_results

    def _copy_and_upload_image(self, source_path: str, local_dir: str, filename: str,
                             session_id: str, drawing_name: str) -> str:
        """Copy image locally and upload to cloud storage with proper GCS path"""
        import shutil

        # Copy to local directory first
        local_path = os.path.join(local_dir, filename)
        shutil.copy2(source_path, local_path)

        # Upload to cloud storage
        try:
            from gcp.storage import storage_service
            if hasattr(storage_service, 'bucket') and storage_service.bucket:
                # Use proper GCS path format
                cloud_path = f"sessions/{session_id}/results/{drawing_name}/{filename}"
                gcs_url = storage_service.upload_from_filename(local_path, cloud_path)
                logger.info(f"Uploaded {filename} to {gcs_url}")
                return gcs_url
            else:
                # Fallback to local path for development
                logger.warning(f"Cloud storage not available, using local path: {local_path}")
                return local_path
        except Exception as e:
            logger.warning(f"Cloud upload failed for {filename}: {e}, using local path")
            return local_path

    def _pdf_to_pages(self, pdf_path: str, temp_dir: str, prefix: str) -> List[str]:
        """Convert PDF to individual page images with memory management"""
        try:
            # Convert PDF to images one at a time for maximum memory efficiency
            page_paths = []
            batch_size = 1  # Process only 1 page at a time for maximum memory efficiency

            total_pages = self._count_pdf_pages(pdf_path)
            logger.info(f"Converting {total_pages} pages from {prefix} PDF at {self.dpi} DPI")

            for start_page in range(1, total_pages + 1, batch_size):
                end_page = min(start_page + batch_size - 1, total_pages)

                try:
                    # Convert single page with optimized threading
                    thread_count = 1 if os.getenv('ENVIRONMENT') != 'production' else min(4, os.cpu_count() or 1)

                    images = pdf2image.convert_from_path(
                        pdf_path,
                        dpi=self.dpi,
                        first_page=start_page,
                        last_page=end_page,
                        thread_count=thread_count,
                        fmt='PNG',
                        size=(None, 6000 if os.getenv('ENVIRONMENT') == 'production' else 4500)
                    )

                    # Save each page and clear from memory immediately
                    for i, image in enumerate(images):
                        page_num = start_page + i
                        page_path = os.path.join(temp_dir, f"{prefix}_page_{page_num:03d}.png")

                        # Resize if still too large
                        if image.width > 6000 or image.height > 6000:
                            ratio = min(6000/image.width, 6000/image.height)
                            new_size = (int(image.width * ratio), int(image.height * ratio))
                            image = image.resize(new_size, Image.Resampling.LANCZOS)

                        image.save(page_path, "PNG", optimize=True, compress_level=6)
                        page_paths.append(page_path)

                        # Clear from memory immediately
                        image.close()

                    # Clear batch from memory
                    del images

                except Exception as e:
                    logger.error(f"Error converting page {start_page}: {e}")
                    raise

                # Force garbage collection after each page
                import gc
                gc.collect()

            return page_paths

        except Exception as e:
            logger.error(f"Error converting PDF {prefix}: {e}")
            raise

    def _cleanup_page_memory(self):
        """Force memory cleanup after processing each page"""
        import gc
        gc.collect()

    def _process_matching_drawings_parallel(self, old_pages, new_pages, matching_drawings,
                                          old_drawing_map, new_drawing_map, temp_dir, results_dir, session_id):
        """Process matching drawings in parallel (stub for now - falls back to sequential)"""
        logger.info("Parallel processing not yet implemented, falling back to sequential")

        processed_results = []
        for page_num, drawing_name in enumerate(sorted(matching_drawings), 1):
            try:
                # Get the correct page indices for this drawing name
                old_page_index = old_drawing_map[drawing_name]['page_index']
                new_page_index = new_drawing_map[drawing_name]['page_index']

                # Ensure page indices are within bounds
                if old_page_index >= len(old_pages) or new_page_index >= len(new_pages):
                    logger.error(f"Page index out of bounds for {drawing_name}: old={old_page_index}, new={new_page_index}")
                    continue

                logger.info(f"Parallel stub: Processing {drawing_name}: old page {old_page_index+1}, new page {new_page_index+1}")

                # Process this single drawing pair with AI using correct page indices
                page_result = self._process_single_drawing_with_ai(
                    old_pages[old_page_index], new_pages[new_page_index],
                    drawing_name, page_num, temp_dir, results_dir, session_id
                )
                processed_results.append(page_result)

                # Force memory cleanup after each page
                self._cleanup_page_memory()

            except Exception as e:
                logger.error(f"Error processing drawing {drawing_name}: {e}")
                processed_results.append({
                    'page_number': page_num,
                    'drawing_name': drawing_name,
                    'success': False,
                    'error': str(e)
                })

        return processed_results

    def _check_memory_usage(self) -> bool:
        """Check if memory usage is within limits"""
        if not PSUTIL_AVAILABLE or not self.process:
            # If psutil is not available, assume memory is okay
            return True

        try:
            memory_info = self.process.memory_info()
            memory_gb = memory_info.rss / (1024 ** 3)  # Convert bytes to GB

            logger.info(f"Current memory usage: {memory_gb:.2f} GB")

            if memory_gb > self.memory_limit_gb:
                logger.warning(f"Memory usage ({memory_gb:.2f} GB) exceeds limit ({self.memory_limit_gb} GB)")
                return False
            return True
        except Exception as e:
            logger.warning(f"Could not check memory usage: {e}")
            return True

    def _extract_drawing_names_efficient(self, pdf_path: str) -> List[Dict]:
        """Memory-efficient drawing name extraction with font size and position scoring"""
        try:
            import fitz  # PyMuPDF
            import re

            # Regex for drawing names (supports decimal numbers like A2.1, A1.1)
            DRAWING_RE = re.compile(r"\b([A-Z])[-\s]?(\d{1,4}(?:\.\d{1,2})?)(?:-([A-Z0-9]{1,8}))?\b")

            def normalize_dwg(text, token_match):
                """Preserve original format (A2.1 stays A2.1, A-101 stays A-101)"""
                letter = token_match.group(1)
                number = token_match.group(2)
                suffix = token_match.group(3)
                
                # Find the original separator between letter and number
                start_pos = token_match.start()
                letter_end = token_match.start(2)
                separator = text[start_pos + 1:letter_end]
                
                # Build result preserving original separator
                result = letter + separator + number
                if suffix:
                    result += '-' + suffix
                
                return result

            def extract_with_font_size(page):
                """Extract drawing names using position and font size scoring"""
                words = page.get_text("words")
                
                # Get font size information
                font_sizes = {}
                try:
                    blocks = page.get_text("dict")["blocks"]
                    for block in blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    text = span["text"]
                                    size = span["size"]
                                    bbox = span["bbox"]
                                    cx = 0.5 * (bbox[0] + bbox[2])
                                    cy = 0.5 * (bbox[1] + bbox[3])
                                    key = (round(cx), round(cy), text.strip())
                                    font_sizes[key] = size
                except:
                    pass
                
                # Find candidates with font sizes
                candidates = []
                for (x0, y0, x1, y1, text, *_rest) in words:
                    for m in DRAWING_RE.finditer(text):
                        cand = normalize_dwg(text, m)
                        cx = 0.5 * (x0 + x1)
                        cy = 0.5 * (y0 + y1)
                        key = (round(cx), round(cy), text.strip())
                        font_size = font_sizes.get(key, 0)
                        candidates.append((cand, cx, cy, font_size))
                
                if not candidates:
                    return None
                
                # Score by font size (3x weight) + position
                w = page.rect.width
                h = page.rect.height
                max_font = max([c[3] for c in candidates])
                if max_font == 0:
                    max_font = 1
                
                best = None
                best_score = -1e9
                for cand, cx, cy, font_size in candidates:
                    norm_font = font_size / max_font
                    pos_score = (cx / w) + (cy / h)
                    score = (norm_font * 3.0) + pos_score
                    if score > best_score:
                        best_score = score
                        best = cand
                
                return best

            doc = fitz.open(pdf_path)
            results = []

            for page_num, page in enumerate(doc):
                try:
                    # Try position + font size extraction
                    drawing_name = extract_with_font_size(page)

                    if drawing_name:
                        results.append({
                            'page_number': page_num + 1,
                            'drawing_name': drawing_name
                        })
                        logger.info(f"Found drawing name via text extraction: {drawing_name}")
                    else:
                        # Fallback to OCR only if text extraction fails, but with smaller crop
                        try:
                            # Render only bottom-right corner at lower resolution
                            zoom = 1.0  # Reduced from 2.0
                            mat = fitz.Matrix(zoom, zoom)

                            # Get smaller crop area
                            rect = page.rect
                            crop_rect = fitz.Rect(
                                rect.width * 0.75,   # Start at 75% width
                                rect.height * 0.85,  # Start at 85% height
                                rect.width,          # End at 100% width
                                rect.height          # End at 100% height
                            )

                            pix = page.get_pixmap(matrix=mat, clip=crop_rect, annots=False)

                            # Convert to PIL with size limit
                            import io
                            from PIL import Image
                            img = Image.open(io.BytesIO(pix.tobytes("png")))

                            # Further resize if still large
                            if img.width > 400 or img.height > 400:
                                img.thumbnail((400, 400), Image.Resampling.LANCZOS)

                            # OCR on small region
                            import pytesseract
                            ocr_text = pytesseract.image_to_string(img, config="--psm 6")
                            match = DRAWING_RE.search(ocr_text)

                            if match:
                                drawing_name = normalize_dwg(ocr_text, match)
                                results.append({
                                    'page_number': page_num + 1,
                                    'drawing_name': drawing_name
                                })
                                logger.info(f"Found drawing name via OCR: {drawing_name}")
                            else:
                                # Use page number as fallback
                                drawing_name = f"Page_{page_num + 1:03d}"
                                results.append({
                                    'page_number': page_num + 1,
                                    'drawing_name': drawing_name
                                })
                                logger.info(f"Using fallback name: {drawing_name}")

                            # Clean up PIL image
                            img.close()
                            del img, pix

                        except Exception as ocr_e:
                            logger.warning(f"OCR failed for page {page_num + 1}: {ocr_e}")
                            # Use page number as fallback
                            drawing_name = f"Page_{page_num + 1:03d}"
                            results.append({
                                'page_number': page_num + 1,
                                'drawing_name': drawing_name
                            })

                    # Memory cleanup after each page
                    import gc
                    gc.collect()

                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {e}")
                    # Add fallback entry
                    results.append({
                        'page_number': page_num + 1,
                        'drawing_name': f"Page_{page_num + 1:03d}"
                    })

            doc.close()
            return results

        except Exception as e:
            logger.error(f"Error extracting drawing names from {pdf_path}: {e}")
            return []

    def _save_comparison_to_db(self, session_id: str, drawing_name: str,
                             old_image_path: str, new_image_path: str, overlay_path: str,
                             alignment_score: float = 0.0, changes_detected: bool = True) -> str:
        """Save comparison results to PostgreSQL database"""
        try:
            from gcp.database import get_db_session
            from gcp.database.models import Comparison, Drawing
            import uuid

            with get_db_session() as db:
                # Find or create drawing records
                old_drawing = db.query(Drawing).filter(
                    Drawing.session_id == session_id,
                    Drawing.drawing_type == 'old',
                    Drawing.drawing_name == drawing_name
                ).first()

                new_drawing = db.query(Drawing).filter(
                    Drawing.session_id == session_id,
                    Drawing.drawing_type == 'new',
                    Drawing.drawing_name == drawing_name
                ).first()

                if not old_drawing:
                    old_drawing = Drawing(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        drawing_type='old',
                        filename=f"{drawing_name}_old.png",
                        original_filename=f"{drawing_name}_old.png",
                        storage_path=old_image_path,
                        drawing_name=drawing_name,
                        page_number=1
                    )
                    db.add(old_drawing)
                    db.flush()  # Get the ID

                if not new_drawing:
                    new_drawing = Drawing(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        drawing_type='new',
                        filename=f"{drawing_name}_new.png",
                        original_filename=f"{drawing_name}_new.png",
                        storage_path=new_image_path,
                        drawing_name=drawing_name,
                        page_number=1
                    )
                    db.add(new_drawing)
                    db.flush()  # Get the ID

                # Create or update comparison record (upsert logic to prevent duplicates)
                existing_comparison = db.query(Comparison).filter_by(
                    session_id=session_id, drawing_name=drawing_name
                ).first()

                if existing_comparison:
                    # Update existing comparison
                    existing_comparison.old_drawing_id = old_drawing.id
                    existing_comparison.new_drawing_id = new_drawing.id
                    existing_comparison.overlay_path = overlay_path
                    existing_comparison.old_image_path = old_image_path
                    existing_comparison.new_image_path = new_image_path
                    existing_comparison.alignment_score = alignment_score
                    existing_comparison.changes_detected = changes_detected
                    comparison = existing_comparison
                    logger.info(f"Updated existing comparison in database: {drawing_name}")
                else:
                    # Create new comparison
                    comparison = Comparison(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        old_drawing_id=old_drawing.id,
                        new_drawing_id=new_drawing.id,
                        drawing_name=drawing_name,
                        overlay_path=overlay_path,
                        old_image_path=old_image_path,
                        new_image_path=new_image_path,
                        alignment_score=alignment_score,
                        changes_detected=changes_detected
                    )
                    db.add(comparison)
                    logger.info(f"Created new comparison in database: {drawing_name}")

                db.commit()

                logger.info(f"Saved comparison to database: {drawing_name}")
                return comparison.id

        except Exception as e:
            logger.error(f"Failed to save comparison to database: {e}")
            return None

    def _run_ai_analysis(self, overlay_path: str, old_page_path: str, new_page_path: str, drawing_name: str):
        """Run AI analysis on a single overlay"""
        try:
            from openai_change_analyzer import OpenAIChangeAnalyzer
            import tempfile

            # Create analyzer
            analyzer = OpenAIChangeAnalyzer()

            # Create a temporary folder structure for the analyzer
            with tempfile.TemporaryDirectory() as temp_dir:
                overlay_folder = os.path.join(temp_dir, drawing_name)
                os.makedirs(overlay_folder, exist_ok=True)

                # Copy all three required files to temp folder with expected names
                import shutil
                temp_old_path = os.path.join(overlay_folder, f"{drawing_name}_old.png")
                temp_new_path = os.path.join(overlay_folder, f"{drawing_name}_new.png")
                temp_overlay_path = os.path.join(overlay_folder, f"{drawing_name}_overlay.png")

                shutil.copy2(old_page_path, temp_old_path)
                shutil.copy2(new_page_path, temp_new_path)
                shutil.copy2(overlay_path, temp_overlay_path)

                logger.info(f"Analyzing overlay at {overlay_folder} with all three images")
                result = analyzer.analyze_overlay_folder(overlay_folder)

                return result

        except Exception as e:
            logger.error(f"AI analysis failed for {drawing_name}: {e}")
            return None

    def _save_ai_analysis_to_db(self, comparison_id: str, analysis_result) -> str:
        """Save AI analysis results to the database"""
        try:
            from gcp.database import get_db_session
            from gcp.database.models import AnalysisResult
            import uuid

            if not analysis_result or not comparison_id:
                return None

            with get_db_session() as db:
                analysis = AnalysisResult(
                    id=str(uuid.uuid4()),
                    comparison_id=comparison_id,
                    drawing_name=analysis_result.drawing_name,
                    changes_found=analysis_result.changes_found,
                    critical_change=analysis_result.critical_change,
                    analysis_summary=analysis_result.analysis_summary,
                    recommendations=analysis_result.recommendations,
                    success=analysis_result.success,
                    error_message=analysis_result.error_message,
                    ai_model_used='gpt-4o'
                )
                db.add(analysis)
                db.commit()

                logger.info(f"Saved AI analysis to database for {analysis_result.drawing_name}")
                return analysis.id

        except Exception as e:
            logger.error(f"Failed to save AI analysis to database: {e}")
            return None

    def _process_pages_parallel(self, old_pages: List[str], new_pages: List[str],
                               old_drawing_names: List[str], new_drawing_names: List[str],
                               temp_dir: str, results_dir: str, session_id: str) -> List[Dict]:
        """Process multiple pages in parallel for high-compute environments"""
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            min_pages = min(len(old_pages), len(new_pages))
            # Scale workers based on page count and available resources
            if min_pages <= 10:
                max_workers = min(4, os.cpu_count() or 1, min_pages)
            elif min_pages <= 50:
                max_workers = min(6, os.cpu_count() or 1)
            else:
                # For very large documents, use up to 8 workers but respect system limits
                max_workers = min(8, os.cpu_count() or 1)

            logger.info(f"Processing {min_pages} pages with {max_workers} workers")

            processed_results = [None] * min_pages  # Pre-allocate results list

            def process_single_page(i: int) -> Tuple[int, Dict]:
                """Process a single page and return index + result"""
                try:
                    # Get drawing name for this page
                    drawing_name = None
                    if old_drawing_names and i < len(old_drawing_names):
                        drawing_name = old_drawing_names[i]
                    elif new_drawing_names and i < len(new_drawing_names):
                        drawing_name = new_drawing_names[i]
                    else:
                        drawing_name = f"Page_{i+1:03d}"

                    # Process this single drawing pair
                    page_result = self._process_single_drawing_with_ai(
                        old_pages[i], new_pages[i], drawing_name, i + 1, temp_dir, results_dir, session_id
                    )

                    return i, page_result

                except Exception as e:
                    logger.error(f"Error processing page {i+1} in parallel: {e}")
                    return i, {
                        'page_number': i + 1,
                        'success': False,
                        'error': str(e)
                    }

            # Execute parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_index = {
                    executor.submit(process_single_page, i): i
                    for i in range(min_pages)
                }

                # Collect results as they complete
                completed = 0
                for future in as_completed(future_to_index):
                    try:
                        index, result = future.result(timeout=300)  # 5 minute timeout per page
                        processed_results[index] = result
                        completed += 1
                        logger.info(f"Completed page {index + 1}/{min_pages} ({completed}/{min_pages} total)")

                        # Memory cleanup
                        self._cleanup_page_memory()

                    except Exception as e:
                        index = future_to_index[future]
                        logger.error(f"Page {index + 1} failed: {e}")
                        processed_results[index] = {
                            'page_number': index + 1,
                            'success': False,
                            'error': str(e)
                        }

            # Filter out None results (shouldn't happen, but safety)
            return [r for r in processed_results if r is not None]

        except Exception as e:
            logger.error(f"Parallel processing failed, falling back to sequential: {e}")
            # Fallback to sequential processing
            return []

    def _save_results_to_json(self, results: Dict, session_id: str = None):
        """Save results to JSON file in both uploads and Cloud Storage for frontend consumption"""
        if not session_id:
            logger.warning("No session_id provided, skipping results.json save")
            return

        try:
            # Create results in format expected by frontend/chatbot
            chatbot_results = {
                'output_directories': []
            }

            # Extract directory names from successful comparisons
            for comparison in results.get('comparisons', []):
                if comparison.get('success', False) and comparison.get('drawing_name'):
                    chatbot_results['output_directories'].append(comparison['drawing_name'])

            # Save to local uploads directory (for chatbot access)
            uploads_dir = f"uploads/{session_id}"
            os.makedirs(uploads_dir, exist_ok=True)

            results_file_path = f"{uploads_dir}/results.json"
            with open(results_file_path, 'w') as f:
                json.dump(chatbot_results, f, indent=2)

            logger.info(f"Saved results.json with {len(chatbot_results['output_directories'])} directories to {results_file_path}")

            # Also save full results to Cloud Storage if available
            try:
                if storage_service and storage_service.bucket:
                    # Save the full results data to Cloud Storage
                    full_results_path = f"sessions/{session_id}/results.json"

                    # Convert any non-serializable objects to strings
                    serializable_results = json.loads(json.dumps(results, default=str))

                    results_json = json.dumps(serializable_results, indent=2)
                    storage_service.upload_file(
                        io.StringIO(results_json).read().encode('utf-8'),
                        full_results_path,
                        content_type='application/json'
                    )
                    logger.info(f"Saved full results to Cloud Storage: {full_results_path}")

            except Exception as e:
                logger.warning(f"Could not save results to Cloud Storage: {e}")

        except Exception as e:
            logger.error(f"Failed to save results.json: {e}")

# Usage example
def process_documents(old_pdf_path: str, new_pdf_path: str, session_id: str = None) -> Dict:
    """Main entry point for memory-efficient document processing"""
    # Detect environment and configure accordingly
    if os.getenv('ENVIRONMENT') == 'production':
        # Production Cloud Run with high compute/memory
        processor = ChunkedProcessor(
            max_sync_pages=50,  # Handle larger documents synchronously
            dpi=300,           # Higher quality for production
            use_ai_analysis=True,   # Enable AI analysis for summaries
            memory_limit_gb=25.0,   # Use most of 32GB available
            session_id=session_id
        )
        logger.info("Using production high-compute configuration")
    else:
        # Development mode - conservative settings
        processor = ChunkedProcessor(
            max_sync_pages=10,
            dpi=300,
            use_ai_analysis=True,
            memory_limit_gb=10,
            session_id=session_id
        )
        logger.info("Using development low-resource configuration")

    if processor.should_process_sync(old_pdf_path, new_pdf_path):
        logger.info("Processing synchronously with memory-optimized pipeline (small document)")
        return processor.process_sync(old_pdf_path, new_pdf_path, session_id)
    else:
        logger.info("Document too large for sync processing - using lightweight pipeline")
        return processor._process_lightweight(old_pdf_path, new_pdf_path, session_id)