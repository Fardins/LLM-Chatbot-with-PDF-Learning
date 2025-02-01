import streamlit as st
import os
import time
import logging
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_chroma import Chroma
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Ensure necessary directories exist
if not os.path.exists('pdfFiles'):
    os.makedirs('pdfFiles')
if not os.path.exists('vectorDB'):
    os.makedirs('vectorDB')

# Initialize session state
if 'memory' not in st.session_state:
    st.session_state['memory'] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

if 'vectorstore' not in st.session_state:
    try:
        embedding_function = OllamaEmbeddings(model="llama2")
        st.session_state['vectorstore'] = Chroma(persist_directory='vectorDB', embedding_function=embedding_function)
    except Exception as e:
        logging.error(f"Error initializing vectorstore: {e}")

if 'llm' not in st.session_state:
    st.session_state['llm'] = Ollama(model="llama2")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# Application title
st.title("LLM Chatbot with PDF Learning")

# File uploader
uploaded_file = st.file_uploader("Upload a PDF file to enhance knowledge", type="pdf")

# Process uploaded file
if uploaded_file is not None:
    file_path = f'pdfFiles/{uploaded_file.name}'
    if not os.path.exists(file_path):
        with st.status("Processing PDF..."):
            bytes_data = uploaded_file.read()
            with open(file_path, 'wb') as f:
                f.write(bytes_data)

            loader = PyPDFLoader(file_path)
            data = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            all_splits = text_splitter.split_documents(data)

            try:
                st.session_state['vectorstore'] = Chroma.from_documents(documents=all_splits, embedding=OllamaEmbeddings(model="llama2"))
                st.success("PDF processed and ready for queries!")
            except Exception as e:
                logging.error(f"Error processing PDF: {e}")
                st.error(f"Error processing PDF: {e}")

# Display chat history
for message in st.session_state['chat_history']:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if user_input := st.chat_input("Ask me anything:"):
    st.session_state['chat_history'].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if 'vectorstore' in st.session_state:
                retriever = st.session_state['vectorstore'].as_retriever()
                qa_chain = RetrievalQA.from_chain_type(llm=st.session_state['llm'], chain_type="stuff", retriever=retriever)
                response = qa_chain.run(user_input)
            else:
                response = st.session_state['llm'](user_input)

            st.session_state['chat_history'].append({"role": "assistant", "content": response})
            st.markdown(response)