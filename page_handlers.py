"""
Page handlers for Claude-call and no-call page types with selective content control
"""

import logging
import json
from flask import jsonify
from utils import truncate_text, count_form_fields

logger = logging.getLogger(__name__)

def get_content_preferences(form_data):
    """Parse content preferences from form data"""
    preferences = {
        'docx_text': form_data.get('include_docx_text', 'true').lower() == 'true',
        'docx_xml': form_data.get('include_docx_xml', 'false').lower() == 'true',
        'pdf_text': form_data.get('include_pdf_text', 'true').lower() == 'true',
        'pdf_forms': form_data.get('include_pdf_forms', 'false').lower() == 'true',
        'txt_content': form_data.get('include_txt_content', 'true').lower() == 'true'
    }
    return preferences

def build_claude_prompt(form_data, uploaded_files_data, server_files_data):
    """Build Claude prompt from form data, uploaded files, and server files with selective content"""
    
    # Get the custom prompt from the form
    custom_prompt = form_data.get('claude_prompt', '').strip()
    if not custom_prompt:
        return None, "No Claude prompt provided"
    
    # Get content preferences
    content_prefs = get_content_preferences(form_data)
    
    # Build the context sections
    context_sections = []
    
    # Add server files first (background/examples)
    if server_files_data:
        context_sections.append("=== SERVER REFERENCE FILES ===")
        for file_name, file_data in server_files_data.items():
            context_sections.append(f"\n--- {file_name.upper()} ---")
            
            if isinstance(file_data, dict):
                file_type = file_data.get('file_type', 'unknown')
                
                # Handle DOCX files
                if file_type == 'docx':
                    if content_prefs['docx_text'] and 'text_content' in file_data and file_data['text_content']:
                        context_sections.append("Text Content:")
                        context_sections.append(str(file_data['text_content']).strip())
                    
                    if content_prefs['docx_xml'] and 'xml_structure' in file_data and file_data['xml_structure']:
                        context_sections.append("\nDocument Structure (XML):")
                        xml_structure = file_data['xml_structure']
                        if isinstance(xml_structure, dict):
                            for xml_type, xml_content in xml_structure.items():
                                if xml_type != 'error' and xml_content:
                                    context_sections.append(f"{xml_type.upper()}:")
                                    xml_str = str(xml_content) if xml_content else ""
                                    if len(xml_str) > 2000:
                                        context_sections.append(xml_str[:2000] + "... [truncated]")
                                    else:
                                        context_sections.append(xml_str)
                
                # Handle PDF files
                elif file_type == 'pdf':
                    if content_prefs['pdf_text'] and 'text_content' in file_data and file_data['text_content']:
                        context_sections.append("Text Content:")
                        context_sections.append(str(file_data['text_content']).strip())
                    
                    if content_prefs['pdf_forms'] and 'form_data' in file_data and file_data['form_data']:
                        context_sections.append("\nPDF Form Data and Metadata:")
                        try:
                            form_data_str = json.dumps(file_data['form_data'], indent=2, default=str)
                            context_sections.append(form_data_str)
                        except Exception as e:
                            logger.warning(f"Could not serialize PDF form data: {e}")
                            context_sections.append(str(file_data['form_data']))
                
                # Handle TXT files
                elif file_type == 'txt':
                    if content_prefs['txt_content'] and 'text_content' in file_data and file_data['text_content']:
                        context_sections.append("Text Content:")
                        context_sections.append(str(file_data['text_content']).strip())
                
            else:
                # Legacy text-only data - always include for backward compatibility
                context_sections.append(str(file_data).strip())
    
    # Add form data (excluding the prompt itself and content preferences)
    excluded_keys = ['claude_prompt', 'page_type', 'page_title', 
                     'include_docx_text', 'include_docx_xml', 'include_pdf_text', 
                     'include_pdf_forms', 'include_txt_content']
    
    form_context = {}
    for key, value in form_data.items():
        if key not in excluded_keys and str(value).strip():
            form_context[key] = str(value).strip()
    
    if form_context:
        context_sections.append("\n=== FORM DATA ===")
        for key, value in form_context.items():
            clean_key = key.replace('_', ' ').title()
            context_sections.append(f"{clean_key}: {value}")
    
    # Add uploaded file contents
    if uploaded_files_data:
        for file_type, file_data in uploaded_files_data.items():
            if file_data:
                context_sections.append(f"\n=== UPLOADED {file_type.upper()} CONTENT ===")
                
                if isinstance(file_data, dict):
                    data_file_type = file_data.get('file_type', 'unknown')
                    
                    # Handle uploaded DOCX files
                    if data_file_type == 'docx':
                        if content_prefs['docx_text'] and 'text_content' in file_data and file_data['text_content']:
                            context_sections.append("Text Content:")
                            context_sections.append(str(file_data['text_content']).strip())
                        
                        if content_prefs['docx_xml'] and 'xml_structure' in file_data and file_data['xml_structure']:
                            context_sections.append("\nDocument Structure (XML):")
                            xml_structure = file_data['xml_structure']
                            if isinstance(xml_structure, dict):
                                for xml_type, xml_content in xml_structure.items():
                                    if xml_type != 'error' and xml_content:
                                        context_sections.append(f"{xml_type.upper()}:")
                                        xml_str = str(xml_content) if xml_content else ""
                                        if len(xml_str) > 2000:
                                            context_sections.append(xml_str[:2000] + "... [truncated]")
                                        else:
                                            context_sections.append(xml_str)
                    
                    # Handle uploaded PDF files
                    elif data_file_type == 'pdf':
                        if content_prefs['pdf_text'] and 'text_content' in file_data and file_data['text_content']:
                            context_sections.append("Text Content:")
                            context_sections.append(str(file_data['text_content']).strip())
                        
                        if content_prefs['pdf_forms'] and 'form_data' in file_data and file_data['form_data']:
                            context_sections.append("\nPDF Form Data and Metadata:")
                            try:
                                form_data_str = json.dumps(file_data['form_data'], indent=2, default=str)
                                context_sections.append(form_data_str)
                            except Exception as e:
                                logger.warning(f"Could not serialize PDF form data: {e}")
                                context_sections.append(str(file_data['form_data']))
                    
                    # Handle uploaded TXT files
                    elif data_file_type == 'txt':
                        if content_prefs['txt_content'] and 'text_content' in file_data and file_data['text_content']:
                            context_sections.append("Text Content:")
                            context_sections.append(str(file_data['text_content']).strip())
                    
                else:
                    # Legacy text-only data - always include for backward compatibility
                    context_sections.append(str(file_data).strip())
    
    # Ensure all items in context_sections are strings
    cleaned_sections = []
    for section in context_sections:
        if isinstance(section, str):
            cleaned_sections.append(section)
        else:
            cleaned_sections.append(str(section))
    
    # Combine everything
    if cleaned_sections:
        full_prompt = "\n".join(cleaned_sections) + "\n\n" + custom_prompt
    else:
        full_prompt = custom_prompt
    
    return full_prompt, None

def handle_no_call_page(page_name, form_data, uploaded_files_data, server_files_data, session_id):
    """Handle no-call pages that organize and display information without API calls"""
    try:
        logger.info(f"Processing no-call page: {page_name}")
        
        # Get content preferences
        content_prefs = get_content_preferences(form_data)
        
        # Build organized content from available data
        content_sections = []
        
        # Add page header
        page_title = form_data.get('page_title', page_name.replace('-', ' ').title())
        content_sections.append(f"# {page_title}")
        content_sections.append("")
        
        # Add content preferences summary
        content_sections.append("## Content Processing Settings")
        content_sections.append("")
        content_sections.append(f"- **DOCX Text Content:** {'Included' if content_prefs['docx_text'] else 'Excluded'}")
        content_sections.append(f"- **DOCX XML Structure:** {'Included' if content_prefs['docx_xml'] else 'Excluded'}")
        content_sections.append(f"- **PDF Text Content:** {'Included' if content_prefs['pdf_text'] else 'Excluded'}")
        content_sections.append(f"- **PDF Form Data:** {'Included' if content_prefs['pdf_forms'] else 'Excluded'}")
        content_sections.append(f"- **TXT Content:** {'Included' if content_prefs['txt_content'] else 'Excluded'}")
        content_sections.append("")
        
        # Add server reference files with selective content
        if server_files_data:
            content_sections.append("## Reference Materials")
            content_sections.append("")
            for file_name, file_data in server_files_data.items():
                content_sections.append(f"### {file_name.title()}")
                content_sections.append("")
                
                if isinstance(file_data, dict):
                    file_type = file_data.get('file_type', 'unknown')
                    content_sections.append(f"**File Type:** {file_type.upper()}")
                    
                    # Show what content types are available and included
                    available_content = []
                    included_content = []
                    
                    if 'text_content' in file_data and file_data['text_content']:
                        available_content.append("Text Content")
                        if ((file_type == 'docx' and content_prefs['docx_text']) or 
                            (file_type == 'pdf' and content_prefs['pdf_text']) or 
                            (file_type == 'txt' and content_prefs['txt_content'])):
                            included_content.append("Text Content")
                    
                    if file_type == 'docx' and 'xml_structure' in file_data and file_data['xml_structure']:
                        available_content.append("XML Structure")
                        if content_prefs['docx_xml']:
                            included_content.append("XML Structure")
                    
                    if file_type == 'pdf' and 'form_data' in file_data and file_data['form_data']:
                        available_content.append("Form Data")
                        if content_prefs['pdf_forms']:
                            included_content.append("Form Data")
                    
                    if available_content:
                        content_sections.append(f"**Available Content:** {', '.join(available_content)}")
                        content_sections.append(f"**Included Content:** {', '.join(included_content) if included_content else 'None'}")
                    
                    # Show preview of included content
                    if included_content and 'text_content' in file_data and file_data['text_content']:
                        if ((file_type == 'docx' and content_prefs['docx_text']) or 
                            (file_type == 'pdf' and content_prefs['pdf_text']) or 
                            (file_type == 'txt' and content_prefs['txt_content'])):
                            content_sections.append("**Text Content Preview:**")
                            preview = truncate_text(str(file_data['text_content']), 500)
                            content_sections.append(preview)
                else:
                    # Legacy text data
                    preview = truncate_text(str(file_data), 500)
                    content_sections.append(preview)
                
                content_sections.append("")
        
        # Add form data (excluding content preferences)
        if form_data:
            content_sections.append("## Submitted Information")
            content_sections.append("")
            excluded_keys = ['page_type', 'page_title', 'include_docx_text', 'include_docx_xml', 
                           'include_pdf_text', 'include_pdf_forms', 'include_txt_content']
            for key, value in form_data.items():
                if key not in excluded_keys and str(value).strip():
                    display_key = key.replace('_', ' ').title()
                    content_sections.append(f"**{display_key}:** {value}")
            content_sections.append("")
        
        # Add uploaded files with selective content
        if uploaded_files_data:
            content_sections.append("## Uploaded Documents")
            content_sections.append("")
            for file_type, file_data in uploaded_files_data.items():
                content_sections.append(f"### {file_type.title()}")
                content_sections.append("")
                
                if isinstance(file_data, dict):
                    data_file_type = file_data.get('file_type', 'unknown')
                    content_sections.append(f"**File Type:** {data_file_type.upper()}")
                    
                    # Show content processing status
                    if data_file_type == 'docx':
                        content_sections.append(f"**Text Content:** {'Processed' if content_prefs['docx_text'] else 'Skipped'}")
                        content_sections.append(f"**XML Structure:** {'Processed' if content_prefs['docx_xml'] else 'Skipped'}")
                    elif data_file_type == 'pdf':
                        content_sections.append(f"**Text Content:** {'Processed' if content_prefs['pdf_text'] else 'Skipped'}")
                        content_sections.append(f"**Form Data:** {'Processed' if content_prefs['pdf_forms'] else 'Skipped'}")
                    elif data_file_type == 'txt':
                        content_sections.append(f"**Content:** {'Processed' if content_prefs['txt_content'] else 'Skipped'}")
                    
                    # Show preview if content was processed
                    if 'text_content' in file_data and file_data['text_content']:
                        should_show_text = ((data_file_type == 'docx' and content_prefs['docx_text']) or 
                                          (data_file_type == 'pdf' and content_prefs['pdf_text']) or 
                                          (data_file_type == 'txt' and content_prefs['txt_content']))
                        if should_show_text:
                            content_sections.append("**Text Content Preview:**")
                            preview = truncate_text(str(file_data['text_content']), 500)
                            content_sections.append(preview)
                else:
                    # Legacy text data
                    preview = truncate_text(str(file_data), 500)
                    content_sections.append(preview)
                
                content_sections.append("")
        
        # Add summary
        total_items = len(server_files_data) + len(uploaded_files_data) + count_form_fields(form_data, exclude_keys=['page_type', 'page_title', 'include_docx_text', 'include_docx_xml', 'include_pdf_text', 'include_pdf_forms', 'include_txt_content'])
        content_sections.append("## Summary")
        content_sections.append("")
        content_sections.append(f"- **Server Reference Files:** {len(server_files_data)}")
        content_sections.append(f"- **Uploaded Documents:** {len(uploaded_files_data)}")
        content_sections.append(f"- **Form Fields Completed:** {count_form_fields(form_data, exclude_keys=['page_type', 'page_title', 'include_docx_text', 'include_docx_xml', 'include_pdf_text', 'include_pdf_forms', 'include_txt_content'])}")
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
            'form_fields_received': [k for k in form_data.keys() if k not in ['page_type', 'page_title']],
            'content_preferences': content_prefs
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
            model="claude-sonnet-4-20250514",
            max_tokens=5000,
            messages=[
                {"role": "user", "content": claude_prompt}
            ]
        )
        
        generated_content = message.content[0].text
        
        logger.info(f"Claude API successful for page: {page_name} - Session: {session_id}")
        
        # Get content preferences for response metadata
        content_prefs = get_content_preferences(form_data)
        
        return jsonify({
            'success': True,
            'content': generated_content,
            'session_id': session_id,
            'page_type': 'claude-call',
            'files_processed': list(uploaded_files_data.keys()),
            'server_files_loaded': list(server_files_data.keys()),
            'form_fields_received': [k for k in form_data.keys() if k != 'claude_prompt'],
            'content_preferences': content_prefs
        })
        
    except Exception as e:
        logger.error(f"Claude API error for page {page_name}: {e}")
        return jsonify({'error': f'Error generating content: {str(e)}'}), 500
