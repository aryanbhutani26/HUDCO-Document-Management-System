
Set up the secure local pipeline

Validate user uploads to allow only permitted file types and sizes.

Use ClamAV to scan every file (especially PDFs) for malware before processing.

Parse PDFs after passing the malware scan.

Integrate pgvector for storing and retrieving document embeddings to support semantic search and AI-powered querying.

Get your Gemini API key from Google AI Studio

Register or sign in to Google AI Studio and generate an API key for Gemini (or whichever Google generative model you will use).

Implement the RAG workflow with strict grounding prompts

Combine retrieval (using semantic search powered by pgvector) and generation (with Gemini or other LLM).

Craft prompts that strictly instruct the model to reference only retrieved content, not hallucinate or guess.

Test with security controls

Confirm malware scanning with ClamAV is effective and triggers on threats.

Validate prompt injection defenses (e.g., sanitizing user inputs).

Ensure role/permission checks to protect document access.

Document your security measures for the internship presentation

Keep clear notes/screenshots of each security layer.

Document your rationale for defenses against malware, prompt injection, and unauthorized access.

Prepare a short, technical summary for your final report or demo.