"""
Page handlers for Claude-call and no-call page types
"""

import logging
import json
from flask import jsonify

logger = logging.getLogger(__name__)

def build_claude_prompt(form_data, uploaded_files_data, server_files_data):
    """Build Claude prompt from form data, uploaded files, and server files"""
    
    # Get the custom prompt from the form
    custom_prompt = form_data.get('claude_prompt', '').strip()
    if not custom_prompt:
        return None, "No Claude prompt provided"
    
    # Build the context sections
    context_sections = []
    
    # Add server files first (background/examples)
    if server_files_data:
        context_sections.append("=== SERVER REFERENCE FILES ===")
        for file_name, file_data in server_files_data.items():
            context_sections.append(f"\n--- {file_name.upper()} ---")
            
            if isinstance(file_data, dict):
                # Rich file data with structure
                if 'text_content' in file_data:
                    context_sections.append("Text Content:")
                    context_sections.append(file_data['text_content'].strip())
                
                if 'xml_structure' in file_data and file_data['xml_structure']:
                    context_sections.append("\nDocument Structure (XML):")
                    if isinstance(file_data['xml_structure'], dict):
                        for xml_type, xml_content in file_data['xml_structure'].items():
                            if xml_type != 'error' and xml_content:
                                context_sections.append(f"{xml_type.upper()}:")
                                # Truncate very long XML for readability
                                if len(xml_content) > 2000:
                                    context_sections.append(xml_content[:2000] + "... [truncated]")
                                else:
                                    context_sections.append(xml_content)
                
                if 'form_data' in file_data and file_data['form_data']:
                    context_sections.append("\nPDF Form Data and Metadata:")
                    context_sections.append(json.dumps(file_data['form_data'], indent=2))
            else:
                # Legacy text-only data
                context_sections.append(str(file_data).strip())
    
    # Add form data (excluding the prompt itself)
    form_context = {}
    for key, value in form_data.items():
        if key not in ['claude_prompt', 'page_type', 'page_title'] and value.strip():
            form_context[key] = value.strip()
    
    if form_context:
        context_sections.append("\n=== FORM DATA ===")
        for key, value in form_context.items():
            context_sections.append(f"{key.replace('_', ' ').title()}: {value}")
    
    # Add uploaded file contents
    if uploaded_files_data:
        for file_type, file_data in uploaded_files_data.items():
            if file_data:
                context_sections.append(f"\n=== UPLOADED {file_type.upper()} CONTENT ===")
                
                if isinstance(file_data, dict):
                    # Rich file data with structure
                    if 'text_content' in file_data:
                        context_sections.append("Text Content:")
                        context_sections.append(file_data['text_content'].strip())
                    
                    if 'xml_structure' in file_data and file_data['xml_structure']:
                        context_sections.append("\nDocument Structure (XML):")
                        if isinstance(file_data['xml_structure'], dict):
                            for xml_type, xml_content in file_data['xml_structure'].items():
                                if xml_type != 'error' and xml_content:
                                    context_sections.append(f"{xml_type.upper()}:")
                                    # Truncate very long XML for readability
                                    if len(xml_content) > 2000:
                                        context_sections.append(xml_content[:2000] + "... [truncated]")
                                    else:
                                        context_sections.append(xml_content)
                    
                    if 'form_data' in file_data and file_data['form_data']:
                        context_sections.append("\nPDF Form Data and Metadata:")
                        context_sections.append(json.dumps(file_data['form_data'], indent=2))
                else:
                    # Legacy text-only data
                    context_sections.append(str(file_data).strip())
    
    # Combine everything
    if context_sections:
        full_prompt = "\n".join(context_sections) + "\n\n" + custom_prompt
    else:
        full_prompt = custom_prompt
    
    return full_prompt, None

def handle_no_call_page(page_name, form_data, uploaded_files_data, server_files_data, session_id):
    """Handle no-call pages that organize and display information without API calls"""
    try:
        logger.info(f"Processing no-call page: {page_name}")
        
        # Build organized content from available data
        content_sections = []
        
        # Add page header
        page_title = form_data.get('page_title', page_name.replace('-', ' ').title())
        content_sections.append(f"# {page_title}")
        content_sections.append("")
        
        # Add server reference files with rich data
        if server_files_data:
            content_sections.append("## Reference Materials")
            content_sections.append("")
            for file_name, file_data in server_files_data.items():
                content_sections.append(f"### {file_name.title()}")
                content_sections.append("")
                
                if isinstance(file_data, dict):
                    # Rich file data
                    content_sections.append(f"**File Type:** {file_data.get('file_type', 'unknown').upper()}")
                    
                    if 'text_content' in file_data:
                        content_sections.append("**Text Content Preview:**")
                        preview = file_data['text_content'][:500] + "..." if len(file_data['text_content']) > 500 else file_data['text_content']
                        content_sections.append(preview)
                    
                    if 'xml_structure' in file_data and file_data['xml_structure']:
                        content_sections.append("**Document Structure Available:** Yes (XML)")
                    
                    if 'form_data' in file_data and file_data['form_data']:
                        content_sections.append("**PDF Form Data Available:** Yes")
                        if 'document_info' in file_data['form_data']:
                            doc_info = file_data['form_data']['document_info']
                            content_sections.append(f"- Pages: {doc_info.get('page_count', 'unknown')}")
                            content_sections.append(f"- Has Form Fields: {doc_info.get('has_form_fields', False)}")
                else:
                    # Legacy text data
                    preview = str(file_data)[:500] + "..." if len(str(file_data)) > 500 else str(file_data)
                    content_sections.append(preview)
                
                content_sections.append("")
        
        # Add form data
        if form_data:
            content_sections.append("## Submitted Information")
            content_sections.append("")
            for key, value in form_data.items():
                if key not in ['page_type', 'page_title'] and value.strip():
                    display_key = key.replace('_', ' ').title()
                    content_sections.append(f"**{display_key}:** {value}")
            content_sections.append("")
        
        # Add uploaded files with rich data
        if uploaded_files_data:
            content_sections.append("## Uploaded Documents")
            content_sections.append("")
            for file_type, file_data in uploaded_files_data.items():
                content_sections.append(f"### {file_type.title()}")
                content_sections.append("")
                
                if isinstance(file_data, dict):
                    # Rich file data
                    content_sections.append(f"**File Type:** {file_data.get('file_type', 'unknown').upper()}")
                    
                    if 'text_content' in file_data:
                        content_sections.append("**Text Content Preview:**")
                        preview = file_data['text_content'][:500] + "..." if len(file_data['text_content']) > 500 else file_data['text_content']
                        content_sections.append(preview)
                    
                    if 'xml_structure' in file_data and file_data['xml_structure']:
                        content_sections.append("**Document Structure:** Available")
                        xml_files = list(file_data['xml_structure'].keys())
                        if 'error' in xml_files:
                            xml_files.remove('error')
                        content_sections.append(f"- XML Components: {', '.join(xml_files)}")
                    
                    if 'form_data' in file_data and file_data['form_data']:
                        content_sections.append("**PDF Analysis:**")
                        if 'document_info' in file_data['form_data']:
                            doc_info = file_data['form_data']['document_info']
                            content_sections.append(f"- Pages: {doc_info.get('page_count', 'unknown')}")
                            content_sections.append(f"- Encrypted: {doc_info.get('is_encrypted', False)}")
                            content_sections.append(f"- Has Form Fields: {doc_info.get('has_form_fields', False)}")
                        
                        if 'metadata' in file_data['form_data'] and file_data['form_data']['metadata']:
                            content_sections.append("- Metadata: Available")
                else:
                    # Legacy text data
                    preview = str(file_data)[:500] + "..." if len(str(file_data)) > 500 else str(file_data)
                    content_sections.append(preview)
                
                content_sections.append("")
        
        # Add summary
        total_items = len(server_files_data) + len(uploaded_files_data) + len([k for k in form_data.keys() if k not in ['page_type', 'page_title'] and form_data[k].strip()])
        content_sections.append("## Summary")
        content_sections.append("")
        content_sections.append(f"- **Server Reference Files:** {len(server_files_data)}")
        content_sections.append(f"- **Uploaded Documents:** {len(uploaded_files_data)}")
        content_sections.append(f"- **Form Fields Completed:** {len([k for k in form_data.keys() if k not in ['page_type', 'page_title'] and form_data[k].strip()])}")
        content_sections.append(f"- **Total Items Processed:** {total_items}")
        
        generated_content = "\n".join(content_sections)
        
        logger.info(f"No-call page processed successfully for: {page_name}")
        
        return jsonify({
            'success': True,
            'content': generated_content,
            'session_id': session_id,
            'page_type': 'no-call',
            'files_processed': list(uploaded_files_data.keys()),
            'server_files_loaded': list(server_files_data.keys()),
            'form_fields_received': [k for k in form_data.keys() if k not in ['page_type', 'page_title']]
        })
        
    except Exception as e:
        logger.error(f"Error in no-call page handler: {e}")
        return jsonify({'error': 'Error processing no-call page'}), 500

def handle_claude_call_page(page_name, form_data, uploaded_files_data, server_files_data, session_id, claude_client):
    """Handle Claude API pages (existing functionality)"""
    if not claude_client:
        return jsonify({'error': 'Claude API not available'}), 503
    
    try:
        # Build Claude prompt from form data, uploaded files, and server files
        claude_prompt, error = build_claude_prompt(form_data, uploaded_files_data, server_files_data)
        if error:
            return jsonify({'error': error}), 400
        
        # Call Claude API
        message = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": claude_prompt}
            ]
        )
        
        generated_content = message.content[0].text
        
        logger.info(f"Claude API successful for page: {page_name} - Session: {session_id}")
        
        return jsonify({
            'success': True,
            'content': generated_content,
            'session_id': session_id,
            'page_type': 'claude-call',
            'files_processed': list(uploaded_files_data.keys()),
            'server_files_loaded': list(server_files_data.keys()),
            'form_fields_received': [k for k in form_data.keys() if k != 'claude_prompt']
        })
        
    except Exception as e:
        logger.error(f"Claude API error for page {page_name}: {e}")
        return jsonify({'error': f'Error generating content: {str(e)}'}), 500
