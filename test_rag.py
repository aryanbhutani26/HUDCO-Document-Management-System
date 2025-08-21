# test_rag.py
def test_rag_pipeline():
    # Test document processing
    with open('test_document.pdf', 'rb') as f:
        result = rag_pipeline.process_document(f, 'test_document.pdf')
        print("Processing result:", result)
    
    # Test querying
    query_result = rag_pipeline.query_documents("What is the main topic of the document?")
    print("Query result:", query_result)

if __name__ == "__main__":
    test_rag_pipeline()
