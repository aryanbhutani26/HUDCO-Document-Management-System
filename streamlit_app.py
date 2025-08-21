

# # Streamlit Frontend - RAG Integrated Version
# import streamlit as st
# import requests
# import time
# import json

# # Page configuration
# st.set_page_config(
#     page_title="Document Management System",
#     page_icon="📄",
#     layout="wide"
# )

# st.title("📄 Document Management System with AI Search")
# st.write("Upload PDF files, process them for AI search, and query your documents using natural language.")

# # Backend URL
# BACKEND_URL = "http://127.0.0.1:5000"

# # Initialize session state
# if 'last_doc_id' not in st.session_state:
#     st.session_state.last_doc_id = ""
# if 'processed_docs' not in st.session_state:
#     st.session_state.processed_docs = []

# # Sidebar for navigation
# st.sidebar.title("Navigation")
# page = st.sidebar.selectbox("Choose a section:", [
#     "📤 Upload Document", 
#     "🔍 AI Search", 
#     "📋 Document List", 
#     "🔧 System Status"
# ])

# # Helper function to make API calls
# def make_api_call(method, endpoint, **kwargs):
#     """Helper function to make API calls with error handling"""
#     try:
#         url = f"{BACKEND_URL}{endpoint}"
#         headers = kwargs.get('headers', {})
#         headers.update({"X-User-ID": "streamlit_user"})
        
#         if method.upper() == "GET":
#             response = requests.get(url, headers=headers, timeout=kwargs.get('timeout', 30))
#         elif method.upper() == "POST":
#             if 'files' in kwargs:
#                 response = requests.post(url, files=kwargs['files'], headers=headers, timeout=kwargs.get('timeout', 200))
#             elif 'json' in kwargs:
#                 response = requests.post(url, json=kwargs['json'], headers=headers, timeout=kwargs.get('timeout', 120))
#             else:
#                 response = requests.post(url, headers=headers, timeout=kwargs.get('timeout', 30))
        
#         return response
    
#     except requests.exceptions.ConnectionError:
#         st.error("🔌 Cannot connect to backend server. Make sure Flask is running on port 5000.")
#         return None
#     except requests.exceptions.Timeout:
#         st.error("⏰ Request timed out. Server may be busy.")
#         return None
#     except Exception as e:
#         st.error(f"❌ Request failed: {str(e)}")
#         return None

# # System Status Check
# def check_backend_health():
#     """Check if backend is healthy"""
#     response = make_api_call("GET", "/health", timeout=5)
#     if response and response.status_code == 200:
#         return True, response.json()
#     return False, None

# # Main content based on selected page
# if page == "🔧 System Status":
#     st.header("System Status")
    
#     with st.spinner("Checking backend health..."):
#         is_healthy, health_data = check_backend_health()
    
#     if is_healthy:
#         st.success("✅ Backend server is running")
        
#         col1, col2 = st.columns(2)
#         with col1:
#             st.subheader("System Health")
#             st.json(health_data)
        
#         with col2:
#             st.subheader("RAG Status")
#             st.write(f"**RAG Enabled:** {'✅ Yes' if health_data.get('rag_enabled') else '❌ No'}")
#             st.write(f"**ClamAV DB Present:** {'✅ Yes' if health_data.get('clamav_db_present') else '❌ No'}")
#             st.write(f"**Status:** {health_data.get('status', 'Unknown')}")
#     else:
#         st.error("❌ Backend server is not responding")
#         st.stop()

# elif page == "📤 Upload Document":
#     st.header("Upload PDF Document")
    
#     # Check backend health first
#     with st.spinner("Checking system status..."):
#         is_healthy, _ = check_backend_health()
    
#     if not is_healthy:
#         st.error("❌ Backend not available. Please check system status.")
#         st.stop()
    
#     uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
#     if uploaded_file is not None:
#         st.info(f"📄 Selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
#         if st.button("🚀 Upload and Scan Document"):
#             files = {"file": uploaded_file}
            
#             with st.spinner("Uploading and scanning file..."):
#                 response = make_api_call("POST", "/upload", files=files, timeout=200)
            
#             if response and response.status_code == 200:
#                 st.success("✅ File uploaded and scanned successfully!")
#                 result = response.json()
                
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.subheader("Upload Result")
#                     st.json(result)
                
#                 with col2:
#                     st.subheader("Next Steps")
#                     if "document_id" in result:
#                         st.session_state.last_doc_id = result["document_id"]
#                         st.write(f"**Document ID:** `{result['document_id']}`")
#                         st.write("✅ Document is ready for AI processing!")
                        
#                         if st.button("🧠 Process for AI Search"):
#                             with st.spinner("Processing document for AI search..."):
#                                 proc_response = make_api_call("POST", f"/process-document/{result['document_id']}", timeout=300)
                            
#                             if proc_response and proc_response.status_code == 200:
#                                 st.success("✅ Document processed for AI search!")
#                                 proc_result = proc_response.json()
#                                 st.json(proc_result)
                                
#                                 # Add to processed docs list
#                                 if result['document_id'] not in st.session_state.processed_docs:
#                                     st.session_state.processed_docs.append(result['document_id'])
#                             else:
#                                 st.error("❌ AI processing failed")
#                                 if proc_response:
#                                     st.json(proc_response.json())
            
#             elif response:
#                 st.error(f"❌ Upload failed: {response.status_code}")
#                 error_data = response.json()
#                 st.json(error_data)
                
#                 if "hint" in error_data:
#                     st.info(f"💡 Hint: {error_data['hint']}")

# elif page == "📋 Document List":
#     st.header("Document Library")
    
#     if st.button("🔄 Refresh List"):
#         response = make_api_call("GET", "/documents")
        
#         if response and response.status_code == 200:
#             data = response.json()
#             documents = data.get('documents', [])
            
#             if documents:
#                 st.success(f"Found {data.get('total_count', 0)} documents ({data.get('processed_count', 0)} processed for AI)")
                
#                 # Create a nice table view
#                 for doc in documents:
#                     with st.expander(f"📄 {doc['filename']} {'🧠' if doc['is_processed'] else '⏳'}"):
#                         col1, col2, col3 = st.columns(3)
                        
#                         with col1:
#                             st.write(f"**ID:** `{doc['id']}`")
#                             st.write(f"**Size:** {doc['file_size']} bytes")
#                             st.write(f"**Status:** {doc['scan_status']}")
                        
#                         with col2:
#                             st.write(f"**AI Ready:** {'✅ Yes' if doc['is_processed'] else '❌ No'}")
#                             st.write(f"**Uploaded:** {doc['created_at'][:19] if doc['created_at'] else 'N/A'}")
#                             if doc['processed_at']:
#                                 st.write(f"**Processed:** {doc['processed_at'][:19]}")
                        
#                         with col3:
#                             if not doc['is_processed'] and doc['scan_status'] == 'clean':
#                                 if st.button(f"🧠 Process for AI", key=f"process_{doc['id']}"):
#                                     with st.spinner("Processing..."):
#                                         proc_response = make_api_call("POST", f"/process-document/{doc['id']}")
#                                     if proc_response and proc_response.status_code == 200:
#                                         st.success("✅ Processed!")
#                                         st.rerun()
#                             elif doc['is_processed']:
#                                 st.success("✅ Ready for AI queries")
#             else:
#                 st.info("No documents found. Upload some PDFs first!")
#         else:
#             st.error("❌ Failed to fetch document list")

# elif page == "🔍 AI Search":
#     st.header("AI-Powered Document Search")
    
#     # Tab for different search types
#     tab1, tab2 = st.tabs(["🌐 Search All Documents", "📄 Search Specific Document"])
    
#     with tab1:
#         st.subheader("Search Across All Processed Documents")
        
#         user_query = st.text_area(
#             "Enter your question:",
#             placeholder="e.g., What are the main findings in the research papers?",
#             height=100
#         )
        
#         col1, col2 = st.columns([3, 1])
#         with col1:
#             search_all = st.button("🔍 Search All Documents", type="primary")
#         with col2:
#             if st.button("📋 Show Available Docs"):
#                 response = make_api_call("GET", "/documents")
#                 if response and response.status_code == 200:
#                     docs = response.json().get('documents', [])
#                     processed_docs = [d for d in docs if d['is_processed']]
#                     if processed_docs:
#                         st.info(f"📊 {len(processed_docs)} documents ready for search")
#                         for doc in processed_docs[:5]:  # Show first 5
#                             st.write(f"• {doc['filename']}")
#                     else:
#                         st.warning("No documents processed for AI search yet")
        
#         if search_all and user_query.strip():
#             if len(user_query) > 500:
#                 st.error("❌ Query too long (max 500 characters)")
#             elif len(user_query) < 3:
#                 st.error("❌ Query too short (min 3 characters)")
#             else:
#                 with st.spinner("🧠 AI is searching through your documents..."):
#                     response = make_api_call("POST", "/query", json={"query": user_query})
                
#                 if response and response.status_code == 200:
#                     result = response.json()
                    
#                     st.success("✅ Search completed!")
                    
#                     # Display answer
#                     st.subheader("📝 Answer")
#                     answer = result.get('answer', 'No answer returned.')
#                     st.write(answer)
                    
#                     # Display sources
#                     sources = result.get('sources', [])
#                     if sources:
#                         st.subheader("📚 Sources")
#                         for i, source in enumerate(sources, 1):
#                             similarity = source.get('similarity', 0)
#                             filename = source.get('filename', 'Unknown')
#                             st.write(f"{i}. **{filename}** (relevance: {similarity:.1%})")
                    
#                     # Show sanitized query if different
#                     original_query = user_query.strip()
#                     sanitized_query = result.get('query', '')
#                     if sanitized_query and sanitized_query != original_query:
#                         st.info(f"🔒 Query was sanitized for security: '{sanitized_query}'")
                        
#                 elif response:
#                     st.error("❌ Search failed")
#                     st.json(response.json())
    
#     with tab2:
#         st.subheader("Search Within a Specific Document")
        
#         col1, col2 = st.columns([2, 1])
#         with col1:
#             specific_doc_id = st.text_input(
#                 "Document ID:", 
#                 value=st.session_state.last_doc_id,
#                 placeholder="Enter document ID"
#             )
#         with col2:
#             st.write("**Last uploaded:**")
#             if st.session_state.last_doc_id:
#                 st.code(st.session_state.last_doc_id)
#             else:
#                 st.write("None")
        
#         specific_query = st.text_area(
#             "Enter your question for this document:",
#             placeholder="e.g., What is the conclusion of this document?",
#             height=100
#         )
        
#         if st.button("🔍 Search This Document", type="primary") and specific_doc_id and specific_query:
#             if len(specific_query) > 500:
#                 st.error("❌ Query too long (max 500 characters)")
#             elif len(specific_query) < 3:
#                 st.error("❌ Query too short (min 3 characters)")
#             else:
#                 with st.spinner("🧠 AI is analyzing the specific document..."):
#                     response = make_api_call("POST", f"/query-document/{specific_doc_id}", json={"query": specific_query})
                
#                 if response and response.status_code == 200:
#                     result = response.json()
                    
#                     st.success("✅ Document search completed!")
                    
#                     # Display answer
#                     st.subheader("📝 Answer")
#                     answer = result.get('answer', 'No answer returned.')
#                     st.write(answer)
                    
#                     # Display sources
#                     sources = result.get('sources', [])
#                     if sources:
#                         st.subheader("📚 Sources")
#                         for i, source in enumerate(sources, 1):
#                             similarity = source.get('similarity', 0)
#                             filename = source.get('filename', 'Unknown')
#                             st.write(f"{i}. **{filename}** (relevance: {similarity:.1%})")
                            
#                 elif response:
#                     st.error("❌ Document search failed")
#                     error_data = response.json()
#                     st.json(error_data)
                    
#                     if response.status_code == 404:
#                         st.info("💡 Make sure the document ID is correct and the document has been processed for AI search.")

# # Footer
# st.markdown("---")
# st.markdown(
#     """
#     <div style='text-align: center; color: #666;'>
#         <p>📄 Document Management System with AI Search | Powered by Flask + Streamlit + Gemini AI</p>
#         <p>🔒 Secured with ClamAV scanning and prompt injection protection</p>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

# # Quick actions in sidebar
# st.sidebar.markdown("---")
# st.sidebar.subheader("Quick Actions")

# if st.sidebar.button("🏠 Reset Session"):
#     st.session_state.clear()
#     st.rerun()

# if st.sidebar.button("🔄 Check Backend"):
#     is_healthy, health_data = check_backend_health()
#     if is_healthy:
#         st.sidebar.success("✅ Backend OK")
#     else:
#         st.sidebar.error("❌ Backend Down")

# # Display current document ID in sidebar
# if st.session_state.last_doc_id:
#     st.sidebar.info(f"**Last Doc ID:**\n`{st.session_state.last_doc_id}`")

# # Instructions
# with st.sidebar.expander("📖 How to Use"):
#     st.write("""
#     1. **Upload**: Choose a PDF file and upload it
#     2. **Process**: Process the clean document for AI search
#     3. **Search**: Ask questions about your documents
#     4. **Review**: Check document status and manage your library
#     """)
# Streamlit Frontend - FIXED Version
import streamlit as st
import requests
import time
import json

# Page configuration
st.set_page_config(
    page_title="Document Management System",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Document Management System with AI Search")
st.write("Upload PDF files, process them for AI search, and query your documents using natural language.")

# Backend URL
BACKEND_URL = "http://127.0.0.1:5000"

# Initialize session state
if 'last_doc_id' not in st.session_state:
    st.session_state.last_doc_id = ""
if 'processed_docs' not in st.session_state:
    st.session_state.processed_docs = []
if 'auto_switch_to_search' not in st.session_state:
    st.session_state.auto_switch_to_search = False
if 'just_processed_doc' not in st.session_state:
    st.session_state.just_processed_doc = ""

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a section:", [
    "📤 Upload Document", 
    "🔍 AI Search", 
    "📋 Document List", 
    "🔧 System Status"
])

# Auto-switch to AI Search if document was just processed
if st.session_state.auto_switch_to_search and page != "🔍 AI Search":
    page = "🔍 AI Search"
    st.session_state.auto_switch_to_search = False

# Helper function to make API calls - FIXED FILE UPLOAD
def make_api_call(method, endpoint, **kwargs):
    """Helper function to make API calls with error handling"""
    try:
        url = f"{BACKEND_URL}{endpoint}"
        headers = kwargs.get('headers', {})
        headers.update({"X-User-ID": "streamlit_user"})
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=kwargs.get('timeout', 30))
        elif method.upper() == "POST":
            if 'files' in kwargs:
                # FIXED: Proper file upload format
                response = requests.post(url, files=kwargs['files'], headers=headers, timeout=kwargs.get('timeout', 200))
            elif 'json' in kwargs:
                response = requests.post(url, json=kwargs['json'], headers=headers, timeout=kwargs.get('timeout', 120))
            else:
                response = requests.post(url, headers=headers, timeout=kwargs.get('timeout', 30))
        
        return response
    
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend server. Make sure Flask is running on port 5000.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. Server may be busy.")
        return None
    except Exception as e:
        st.error(f"❌ Request failed: {str(e)}")
        return None

# System Status Check
def check_backend_health():
    """Check if backend is healthy"""
    response = make_api_call("GET", "/health", timeout=5)
    if response and response.status_code == 200:
        return True, response.json()
    return False, None

def process_document_for_rag(doc_id):
    """Process document for RAG and handle UI updates"""
    with st.spinner("🧠 Processing document for AI search... This may take a few moments."):
        proc_response = make_api_call("POST", f"/process-document/{doc_id}", timeout=300)
    
    if proc_response and proc_response.status_code == 200:
        st.success("✅ Document processed for AI search successfully!")
        proc_result = proc_response.json()
        
        # Show processing details
        with st.expander("📊 Processing Details"):
            st.json(proc_result)
        
        # Add to processed docs list
        if doc_id not in st.session_state.processed_docs:
            st.session_state.processed_docs.append(doc_id)
        
        st.session_state.just_processed_doc = doc_id
        
        # Show next steps
        st.info("🎉 **Your document is now ready for AI search!**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 **Search This Document Now**", type="primary", key="search_now_btn"):
                st.session_state.auto_switch_to_search = True
                st.session_state.last_doc_id = doc_id
                st.rerun()
        
        with col2:
            if st.button("📋 View All Documents", key="view_docs_btn"):
                st.session_state.auto_switch_to_search = False
                st.rerun()
        
        return True
    else:
        st.error("❌ AI processing failed")
        if proc_response:
            error_data = proc_response.json()
            st.json(error_data)
        return False

# Main content based on selected page
if page == "🔧 System Status":
    st.header("System Status")
    
    with st.spinner("Checking backend health..."):
        is_healthy, health_data = check_backend_health()
    
    if is_healthy:
        st.success("✅ Backend server is running")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("System Health")
            st.json(health_data)
        
        with col2:
            st.subheader("RAG Status")
            st.write(f"**RAG Enabled:** {'✅ Yes' if health_data.get('rag_enabled') else '❌ No'}")
            st.write(f"**ClamAV DB Present:** {'✅ Yes' if health_data.get('clamav_db_present') else '❌ No'}")
            st.write(f"**Status:** {health_data.get('status', 'Unknown')}")
    else:
        st.error("❌ Backend server is not responding")
        st.stop()

elif page == "📤 Upload Document":
    st.header("Upload PDF Document")
    
    # Check backend health first
    with st.spinner("Checking system status..."):
        is_healthy, _ = check_backend_health()
    
    if not is_healthy:
        st.error("❌ Backend not available. Please check system status.")
        st.stop()
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        st.info(f"📄 Selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Add auto-process option
        auto_process = st.checkbox("🧠 Automatically process for AI search after upload", value=True)
        
        if st.button("🚀 Upload and Scan Document"):
            # FIXED: Proper file format for Flask backend
            files = {
                "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
            }
            
            with st.spinner("Uploading and scanning file..."):
                response = make_api_call("POST", "/upload", files=files, timeout=200)
            
            if response and response.status_code == 200:
                st.success("✅ File uploaded and scanned successfully!")
                result = response.json()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Upload Result")
                    st.json(result)
                
                with col2:
                    st.subheader("Next Steps")
                    if "document_id" in result:
                        st.session_state.last_doc_id = result["document_id"]
                        st.write(f"**Document ID:** `{result['document_id']}`")
                        st.write("✅ Document is ready for AI processing!")
                
                # Auto-process or manual process
                if "document_id" in result:
                    doc_id = result["document_id"]
                    
                    if auto_process:
                        st.info("🔄 Auto-processing enabled. Processing document for AI search...")
                        process_document_for_rag(doc_id)
                    else:
                        if st.button("🧠 Process for AI Search", key="manual_process_btn"):
                            process_document_for_rag(doc_id)
            
            elif response:
                st.error(f"❌ Upload failed: {response.status_code}")
                error_data = response.json() if response.content else {"error": "No response content"}
                st.json(error_data)
                
                if "hint" in error_data:
                    st.info(f"💡 Hint: {error_data['hint']}")
            else:
                st.error("❌ Failed to get response from server")

elif page == "📋 Document List":
    st.header("Document Library")
    
    if st.button("🔄 Refresh List"):
        response = make_api_call("GET", "/documents")
        
        if response and response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            
            if documents:
                st.success(f"Found {data.get('total_count', 0)} documents ({data.get('processed_count', 0)} processed for AI)")
                
                # Create a nice table view
                for doc in documents:
                    with st.expander(f"📄 {doc['filename']} {'🧠' if doc['is_processed'] else '⏳'}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**ID:** `{doc['id']}`")
                            st.write(f"**Size:** {doc['file_size']} bytes")
                            st.write(f"**Status:** {doc['scan_status']}")
                        
                        with col2:
                            st.write(f"**AI Ready:** {'✅ Yes' if doc['is_processed'] else '❌ No'}")
                            st.write(f"**Uploaded:** {doc['created_at'][:19] if doc['created_at'] else 'N/A'}")
                            if doc['processed_at']:
                                st.write(f"**Processed:** {doc['processed_at'][:19]}")
                        
                        with col3:
                            if not doc['is_processed'] and doc['scan_status'] == 'clean':
                                if st.button(f"🧠 Process for AI", key=f"process_{doc['id']}"):
                                    if process_document_for_rag(doc['id']):
                                        st.rerun()
                            elif doc['is_processed']:
                                st.success("✅ Ready for AI queries")
                                if st.button(f"🔍 Search This Doc", key=f"search_{doc['id']}"):
                                    st.session_state.last_doc_id = doc['id']
                                    st.session_state.auto_switch_to_search = True
                                    st.rerun()
            else:
                st.info("No documents found. Upload some PDFs first!")
        else:
            st.error("❌ Failed to fetch document list")

elif page == "🔍 AI Search":
    st.header("AI-Powered Document Search")
    
    # Show notification if redirected after processing
    if st.session_state.just_processed_doc:
        st.success(f"🎉 Document `{st.session_state.just_processed_doc}` was just processed and is ready for search!")
        st.session_state.just_processed_doc = ""
    
    # Tab for different search types
    tab1, tab2 = st.tabs(["🌐 Search All Documents", "📄 Search Specific Document"])
    
    with tab1:
        st.subheader("Search Across All Processed Documents")
        
        user_query = st.text_area(
            "Enter your question:",
            placeholder="e.g., What are the main findings in the research papers?",
            height=100
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_all = st.button("🔍 Search All Documents", type="primary")
        with col2:
            if st.button("📋 Show Available Docs"):
                response = make_api_call("GET", "/documents")
                if response and response.status_code == 200:
                    docs = response.json().get('documents', [])
                    processed_docs = [d for d in docs if d['is_processed']]
                    if processed_docs:
                        st.info(f"📊 {len(processed_docs)} documents ready for search")
                        for doc in processed_docs[:5]:  # Show first 5
                            st.write(f"• {doc['filename']}")
                        if len(processed_docs) > 5:
                            st.write(f"... and {len(processed_docs) - 5} more")
                    else:
                        st.warning("No documents processed for AI search yet")
        
        if search_all and user_query.strip():
            if len(user_query) > 500:
                st.error("❌ Query too long (max 500 characters)")
            elif len(user_query) < 3:
                st.error("❌ Query too short (min 3 characters)")
            else:
                with st.spinner("🧠 AI is searching through your documents..."):
                    response = make_api_call("POST", "/query", json={"query": user_query})
                
                if response and response.status_code == 200:
                    result = response.json()
                    
                    st.success("✅ Search completed!")
                    
                    # Display answer
                    st.subheader("📝 Answer")
                    answer = result.get('answer', 'No answer returned.')
                    st.write(answer)
                    
                    # Display sources
                    sources = result.get('sources', [])
                    if sources:
                        st.subheader("📚 Sources")
                        for i, source in enumerate(sources, 1):
                            similarity = source.get('similarity', 0)
                            filename = source.get('filename', 'Unknown')
                            st.write(f"{i}. **{filename}** (relevance: {similarity:.1%})")
                    
                    # Show sanitized query if different
                    original_query = user_query.strip()
                    sanitized_query = result.get('query', '')
                    if sanitized_query and sanitized_query != original_query:
                        st.info(f"🔒 Query was sanitized for security: '{sanitized_query}'")
                        
                elif response:
                    st.error("❌ Search failed")
                    error_data = response.json() if response.content else {"error": "No response content"}
                    st.json(error_data)
    
    with tab2:
        st.subheader("Search Within a Specific Document")
        
        # Pre-fill with last document ID if auto-switched
        default_doc_id = st.session_state.last_doc_id
        
        col1, col2 = st.columns([2, 1])
        with col1:
            specific_doc_id = st.text_input(
                "Document ID:", 
                value=default_doc_id,
                placeholder="Enter document ID",
                key="specific_doc_search"
            )
        with col2:
            st.write("**Last uploaded:**")
            if st.session_state.last_doc_id:
                st.code(st.session_state.last_doc_id)
                if st.button("📋 Use Last Doc", key="use_last_doc"):
                    specific_doc_id = st.session_state.last_doc_id
                    st.rerun()
            else:
                st.write("None")
        
        # Check document status if ID is provided
        if specific_doc_id:
            with st.spinner("Checking document status..."):
                status_response = make_api_call("GET", f"/status/{specific_doc_id}")
                if status_response and status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('rag_processed'):
                        st.success(f"✅ Document is ready for AI search")
                    else:
                        st.warning("⚠️ Document needs to be processed for AI search first")
                        if st.button("🧠 Process This Document Now", key="process_before_search"):
                            if process_document_for_rag(specific_doc_id):
                                st.rerun()
                elif status_response and status_response.status_code == 404:
                    st.error("❌ Document not found")
        
        specific_query = st.text_area(
            "Enter your question for this document:",
            placeholder="e.g., What is the conclusion of this document?",
            height=100,
            key="specific_query_input"
        )
        
        if st.button("🔍 Search This Document", type="primary") and specific_doc_id and specific_query:
            if len(specific_query) > 500:
                st.error("❌ Query too long (max 500 characters)")
            elif len(specific_query) < 3:
                st.error("❌ Query too short (min 3 characters)")
            else:
                with st.spinner("🧠 AI is analyzing the specific document..."):
                    response = make_api_call("POST", f"/query-document/{specific_doc_id}", json={"query": specific_query})
                
                if response and response.status_code == 200:
                    result = response.json()
                    
                    st.success("✅ Document search completed!")
                    
                    # Display answer
                    st.subheader("📝 Answer")
                    answer = result.get('answer', 'No answer returned.')
                    st.write(answer)
                    
                    # Display sources
                    sources = result.get('sources', [])
                    if sources:
                        st.subheader("📚 Sources")
                        for i, source in enumerate(sources, 1):
                            similarity = source.get('similarity', 0)
                            filename = source.get('filename', 'Unknown')
                            st.write(f"{i}. **{filename}** (relevance: {similarity:.1%})")
                            
                elif response:
                    st.error("❌ Document search failed")
                    error_data = response.json() if response.content else {"error": "No response content"}
                    
                    # Enhanced error handling with suggestions
                    error_message = error_data.get("error", "Unknown error")
                    if "not processed" in error_message.lower():
                        st.error("🔄 **Document not processed yet**")
                        st.info("💡 You need to process this document for AI search first.")
                        
                        if st.button("🧠 Process Document Now", key="error_process_btn"):
                            if process_document_for_rag(specific_doc_id):
                                st.success("✅ Document processed! You can now search it.")
                    
                    elif "not found" in error_message.lower():
                        st.error("📄 **Document not found**")
                        st.info("💡 Please check the document ID or upload a new document.")
                    
                    else:
                        st.json(error_data)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>📄 Document Management System with AI Search | Powered by Flask + Streamlit + Gemini AI</p>
        <p>🔒 Secured with ClamAV scanning and prompt injection protection</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Quick actions in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Quick Actions")

if st.sidebar.button("🏠 Reset Session"):
    st.session_state.clear()
    st.rerun()

if st.sidebar.button("🔄 Check Backend"):
    is_healthy, health_data = check_backend_health()
    if is_healthy:
        st.sidebar.success("✅ Backend OK")
    else:
        st.sidebar.error("❌ Backend Down")

# Display current document ID in sidebar
if st.session_state.last_doc_id:
    st.sidebar.info(f"**Last Doc ID:**\n`{st.session_state.last_doc_id}`")

# Quick stats in sidebar
with st.sidebar.expander("📊 Quick Stats"):
    response = make_api_call("GET", "/documents", timeout=5)
    if response and response.status_code == 200:
        data = response.json()
        st.write(f"**Total Documents:** {data.get('total_count', 0)}")
        st.write(f"**AI-Ready:** {data.get('processed_count', 0)}")
    else:
        st.write("Unable to fetch stats")

# Instructions
with st.sidebar.expander("📖 How to Use"):
    st.write("""
    1. **Upload**: Choose a PDF file and upload it
    2. **Process**: Process the clean document for AI search (auto or manual)
    3. **Search**: Ask questions about your documents
    4. **Review**: Check document status and manage your library
    
    **Pro Tips:**
    - Enable auto-processing for seamless workflow
    - Use specific document search for focused queries
    - Check document library to see all processed files
    """)
