# # Streamlit Frontend 


# import streamlit as st
# import requests

# st.title("Document Management System")
# st.write("Upload PDF files to the DMS backend.")

# uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

# if uploaded_file is not None:
#     st.info("Uploading file to backend...")
#     files = {"file": uploaded_file}
#     headers = {"X-User-ID": "streamlit_user"}
#     try:
#         response = requests.post("http://127.0.0.1:5000/upload", files=files, headers=headers)
#         if response.status_code == 200:
#             st.success("File uploaded and scanned successfully!")
#             st.json(response.json())
#         else:
#             st.error(f"Error: {response.json().get('error', 'Unknown error')}")
#             st.write(response.json())
#     except Exception as e:
#         st.error(f"Upload failed: {e}")

# st.write("---")
# st.subheader("Check Document Scan Status")

# doc_id = st.text_input("Enter Document ID")

# if st.button("Check Status") and doc_id:
#     try:
#         response = requests.get(f"http://127.0.0.1:5000/status/{doc_id}")
#         if response.status_code == 200:
#             st.success("Status fetched successfully!")
#             st.json(response.json())
#         else:
#             st.error(response.json().get("error", "Document not found"))
#     except Exception as e:
#         st.error(f"Status check failed: {e}")



import streamlit as st
import requests
import time

st.title("Document Management System")
st.write("Upload PDF files to the DMS backend.")

# Check backend health first
try:
    health_response = requests.get("http://127.0.0.1:5000/health", timeout=5)
    if health_response.status_code == 200:
        st.success("✅ Backend server is running")
        st.json(health_response.json())
    else:
        st.error("❌ Backend server responded with error")
except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to Flask backend. Make sure it's running on port 5000.")
    st.stop()
except Exception as e:
    st.error(f"❌ Backend health check failed: {e}")
    st.stop()

st.write("---")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Uploading file to backend...")
    
    files = {"file": uploaded_file}
    headers = {"X-User-ID": "streamlit_user"}
    
    try:
        with st.spinner("Uploading and scanning file..."):
            response = requests.post(
                "http://127.0.0.1:5000/upload", 
                files=files, 
                headers=headers,
                timeout=200  # 30 second timeout
            )
        
        if response.status_code == 200:
            st.success("✅ File uploaded and scanned successfully!")
            result = response.json()
            st.json(result)
            
            # Store document ID for later use
            if "document_id" in result:
                st.session_state.last_doc_id = result["document_id"]
                
        else:
            st.error(f"❌ Upload failed: {response.status_code}")
            if response.content:
                st.json(response.json())
                
    except requests.exceptions.Timeout:
        st.error("⏰ Upload timed out. File may be too large or server is busy.")
    except requests.exceptions.ConnectionError:
        st.error("🔌 Connection lost during upload. Check if Flask server is still running.")
    except Exception as e:
        st.error(f"❌ Upload failed: {str(e)}")

st.write("---")
st.subheader("Check Document Status")

# Auto-fill last document ID if available
default_doc_id = st.session_state.get("last_doc_id", "")
doc_id = st.text_input("Enter Document ID", value=default_doc_id)

if st.button("Check Status") and doc_id:
    try:
        with st.spinner("Checking status..."):
            response = requests.get(f"http://127.0.0.1:5000/status/{doc_id}", timeout=10)
        
        if response.status_code == 200:
            st.success("✅ Status retrieved successfully!")
            st.json(response.json())
        else:
            st.error("❌ " + response.json().get("error", "Document not found"))
            
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to Flask server for status check.")
    except Exception as e:
        st.error(f"❌ Status check failed: {str(e)}")
