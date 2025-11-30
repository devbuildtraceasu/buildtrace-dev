# Chatbot Implementation - Option 1 (Simple Context Injection)

## Overview

Implemented a minimal chatbot service that uses **Option 1: Simple Context Injection** approach. The chatbot downloads OCR JSON from storage and injects it as context into GPT prompts.

## Files Created

### 1. `services/context_retriever.py`
- Downloads OCR JSON from GCS/local storage
- Extracts key sections (notations, dimensions, revisions, etc.)
- Formats context as text for GPT prompts
- Supports single drawing or multiple drawings (for comparison)

### 2. `services/chatbot_service.py`
- GPT wrapper service
- Injects OCR context into prompts
- Handles conversation history
- Supports both single drawing and comparison queries

### 3. `test_chatbot_standalone.py`
- Standalone test script (works without database)
- Processes A-111_old.pdf and A-111_new.pdf directly
- Runs OCR on both PDFs
- Tests chatbot with both single and comparison contexts

### 4. `test_chatbot_quick.py`
- Database-based test script
- Requires drawings to be uploaded and OCR'd first
- Interactive mode for testing

### 5. `upload_and_process_a111.py`
- Script to upload A-111 PDFs to database and run OCR
- Requires database to be set up

## How It Works

1. **Context Retrieval**:
   - Downloads OCR JSON from storage using `drawing_version.ocr_result_ref`
   - Extracts key sections:
     - TITLE BLOCK & PROJECT IDENTIFICATION
     - KEYNOTES & ANNOTATIONS
     - DIMENSIONS & MEASUREMENTS
     - REVISION HISTORY & CHANGE TRACKING
     - GENERAL NOTES & DISCLAIMERS

2. **Context Formatting**:
   - Converts JSON sections to readable text
   - Limits long text (truncates to 100 chars for keynotes, 500 for general notes)
   - Formats as structured text for GPT

3. **GPT Prompt Construction**:
   - System prompt: Defines chatbot role
   - Context message: Injected drawing context
   - Conversation history: Last 10 messages
   - User message: Current question

4. **Response**:
   - Returns GPT response with metadata (tokens used, context used)

## Testing

### Standalone Test (No Database Required)

```bash
cd buildtrace-dev/backend
python3 test_chatbot_standalone.py
```

This will:
1. Process A-111_old.pdf and A-111_new.pdf
2. Run OCR on both (extracts notations, dimensions, etc.)
3. Test chatbot with questions about:
   - Single drawing (old version)
   - Both drawings (comparison)

### Database-Based Test (Requires Database)

First, upload and process drawings:
```bash
python3 upload_and_process_a111.py
```

Then test:
```bash
python3 test_chatbot_quick.py <old_version_id> <new_version_id>
```

Or let it auto-detect:
```bash
python3 test_chatbot_quick.py
```

## Example Questions

### Single Drawing:
- "What is this drawing about?"
- "What are the key notations on this drawing?"
- "What are the dimensions?"
- "What revision is this drawing?"

### Comparison (Both Drawings):
- "What are the differences between these two versions?"
- "What changed in the keynotes between old and new?"
- "Compare the dimensions between the two versions"

## Features

✅ **Simple Implementation**: No database indexing, no vector search
✅ **Fast to Deploy**: Works with existing OCR results
✅ **Context-Aware**: Uses actual OCR data from drawings
✅ **Comparison Support**: Can answer questions about differences
✅ **Conversation History**: Maintains context across messages

## Limitations

⚠️ **Performance**: Downloads entire OCR JSON for each query
⚠️ **Scalability**: Not optimized for large projects (100+ drawings)
⚠️ **Search**: No semantic search, only keyword matching in GPT
⚠️ **Memory**: Loads full JSON into memory

## Next Steps (Optional Enhancements)

1. **Option 2: RAG with Vector Search** - For better semantic understanding
2. **Option 3: Database Indexing** - For faster queries and structured search
3. **Caching**: Cache OCR results in memory to avoid re-downloading
4. **Chunking**: Split large contexts into smaller chunks for better GPT performance

## Configuration

Requires:
- `OPENAI_API_KEY` environment variable
- `OPENAI_MODEL` (defaults to `gpt-4o`, but can use `gpt-5`)

For database-based tests:
- `USE_DATABASE=true`
- Database connection configured

## Notes

- The standalone test works without database setup
- OCR processing can take 1-3 minutes per PDF (GPT Vision API)
- GPT-5 requires `max_completion_tokens` instead of `max_tokens` (already fixed)

