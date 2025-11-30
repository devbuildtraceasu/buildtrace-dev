# BuildTrace AI Web Application

A modern web interface for intelligent drawing comparison and analysis using your existing Python pipeline.

## Features

### 🎯 **Core Functionality**
- **Two-Panel Upload Interface**: Upload old and new drawing sets side-by-side
- **4-Step Process Indicator**: Clear workflow from upload to results
- **Intelligent Processing**: Uses your existing `complete_drawing_pipeline.py`
- **Real-time Status Updates**: Live feedback during processing

### 📊 **Results Dashboard**
- **Changes List Panel**: Shows all detected changes with drawing numbers
- **Detailed Analysis View**: Comprehensive breakdowns of each change
- **File Management**: Easy access to all generated overlays and output files

### 🤖 **AI Assistant Chatbot**
- **GPT-4 Integration**: Powered by OpenAI's latest model
- **Construction Expertise**: Specialized in building/construction knowledge
- **Context-Aware**: Uses your specific changelist results for relevant answers
- **Web Search Capability**: Gets current costs, codes, and regulations
- **Smart Suggestions**: Context-specific question recommendations

#### Chatbot Capabilities:
- **Cost Estimation**: "What are the typical costs for these changes?"
- **Scheduling**: "How long should this project take to complete?"
- **Permits & Regulations**: "What permits might be required?"
- **Safety & Compliance**: "Are there safety considerations for these changes?"
- **Material Specifications**: "What materials will be needed?"
- **Best Practices**: "What's the best sequence for implementation?"

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure OpenAI API
Create a `config.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Application
```bash
python app.py
```

The application will be available at: `http://localhost:5001`

## File Structure

```
buildtrace-overlay/
├── app.py                          # Main Flask application
├── chatbot_service.py              # AI chatbot service
├── complete_drawing_pipeline.py    # Your existing pipeline
├── templates/
│   ├── index.html                  # Upload interface
│   └── results.html                # Results dashboard
├── static/
│   ├── css/style.css              # Modern styling
│   └── js/
│       ├── app.js                 # Upload page logic
│       └── results.js             # Results & chat logic
└── uploads/                       # Session data storage
```

## API Endpoints

### Core Functions
- `POST /upload` - Upload old and new files
- `POST /process/<session_id>` - Start processing pipeline
- `GET /results/<session_id>` - View results page
- `GET /api/changes/<session_id>` - Get changes data

### Chatbot API
- `POST /api/chat/<session_id>` - Send chat message
- `GET /api/chat/<session_id>/suggested` - Get suggested questions
- `GET /api/chat/<session_id>/history` - Get chat history

## Usage Workflow

### 1. Upload Drawings
- **Drag & drop** or **click to browse** for old drawings
- **Drag & drop** or **click to browse** for new drawings
- Supports: **PDF, DWG, DXF, PNG, JPG** (max 50MB each)

### 2. Process & Analyze
- Click **"Compare Drawings"** button
- Watch real-time progress through 5 steps:
  1. File upload
  2. Drawing name extraction
  3. PDF to PNG conversion
  4. Drawing alignment & overlay creation
  5. AI analysis of changes

### 3. Review Results
- **Changes List**: Browse all detected modifications
- **Details Panel**: Deep-dive into specific changes
- **AI Assistant**: Ask questions about your project

### 4. Get Expert Advice
- Switch to **"AI Assistant"** tab
- Ask about costs, timeline, permits, materials
- Get construction-specific recommendations
- Access current industry information via web search

## Supported File Types

- **PDF**: Multi-page architectural drawings
- **DWG**: AutoCAD drawing files
- **DXF**: Drawing exchange format
- **PNG/JPG**: Image-based drawings

## Technical Integration

This web application seamlessly integrates with your existing Python functions:

- **`complete_drawing_pipeline()`**: Core processing engine
- **`compare_pdf_drawing_sets()`**: Drawing comparison logic
- **`OpenAIChangeAnalyzer`**: AI analysis functionality

No changes to your existing code were required - the webapp acts as a modern interface layer.

## AI Assistant Details

### Context Awareness
The chatbot automatically has access to:
- All detected changes from your session
- Drawing names and numbers
- Specific modifications found
- Analysis summaries and recommendations

### Construction Expertise
Pre-trained with knowledge in:
- Project management and scheduling
- Cost estimation and budgeting
- Building codes and regulations
- Material specifications
- Quality control and safety
- Change order management
- Risk assessment

### Web Search Integration
For current information, the bot can search for:
- Current material costs and labor rates
- Latest building codes and standards
- Regulatory requirements by location
- Industry best practices and trends

## Security & Privacy

- **Session-based**: Each upload creates an isolated session
- **Local Storage**: All files stay on your server
- **API Key Protection**: OpenAI key stored in environment variables
- **No Data Persistence**: Session data can be cleared as needed

## Customization

### Styling
Modify `static/css/style.css` for custom branding and colors.

### Chatbot Behavior
Update `chatbot_service.py` to adjust:
- System prompts and expertise areas
- Web search integration
- Response formatting
- Question suggestions

### UI Components
Templates in `templates/` can be customized for:
- Additional file type support
- Custom workflow steps
- Branded headers and footers

## Troubleshooting

### Common Issues

1. **Port 5000 in use**: App uses port 5001 by default
2. **OpenAI API errors**: Check your API key in `config.env`
3. **File upload limits**: Max 50MB per file (configurable in `app.py`)
4. **Processing failures**: Check that original pipeline dependencies are installed

### Logs
Check Flask console output for detailed error messages and processing status.

## Production Deployment

For production use:

1. **Use a production WSGI server** (gunicorn, uWSGI)
2. **Set up proper file storage** (cloud storage, database)
3. **Configure load balancing** for multiple users
4. **Implement user authentication** if needed
5. **Set up HTTPS** for secure file uploads

## Support

This webapp integrates with your existing BuildTrace pipeline. For issues:

1. Check that your original `complete_drawing_pipeline.py` works independently
2. Verify all dependencies are installed
3. Ensure OpenAI API key is configured correctly
4. Review Flask console logs for specific errors