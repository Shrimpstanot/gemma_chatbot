import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

# Define the name of the pre-trained model used for generating text embeddings.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

def process_file_and_update_vector_store(file_path: str, conversation_id: int):
    """
    Processes a single document file (PDF or TXT) by extracting text,
    splitting it into chunks, generating embeddings, and updating
    the FAISS vector store for a specific conversation.
    """
    print(f"Processing file: {file_path} for conversation: {conversation_id}")

    # Select the appropriate document loader based on the file extension.
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith('.txt'):
        loader = TextLoader(file_path)
    else:
        print(f"Unsupported file type: {file_path}. Skipping.")
        return

    # Load the document content using the selected loader.
    documents = loader.load()

    # Split the loaded document into smaller, manageable text chunks for embedding.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    split_docs = text_splitter.split_documents(documents)

    # Initialize the embedding model to convert text chunks into numerical vectors.
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # Define the unique path where the vector store for this conversation is saved.
    vector_store_path = f"vector_stores/{conversation_id}"

    # Check if a vector store already exists for this conversation.
    if os.path.exists(vector_store_path):
        # If it exists, load the existing store and add the new document chunks to it.
        print("Existing vector store found. Merging new documents.")
        vector_store = FAISS.load_local(
            vector_store_path, 
            embeddings, 
            allow_dangerous_deserialization=True # Required for loading
        )
        vector_store.add_documents(split_docs)
    else:
        # If no store exists, create a new one from the current document chunks.
        print("No existing vector store found. Creating a new one.")
        vector_store = FAISS.from_documents(split_docs, embeddings)

    # Save the updated (or newly created) vector store back to disk.
    vector_store.save_local(vector_store_path)
    print(f"Vector store for conversation {conversation_id} updated successfully.")

async def query_vector_store(query: str, conversation_id: int) -> list:
    """
    Queries the FAISS vector store associated with a specific conversation
    to find and return document chunks relevant to the given query.
    """
    vector_store_path = f"vector_stores/{conversation_id}"
    print(f"Querying vector store for conversation: {conversation_id} with query: {query}")

    # Check if the vector store exists for the given conversation.
    if not os.path.exists(vector_store_path):
        print(f"No vector store found for conversation {conversation_id}. Skipping RAG.")
        return []
    
    try:
        # Initialize the embedding model (must be the same as used for indexing).
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
        # Load the FAISS vector store from disk.
        vector_store = FAISS.load_local(
            vector_store_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Perform a similarity search to retrieve the most relevant document chunks.
        results = vector_store.similarity_search(query, k=3) # Retrieve top 3 results
        print(f"Found {len(results)} relevant documents for query.")
        return results
    except Exception as e:
        print(f"Error querying vector store for conversation {conversation_id}: {e}")
        return []
