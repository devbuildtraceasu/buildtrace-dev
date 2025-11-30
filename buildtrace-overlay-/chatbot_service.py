#!/usr/bin/env python3
"""
ChatBot Service for BuildTrace AI

Provides an intelligent chatbot interface that can answer construction-related questions
using GPT-4, web search capabilities, and context from the user's changelist results.
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from config import config

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError:
    print("Error: Required packages not installed. Run: pip install openai python-dotenv requests")
    raise

# Load environment variables
load_dotenv('config.env')

@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    session_id: Optional[str] = None

@dataclass
class WebSearchResult:
    """Represents a web search result"""
    title: str
    url: str
    snippet: str
    relevance_score: float = 0.0

class ConstructionChatBot:
    """
    Intelligent chatbot for construction-related queries with context awareness
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the chatbot

        Args:
            api_key: OpenAI API key (if None, loads from environment)
        """
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')  # Use the model from config

        # System prompt for construction expertise
        self.system_prompt = """You are BuildTrace AI Assistant, an expert construction project manager and technical advisor with deep knowledge in:

- Construction scheduling and project management
- Cost estimation and budget planning
- Building codes and regulations
- Material specifications and procurement
- Quality control and safety protocols
- Change order management
- Risk assessment and mitigation
- Architectural and engineering coordination

You have access to:
1. Web search capabilities for current information
2. Drawing comparison results and changelist data from the user's current session
3. Construction industry best practices and standards

When answering questions:
- Provide specific, actionable advice
- Reference current industry standards and costs when relevant
- Consider the drawing changes in the user's session for context
- Suggest realistic timelines and budget impacts
- Always prioritize safety and code compliance
- Be concise but thorough in your responses

If you need current information (costs, codes, standards), use web search.
If you reference the user's drawing changes, be specific about which changes you're discussing."""

    def search_web(self, query: str, num_results: int = 5) -> List[WebSearchResult]:
        """
        Perform web search for current information

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of web search results
        """
        try:
            # Using a simple web search API (you can replace with your preferred service)
            # For demo purposes, using DuckDuckGo Instant Answer API
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"

            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()

                results = []

                # Add abstract if available
                if data.get('Abstract'):
                    results.append(WebSearchResult(
                        title=data.get('AbstractSource', 'Web Result'),
                        url=data.get('AbstractURL', ''),
                        snippet=data.get('Abstract', ''),
                        relevance_score=0.9
                    ))

                # Add related topics
                for topic in data.get('RelatedTopics', [])[:num_results-1]:
                    if isinstance(topic, dict) and topic.get('Text'):
                        results.append(WebSearchResult(
                            title=topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                            url=topic.get('FirstURL', ''),
                            snippet=topic.get('Text', ''),
                            relevance_score=0.7
                        ))

                return results[:num_results]

        except Exception as e:
            print(f"Web search error: {e}")

        return []

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get changelist context from a session by reading session-specific change_analysis_*.json files

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session context
        """
        try:
            context = {
                'overlays_created': 0,
                'analyses_completed': 0,
                'changes': [],
                'drawings': []
            }

            # Check if we should use database mode
            use_database = config.USE_DATABASE
            print(f"[Chatbot] Getting context for session {session_id}, database mode: {use_database}")

            if use_database:
                # Get data from GCS JSON files via database session info
                print(f"[Chatbot] Using database mode for session {session_id}")
                try:
                    from gcp.database.database import get_db_session
                    from gcp.database.models import Comparison
                    from gcp.storage.storage_service import storage_service
                    import json

                    with get_db_session() as db:
                        # Query comparisons for this session to get drawing names
                        comparisons = db.query(Comparison).filter(Comparison.session_id == session_id).all()
                        print(f"[Chatbot] Found {len(comparisons)} comparisons for session {session_id}")

                        for comparison in comparisons:
                            drawing_name = comparison.drawing_name
                            print(f"[Chatbot] Processing drawing: {drawing_name}")

                            # Try to download and read the JSON analysis file from GCS
                            json_path = f"sessions/{session_id}/results/{drawing_name}/change_analysis_{drawing_name}.json"

                            try:
                                # Download JSON content from GCS
                                print(f"[Chatbot] Attempting to download JSON from GCS: {json_path}")
                                json_content = storage_service.download_file(json_path)
                                analysis_data = json.loads(json_content)
                                print(f"[Chatbot] Successfully loaded JSON for {drawing_name}")

                                # Process the complete analysis data from JSON
                                if not analysis_data.get('success', False):
                                    continue

                                # Extract all data from the JSON file (which has everything)
                                critical_change = analysis_data.get('critical_change', '')
                                changes_found = analysis_data.get('changes_found', [])
                                analysis_summary = analysis_data.get('analysis_summary', '')
                                recommendations_list = analysis_data.get('recommendations', [])

                                # Clean up changes
                                clean_changes = []
                                for change in changes_found:
                                    if isinstance(change, str):
                                        clean_change = change.replace('**', '').replace('- *Impact*:', 'Impact:')
                                        if len(clean_change.strip()) > 10:
                                            clean_changes.append(clean_change)

                                # Extract construction impact from analysis summary
                                construction_impact = ''
                                if 'Construction Impact' in analysis_summary:
                                    impact_start = analysis_summary.find('**Construction Impact**:')
                                    if impact_start == -1:
                                        impact_start = analysis_summary.find('### 3. Construction Impact')
                                    if impact_start != -1:
                                        impact_section = analysis_summary[impact_start:impact_start + 500]
                                        lines = impact_section.split('\n')
                                        for line in lines[1:]:  # Skip the header line
                                            if line.strip() and not line.startswith('#'):
                                                construction_impact = line.strip()
                                                break

                                # Use recommendations from JSON or defaults
                                if not recommendations_list:
                                    recommendations_list = [
                                        'Prioritize Structural Changes: Begin with critical structural alterations',
                                        'Coordinate with Utility Providers Early: Ensure utility adjustments progress',
                                        'Cost Management: Monitor budget impacts on structural changes',
                                        'Stakeholder Communication: Keep informed about timeline changes'
                                    ]

                                change_info = {
                                    'drawing_name': drawing_name,
                                    'critical_change': critical_change,
                                    'changes_found': clean_changes,
                                    'analysis_summary': analysis_summary,
                                    'construction_impact': construction_impact,
                                    'recommendations': recommendations_list
                                }

                                context['changes'].append(change_info)
                                context['drawings'].append(drawing_name)
                                context['analyses_completed'] += 1

                            except Exception as json_error:
                                # If JSON file not found or error reading, try to fall back to database
                                print(f"Could not read JSON for {drawing_name}: {json_error}")
                                print(f"Attempting database fallback for {drawing_name}")

                                # Fallback to AnalysisResult table
                                try:
                                    from gcp.database.models import AnalysisResult

                                    # Query the AnalysisResult table for this drawing
                                    analysis = db.query(AnalysisResult).filter_by(
                                        session_id=session_id,
                                        drawing_name=drawing_name
                                    ).first()

                                    if analysis:
                                        print(f"Found analysis data in database for {drawing_name}")

                                        # Process database data into same format as JSON
                                        critical_change = analysis.critical_change or 'Changes detected'
                                        changes_found = analysis.changes_found or []
                                        analysis_summary = analysis.analysis_summary or ''
                                        recommendations_list = analysis.recommendations or []

                                        # Clean up changes from database
                                        clean_changes = []
                                        for change in changes_found:
                                            if isinstance(change, str):
                                                clean_change = change.replace('**', '').replace('- *Impact*:', 'Impact:')
                                                if len(clean_change.strip()) > 10:
                                                    clean_changes.append(clean_change)

                                        # Extract construction impact from analysis summary
                                        construction_impact = ''
                                        if 'Construction Impact' in analysis_summary:
                                            impact_start = analysis_summary.find('**Construction Impact**:')
                                            if impact_start == -1:
                                                impact_start = analysis_summary.find('### 3. Construction Impact')
                                            if impact_start != -1:
                                                impact_section = analysis_summary[impact_start:impact_start + 500]
                                                lines = impact_section.split('\n')
                                                for line in lines[1:]:
                                                    if line.strip() and not line.startswith('#'):
                                                        construction_impact = line.strip()
                                                        break

                                        # Use recommendations from database or defaults
                                        if not recommendations_list:
                                            recommendations_list = [
                                                'Prioritize Structural Changes: Begin with critical structural alterations',
                                                'Coordinate with Utility Providers Early: Ensure utility adjustments progress',
                                                'Cost Management: Monitor budget impacts on structural changes',
                                                'Stakeholder Communication: Keep informed about timeline changes'
                                            ]

                                        change_info = {
                                            'drawing_name': drawing_name,
                                            'critical_change': critical_change,
                                            'changes_found': clean_changes,
                                            'analysis_summary': analysis_summary,
                                            'construction_impact': construction_impact,
                                            'recommendations': recommendations_list
                                        }

                                        context['changes'].append(change_info)
                                        context['drawings'].append(drawing_name)
                                        context['analyses_completed'] += 1

                                        print(f"Successfully added {drawing_name} from database fallback")
                                    else:
                                        print(f"No analysis found in database for {drawing_name}")
                                        continue

                                except Exception as db_error:
                                    print(f"Database fallback also failed for {drawing_name}: {db_error}")
                                    continue

                        context['overlays_created'] = len(context['changes'])
                        print(f"[Chatbot] Context loaded - Changes: {len(context['changes'])}, Drawings: {context['drawings']}")
                        return context

                except Exception as e:
                    print(f"Error accessing data from GCS: {e}")
                    # Fall back to file-based approach if database fails
                    pass

            # File-based approach (local mode or fallback)
            # Try to get session-specific results first
            # Look for session metadata or results files
            session_folder = os.path.join('uploads', session_id)
            results_file = os.path.join(session_folder, 'results.json')
            
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    results = json.load(f)
                
                # Get output directories from session results
                output_directories = results.get('output_directories', [])
                
                # Process each output directory from the session
                for output_dir in output_directories:
                    if not os.path.exists(output_dir) or 'overlay_results' not in output_dir:
                        continue
                    
                    # Look for change_analysis_*.json files in this specific directory
                    for file_name in os.listdir(output_dir):
                        if file_name.startswith('change_analysis_') and file_name.endswith('.json'):
                            analysis_file = os.path.join(output_dir, file_name)
                        
                            try:
                                with open(analysis_file, 'r') as f:
                                    analysis_data = json.load(f)
                                
                                if not analysis_data.get('success', False):
                                    continue
                                
                                # Extract drawing name from filename or data
                                drawing_name = analysis_data.get('drawing_name', '')
                                if not drawing_name:
                                    # Extract from filename like change_analysis_A-111.json
                                    drawing_name = file_name.replace('change_analysis_', '').replace('.json', '')
                                
                                # Extract critical change
                                critical_change = analysis_data.get('critical_change', '')
                                if critical_change.startswith('### 1. Most Critical Change') or critical_change.startswith('#### 1. Most Critical Change'):
                                    # Extract the actual critical change from analysis_summary
                                    summary = analysis_data.get('analysis_summary', '')
                                    if 'Most Critical Change' in summary:
                                        # Try to extract the first meaningful change
                                        lines = summary.split('\n')
                                        for line in lines:
                                            if '**[' in line and '] + [' in line:
                                                critical_change = line.strip()
                                                break
                                
                                # Process changes_found array
                                changes_found = analysis_data.get('changes_found', [])
                                clean_changes = []
                                
                                for change in changes_found:
                                    if isinstance(change, str):
                                        # Clean up the change description
                                        clean_change = change.replace('**', '').replace('- *Impact*:', 'Impact:')
                                        if (not clean_change.startswith('- **Timeline') and
                                            not clean_change.startswith('- **Cost') and
                                            not clean_change.startswith('- **Labor') and
                                            len(clean_change.strip()) > 10 and
                                            not clean_change.strip().startswith('-')):
                                            
                                            if '] + [' in clean_change:
                                                parts = clean_change.split('] + [')
                                                if len(parts) >= 3:
                                                    change_type = parts[0].replace('[', '').strip()
                                                    detail = parts[2].split('] + [')[0].replace(']', '').strip()
                                                    clean_changes.append(f"{change_type}: {detail}")
                                            elif 'Impact:' in clean_change:
                                                clean_changes.append(clean_change)
                                            elif not clean_change.startswith('- '):
                                                clean_changes.append(clean_change)
                                
                                # Extract recommendations from analysis_summary
                                recommendations = []
                                summary_text = analysis_data.get('analysis_summary', '')
                                if '### 4. Recommendations' in summary_text or '#### 4. Recommendations' in summary_text:
                                    rec_section = summary_text.split('### 4. Recommendations')[1] if '### 4. Recommendations' in summary_text else summary_text.split('#### 4. Recommendations')[1]
                                    rec_lines = rec_section.split('\n')
                                    for line in rec_lines:
                                        line = line.strip()
                                        if line.startswith('- **') and '**:' in line:
                                            rec = line.replace('- **', '').replace('**:', ':')
                                            recommendations.append(rec)
                                
                                # If no recommendations found, use defaults
                                if not recommendations:
                                    recommendations = [
                                        'Prioritize Structural Changes: Begin with critical structural alterations to avoid future delays',
                                        'Coordinate with Utility Providers Early: Ensure utility adjustments do not delay progress',
                                        'Cost Management: Monitor budget impacts, especially on structural and utility changes',
                                        'Stakeholder Communication: Keep stakeholders informed about timeline and scope changes'
                                    ]
                                
                                # Create clean summary
                                summary = analysis_data.get('analysis_summary', '')
                                if 'Construction Impact' in summary:
                                    impact_start = summary.find('**Construction Impact**:')
                                    if impact_start != -1:
                                        impact_section = summary[impact_start + len('**Construction Impact**:'):impact_start + 400]
                                        clean_impact = impact_section.replace('**', '').replace('\n', ' ').strip()
                                        sentences = clean_impact.split('. ')
                                        if sentences and len(sentences[0]) > 20:
                                            summary = sentences[0].strip() + '.'
                                        else:
                                            summary = "Significant structural alterations impacting both cost and timeline"
                                
                                change_info = {
                                    'drawing_name': drawing_name,
                                    'critical_change': critical_change,
                                    'changes_found': clean_changes,  # Include all changes
                                    'analysis_summary': summary,
                                    'recommendations': recommendations  # Include all recommendations
                                }
                                
                                context['changes'].append(change_info)
                                context['drawings'].append(drawing_name)
                                context['analyses_completed'] += 1
                                
                            except Exception as e:
                                print(f"Error processing analysis file {analysis_file}: {e}")
                                continue
            else:
                # Fallback: if no session results found, return empty context
                print(f"No session results found for session {session_id}")
                return context
            
            # Set overlays created based on number of changes found
            context['overlays_created'] = len(context['changes'])
            
            return context

        except Exception as e:
            print(f"Error getting session context: {e}")

        return {'overlays_created': 0, 'analyses_completed': 0, 'changes': [], 'drawings': []}

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format session context for inclusion in the prompt

        Args:
            context: Session context dictionary

        Returns:
            Formatted context string
        """
        if not context['changes']:
            return "No drawing comparison results available in this session."

        context_text = f"Current Session Drawing Analysis:\n"
        context_text += f"- {context['overlays_created']} drawing overlays created\n"
        context_text += f"- {context['analyses_completed']} AI analyses completed\n"
        context_text += f"- Drawings analyzed: {', '.join(context['drawings'])}\n\n"

        context_text += "Detected Changes:\n"
        for i, change in enumerate(context['changes'], 1):
            context_text += f"\n{i}. Drawing: {change['drawing_name']}\n"
            context_text += f"   Critical Change: {change['critical_change']}\n"
            context_text += f"   Summary: {change['analysis_summary']}\n"

            # Include construction impact if available
            if change.get('construction_impact'):
                context_text += f"   Construction Impact: {change['construction_impact']}\n"

            if change['changes_found']:
                context_text += f"   Specific Changes:\n"
                for change_detail in change['changes_found']:  # Include all changes
                    context_text += f"   - {change_detail}\n"

            if change['recommendations']:
                context_text += f"   Recommendations:\n"
                for rec in change['recommendations']:  # Include all recommendations
                    context_text += f"   - {rec}\n"

        return context_text

    def chat(self, user_message: str, session_id: Optional[str] = None,
             conversation_history: List[ChatMessage] = None) -> ChatMessage:
        """
        Process a chat message and generate a response

        Args:
            user_message: User's message
            session_id: Optional session ID for context
            conversation_history: Previous messages in conversation

        Returns:
            ChatMessage with assistant's response
        """
        try:
            # Build conversation context
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add session context if available
            if session_id:
                context = self.get_session_context(session_id)
                context_text = self.format_context_for_prompt(context)
                messages.append({
                    "role": "system",
                    "content": f"Session Context:\n{context_text}"
                })

            # Add conversation history
            if conversation_history:
                # Keep last 10 messages, but handle empty list safely
                recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                for msg in recent_history:
                    if msg.role in ['user', 'assistant']:
                        messages.append({"role": msg.role, "content": msg.content})

            # Check if we need web search
            search_keywords = [
                'current', 'latest', 'cost', 'price', 'code', 'regulation',
                'standard', 'market', 'today', '2024', '2025'
            ]

            needs_search = any(keyword in user_message.lower() for keyword in search_keywords)

            web_context = ""
            if needs_search:
                # Perform web search
                search_query = f"construction {user_message} 2024"
                search_results = self.search_web(search_query)

                if search_results:
                    web_context = "\nCurrent Web Information:\n"
                    for result in search_results[:3]:
                        web_context += f"- {result.title}: {result.snippet}\n"

                    messages.append({
                        "role": "system",
                        "content": f"Recent web search results for context:{web_context}"
                    })

            # Add user message
            messages.append({"role": "user", "content": user_message})

            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            assistant_message = response.choices[0].message.content

            return ChatMessage(
                role="assistant",
                content=assistant_message,
                timestamp=datetime.now(),
                session_id=session_id
            )

        except Exception as e:
            error_message = f"I apologize, but I encountered an error processing your request: {str(e)}"
            return ChatMessage(
                role="assistant",
                content=error_message,
                timestamp=datetime.now(),
                session_id=session_id
            )

    def get_suggested_questions(self, session_id: Optional[str] = None) -> List[str]:
        """
        Generate suggested questions based on session context

        Args:
            session_id: Optional session ID

        Returns:
            List of suggested questions
        """
        base_questions = [
            "What are the typical costs for these types of changes?",
            "How long should this project take to complete?",
            "What permits might be required for these modifications?",
            "Are there any safety considerations I should be aware of?",
            "What's the best sequence for implementing these changes?"
        ]

        if session_id:
            context = self.get_session_context(session_id)
            if context['changes']:
                # Generate context-specific questions
                drawings = context['drawings']
                context_questions = [
                    f"What's the estimated cost impact of changes to {drawings[0] if drawings else 'these drawings'}?",
                    "How do these changes affect the project timeline?",
                    "What materials will be needed for these modifications?",
                    "Should these changes be done in phases or all at once?",
                ]
                return context_questions + base_questions[:3]

        return base_questions