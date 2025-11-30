# OCR Enhancement - Page-by-Page Information Extraction

## Overview

Enhanced the OCR pipeline to extract detailed information from each page of architectural drawings using OpenAI Vision API, store it in a log file, and display it in real-time during processing.

## Features Added

### 1. Page-by-Page Information Extraction
- Processes each PDF page individually
- Uses OpenAI Vision API (GPT-4o) to extract structured information
- Extracts comprehensive details including:
  - Project & Drawing Identification (name, address, number, title, scale)
  - Client/Owner information
  - Architect & Consultants (all team members)
  - Project Team (PM, checker, drafter)
  - Drawing/Revision History
  - Title block notes and disclaimers

### 2. Real-Time Log File
- Creates a JSON log file that updates after each page is processed
- Log file stored in: `ocr_logs/{drawing_version_id}/ocr_log.json`
- Contains:
  - Page-by-page extraction results
  - Processing timestamps
  - Summary generated after all pages complete

### 3. Summary Generation
- After all pages are processed, generates a comprehensive summary
- Includes:
  - Total pages processed
  - All drawings found
  - Project information
  - Architect information
  - Revision summary

### 4. Frontend Display
- New API endpoint: `GET /api/v1/jobs/<job_id>/ocr-log`
- Side panel in ProcessingMonitor component displays:
  - Project name
  - Architect information
  - Drawings found
  - Revision count
  - Page-by-page processing status
- Updates in real-time (polls every 3 seconds during OCR)

## Implementation Details

### Backend Changes

#### `processing/ocr_pipeline.py`
- Added OpenAI Vision API integration
- `_extract_page_information()`: Extracts detailed info from each page
- `_generate_summary()`: Creates summary from all pages
- Log file created and updated after each page
- Summary included in OCR payload for storage

#### `blueprints/jobs.py`
- New endpoint: `GET /api/v1/jobs/<job_id>/ocr-log`
- Fetches OCR logs for both old and new drawing versions
- Returns structured data for frontend display

### Frontend Changes

#### `lib/api.ts`
- Added `getOcrLog(jobId)` method

#### `components/upload/ProcessingMonitor.tsx`
- Added OCR information sidebar
- Real-time polling of OCR logs
- Displays project, architect, drawings, and revisions
- Shows page-by-page processing status

#### `components/pages/UploadPage.tsx`
- Passes `jobId` to ProcessingMonitor for OCR log fetching

## Data Structure

### OCR Log File Format
```json
{
  "drawing_version_id": "...",
  "started_at": "2025-01-XX...",
  "pages": [
    {
      "page_number": 1,
      "drawing_name": "A-101",
      "extracted_info": {
        "sections": {
          "Project & Drawing Identification": {...},
          "Architect & Consultants": {...},
          "Drawing/Revision History": {...}
        }
      },
      "processed_at": "2025-01-XX..."
    }
  ],
  "summary": {
    "total_pages": 1,
    "drawings_found": ["A-101"],
    "project_info": {...},
    "architect_info": {...},
    "revision_summary": {...}
  },
  "completed_at": "2025-01-XX..."
}
```

## Usage

1. When a drawing is uploaded, OCR pipeline automatically:
   - Extracts drawing names
   - Converts PDF pages to PNG
   - Processes each page with OpenAI Vision API
   - Updates log file after each page
   - Generates summary after all pages complete

2. Frontend automatically:
   - Fetches OCR log when OCR stage is active
   - Displays information in side panel
   - Updates every 3 seconds during processing

## Benefits

- **User Engagement**: Users see useful information while waiting for comparison
- **Transparency**: Real-time visibility into what's being extracted
- **Rich Metadata**: Comprehensive project and drawing information available
- **Better UX**: No blank screen during processing

## Configuration

Requires OpenAI API key in `config.OPENAI_API_KEY` environment variable.

Uses model specified in `config.OPENAI_MODEL` (defaults to "gpt-4o").

## Future Enhancements

- Add caching to reduce API calls for repeated pages
- Support for multi-page drawings with better aggregation
- Export OCR log as PDF report
- Search functionality within extracted information

