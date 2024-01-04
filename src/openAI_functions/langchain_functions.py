import os
from langchain.document_loaders import (PyPDFLoader, Docx2txtLoader, TextLoader)
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.callbacks import get_openai_callback

class DocBot:
    def __init__(self, pdf_path=None, docx_path=None, txt_path=None):
        self.pdf_path = pdf_path
        self.docx_path = docx_path
        self.txt_path = txt_path
        self.dosyalar = []
        self.chat_history = []
        
        os.environ["OPENAI_API_KEY"] = "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"
        
        self.load_documents()
        self.initialize_models()

    def load_documents(self):

        if self.pdf_path:
            pdf_loader = PyPDFLoader(self.pdf_path)
            self.dosyalar.extend(pdf_loader.load())

        if self.docx_path:
            docx_loader = Docx2txtLoader(self.docx_path)
            self.dosyalar.extend(docx_loader.load())

        if self.txt_path:
            txt_loader = TextLoader(self.txt_path)
            self.dosyalar.extend(txt_loader.load())

        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=10)
        self.dosyalar = (text_splitter.split_documents(self.dosyalar))
        print(type(self.dosyalar))
        print(len(self.dosyalar))
 
        print(self.dosyalar)
        
    def initialize_models(self):  
        dosyalar=self.dosyalar  
        print(dosyalar)
        vectordb = Chroma.from_documents(documents=str(dosyalar), embedding=OpenAIEmbeddings)
        vectordb.persist()
        self.pdf_qa = ConversationalRetrievalChain.from_llm(
            ChatOpenAI(temperature=0.5, model_name="gpt-3.5-turbo-16k-0613"),
            vectordb.as_retriever(search_kwargs={'k': 6}),
            return_source_documents=True,
            verbose=False
        )

    def process_query(self, query):
        if query:
            result = self.pdf_qa({"question": query, "chat_history": self.chat_history})
            self.chat_history.append((query, result["answer"]))

            return {
                "result": result["answer"],
                "total_tokens": result["total_tokens"],
                "total_cost": result["total_cost"]
            }
pdf_path = r"C:\Users\lenovo\Desktop\2309.03905v1.pdf"


doc_bot = DocBot(pdf_path)

# Example query executed automatically
initial_query = "What is ImageBind-LLM"
result = doc_bot.process_query(initial_query)
print(result)