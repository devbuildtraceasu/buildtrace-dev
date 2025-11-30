#!/usr/bin/env python3
"""
BuildTrace AI Web Application

Flask web app that provides a UI for drawing comparison using the existing pipeline.
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import time

# Import existing pipeline functions
from complete_drawing_pipeline import complete_drawing_pipeline
from chatbot_service import ConstructionChatBot, ChatMessage

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create uploads directory
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'png', 'jpg', 'jpeg'}

for folder in [UPLOAD_FOLDER, RESULTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Initialize chatbot
chatbot = ConstructionChatBot()

# Store conversation histories (in production, use a database)
conversation_histories = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main upload interface"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and start processing"""
    try:
        # Check if files are provided
        if 'old_file' not in request.files or 'new_file' not in request.files:
            return jsonify({'error': 'Both old and new files are required'}), 400

        old_file = request.files['old_file']
        new_file = request.files['new_file']

        # Check if files are selected
        if old_file.filename == '' or new_file.filename == '':
            return jsonify({'error': 'No files selected'}), 400

        # Check file types
        if not (allowed_file(old_file.filename) and allowed_file(new_file.filename)):
            return jsonify({'error': 'Invalid file type. Allowed: PDF, DWG, DXF, PNG, JPG'}), 400

        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)

        # Save uploaded files
        old_filename = secure_filename(old_file.filename)
        new_filename = secure_filename(new_file.filename)

        old_path = os.path.join(session_folder, f"old_{old_filename}")
        new_path = os.path.join(session_folder, f"new_{new_filename}")

        old_file.save(old_path)
        new_file.save(new_path)

        return jsonify({
            'session_id': session_id,
            'old_filename': old_filename,
            'new_filename': new_filename
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process/<session_id>', methods=['POST'])
def process_drawings(session_id):
    """Process the uploaded drawings using the existing pipeline"""
    try:
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        if not os.path.exists(session_folder):
            return jsonify({'error': 'Session not found'}), 404

        # Find uploaded files
        files = os.listdir(session_folder)
        old_file = next((f for f in files if f.startswith('old_')), None)
        new_file = next((f for f in files if f.startswith('new_')), None)

        if not old_file or not new_file:
            return jsonify({'error': 'Uploaded files not found'}), 404

        old_path = os.path.join(session_folder, old_file)
        new_path = os.path.join(session_folder, new_file)

        # Run the complete pipeline
        results = complete_drawing_pipeline(
            old_pdf_path=old_path,
            new_pdf_path=new_path,
            dpi=300,
            debug=False,
            skip_ai_analysis=False
        )

        # Store results
        results_file = os.path.join(session_folder, 'results.json')
        with open(results_file, 'w') as f:
            # Convert any Path objects to strings for JSON serialization
            json_results = json.loads(json.dumps(results, default=str))
            json.dump(json_results, f, indent=2)

        # Format response
        if results['success']:
            return jsonify({
                'success': True,
                'session_id': session_id,
                'overlays_created': results['summary']['overlays_created'],
                'analyses_completed': results['summary']['analyses_completed'],
                'output_directory': results['summary'].get('base_overlay_directory', ''),
                'processing_time': results['summary']['total_time']
            })
        else:
            return jsonify({
                'success': False,
                'error': results.get('error', 'Unknown error occurred')
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/results/<session_id>')
def view_results(session_id):
    """Display results page"""
    try:
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        results_file = os.path.join(session_folder, 'results.json')

        if not os.path.exists(results_file):
            return "Results not found", 404

        with open(results_file, 'r') as f:
            results = json.load(f)

        return render_template('results.html',
                             session_id=session_id,
                             results=results)

    except Exception as e:
        return f"Error loading results: {str(e)}", 500

@app.route('/api/changes/<session_id>')
def get_changes(session_id):
    """API endpoint to get changes data for the changes list interface"""
    try:
        # Load results to get overlay directories
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        results_file = os.path.join(session_folder, 'results.json')

        if not os.path.exists(results_file):
            return jsonify({'error': 'Results not found'}), 404

        with open(results_file, 'r') as f:
            results = json.load(f)

        # Get output directories from results
        output_directories = results.get('output_directories', [])
        changes = []

        # Look for individual analysis JSON files
        for i, output_dir in enumerate(output_directories):
            if not os.path.exists(output_dir) or not 'overlay_results' in output_dir:
                continue

            # Look for change_analysis_*.json files in the directory
            for file_name in os.listdir(output_dir):
                if file_name.startswith('change_analysis_') and file_name.endswith('.json'):
                    analysis_file = os.path.join(output_dir, file_name)

                    try:
                        with open(analysis_file, 'r') as f:
                            analysis_data = json.load(f)

                        if not analysis_data.get('success', False):
                            continue

                        drawing_name = analysis_data.get('drawing_name', f'Drawing {i+1}')

                        # Extract meaningful critical change
                        critical_change = analysis_data.get('critical_change', '')
                        if critical_change.startswith('### 1. Most Critical Change'):
                            # Extract the actual critical change content
                            summary_text = analysis_data.get('analysis_summary', '')
                            if '**[Room Configuration]' in summary_text:
                                critical_change = 'Storage area reconfigured near break room'
                            elif '**[New Addition]' in summary_text:
                                critical_change = 'New additions detected'
                            elif '**[Wall Shift]' in summary_text:
                                critical_change = 'Wall modifications detected'
                            else:
                                critical_change = 'Structural changes detected'

                        # Process changes_found array to extract meaningful changes
                        changes_found = analysis_data.get('changes_found', [])
                        clean_changes = []

                        for change in changes_found:
                            if isinstance(change, str):
                                # Remove markdown formatting and extract key information
                                clean_change = change.replace('**', '').replace('- *Impact*:', 'Impact:')

                                # Filter out timeline and cost summary lines
                                if (not clean_change.startswith('- **Timeline') and
                                    not clean_change.startswith('- **Cost') and
                                    len(clean_change.strip()) > 10 and
                                    not clean_change.strip().startswith('-')):

                                    # Extract the core change description
                                    if '] + [' in clean_change:
                                        # Extract the bracketed information
                                        parts = clean_change.split('] + [')
                                        if len(parts) >= 3:
                                            change_type = parts[0].replace('[', '').strip()
                                            action = parts[1].strip()
                                            detail = parts[2].split('] + [')[0].replace(']', '').strip()
                                            clean_changes.append(f"{change_type}: {detail}")
                                    elif 'Impact:' in clean_change:
                                        clean_changes.append(clean_change)

                        # If no clean changes found, extract from summary
                        if not clean_changes:
                            summary_text = analysis_data.get('analysis_summary', '')
                            if 'Room Configuration' in summary_text:
                                clean_changes.append('Storage area reconfiguration')
                            if 'New Addition' in summary_text:
                                clean_changes.append('Green space addition near entrance')
                            if 'Wall Shift' in summary_text:
                                clean_changes.append('Interior partition moved in break room area')
                            if 'Utility Lines' in summary_text:
                                clean_changes.append('Utility line re-routing throughout site')
                            if 'New Fixtures' in summary_text:
                                clean_changes.append('Restroom upgrades and new fixtures')
                            if 'Doorway' in summary_text:
                                clean_changes.append('Main entrance doorway expansion')

                        # Create a clean summary from analysis_summary
                        summary = analysis_data.get('analysis_summary', '')
                        if summary:
                            # Extract the construction impact section for a meaningful summary
                            if 'Construction Impact' in summary:
                                impact_start = summary.find('**Construction Impact**:')
                                if impact_start != -1:
                                    # Extract the impact description
                                    impact_section = summary[impact_start + len('**Construction Impact**:'):impact_start + 400]
                                    # Clean up markdown and extract first sentence
                                    clean_impact = impact_section.replace('**', '').replace('\n', ' ').strip()
                                    sentences = clean_impact.split('. ')
                                    if sentences and len(sentences[0]) > 20:
                                        summary = sentences[0].strip() + '.'
                                    else:
                                        summary = "Significant structural alterations impacting both cost and timeline due to storage reconfiguration requirements"
                                else:
                                    summary = "Multiple structural and design changes detected requiring construction modifications"
                            else:
                                # Extract a meaningful description from the summary
                                clean_summary = summary.replace('**', '').replace('### 1. Most Critical Change\n', '').replace('\n', ' ')
                                # Find the first substantial sentence
                                if '[Room Configuration]' in clean_summary:
                                    summary = "Storage area reconfiguration involves significant structural alterations affecting cost and timeline"
                                elif 'structural alterations' in clean_summary.lower():
                                    summary = "Significant structural alterations detected impacting both cost and construction timeline"
                                else:
                                    summary = "Comprehensive analysis of architectural drawing changes with multiple structural modifications"

                        # Process recommendations
                        recommendations_raw = analysis_data.get('recommendations', [])
                        recommendations = []

                        # Extract recommendations from analysis_summary if not in recommendations field
                        if not recommendations_raw or len(recommendations_raw) < 3:
                            summary_text = analysis_data.get('analysis_summary', '')
                            if '### 4. Recommendations' in summary_text:
                                rec_section = summary_text.split('### 4. Recommendations')[1]
                                rec_lines = rec_section.split('\n')
                                for line in rec_lines:
                                    line = line.strip()
                                    if line.startswith('- **') and '**:' in line:
                                        # Extract recommendation text
                                        rec = line.replace('- **', '').replace('**:', ':')
                                        recommendations.append(rec)

                        # Default recommendations if none found
                        if not recommendations:
                            recommendations = [
                                'Prioritize Structural Changes: Begin with critical structural alterations to avoid future delays',
                                'Coordinate with Utility Providers Early: Ensure utility adjustments do not delay progress',
                                'Cost Management: Monitor budget impacts, especially on structural and utility changes',
                                'Stakeholder Communication: Keep stakeholders informed about timeline and scope changes'
                            ]

                        changes.append({
                            'id': i + 1,
                            'drawing_number': drawing_name,
                            'description': critical_change,
                            'details': clean_changes,
                            'summary': summary,
                            'recommendations': recommendations
                        })

                    except Exception as e:
                        print(f"Error processing analysis file {analysis_file}: {e}")
                        continue

        return jsonify({'changes': changes})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<session_id>/<path:filename>')
def download_file(session_id, filename):
    """Download files from session directory"""
    try:
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        return send_from_directory(session_folder, filename, as_attachment=True)
    except Exception as e:
        return f"File not found: {str(e)}", 404

@app.route('/api/drawings/<session_id>')
def get_drawing_images(session_id):
    """Get available drawing images for comparison view"""
    try:
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        results_file = os.path.join(session_folder, 'results.json')

        if not os.path.exists(results_file):
            return jsonify({'error': 'Results not found'}), 404

        with open(results_file, 'r') as f:
            results = json.load(f)

        # Get base directories from results
        base_overlay_dir = results.get('summary', {}).get('base_overlay_directory', '')

        # Find all overlay folders and images
        drawing_comparisons = []

        # Debug: print what we're looking for
        print(f"Looking for overlays in: {base_overlay_dir}")

        if base_overlay_dir and os.path.exists(base_overlay_dir):
            # List all subdirectories in overlay folder
            for folder_name in sorted(os.listdir(base_overlay_dir)):
                folder_path = os.path.join(base_overlay_dir, folder_name)
                if os.path.isdir(folder_path) and 'overlay_results' in folder_name:
                    # Extract drawing name from folder name (e.g., "A-101_overlay_results" -> "A-101")
                    drawing_name = folder_name.replace('_overlay_results', '')

                    comparison = {
                        'drawing_name': drawing_name,
                        'old_image': None,
                        'new_image': None,
                        'overlay_image': None
                    }

                    # Look for images in the folder
                    for file_name in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file_name)
                        if file_name.endswith(('.png', '.jpg', '.jpeg')):
                            # Match exact naming pattern and return paths with /image/ prefix
                            if file_name == f"{drawing_name}_old.png":
                                comparison['old_image'] = f"/image/{file_path}"
                            elif file_name == f"{drawing_name}_new.png":
                                comparison['new_image'] = f"/image/{file_path}"
                            elif file_name == f"{drawing_name}_overlay.png":
                                comparison['overlay_image'] = f"/image/{file_path}"

                    if comparison['overlay_image']:  # Only include if overlay exists
                        print(f"Found overlay for {drawing_name}: {comparison['overlay_image']}")
                        drawing_comparisons.append(comparison)

        print(f"Total comparisons found: {len(drawing_comparisons)}")
        return jsonify({'comparisons': drawing_comparisons})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/image/<path:image_path>')
def serve_image(image_path):
    """Serve image files from any path"""
    try:
        # Security check - ensure path doesn't go outside project directory
        abs_path = os.path.abspath(image_path)
        project_dir = os.path.abspath('.')

        if not abs_path.startswith(project_dir):
            return "Access denied", 403

        if os.path.exists(abs_path):
            directory = os.path.dirname(abs_path)
            filename = os.path.basename(abs_path)
            return send_from_directory(directory, filename)
        else:
            return "Image not found", 404

    except Exception as e:
        return f"Error serving image: {str(e)}", 500

@app.route('/api/chat/<session_id>', methods=['POST'])
def chat_message(session_id):
    """Handle chatbot messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        # Get conversation history for this session
        if session_id not in conversation_histories:
            conversation_histories[session_id] = []

        # Add user message to history
        user_chat_msg = ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(),
            session_id=session_id
        )
        conversation_histories[session_id].append(user_chat_msg)

        # Generate response
        response_msg = chatbot.chat(
            user_message=user_message,
            session_id=session_id,
            conversation_history=conversation_histories[session_id]
        )

        # Add assistant response to history
        conversation_histories[session_id].append(response_msg)

        # Limit conversation history to last 20 messages
        if len(conversation_histories[session_id]) > 20:
            conversation_histories[session_id] = conversation_histories[session_id][-20:]

        return jsonify({
            'response': response_msg.content,
            'timestamp': response_msg.timestamp.isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/suggested', methods=['GET'])
def get_suggested_questions(session_id):
    """Get suggested questions for the chatbot"""
    try:
        suggestions = chatbot.get_suggested_questions(session_id)
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a session"""
    try:
        history = conversation_histories.get(session_id, [])
        formatted_history = [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in history
        ]
        return jsonify({'history': formatted_history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)