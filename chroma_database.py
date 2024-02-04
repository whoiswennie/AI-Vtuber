from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import sentence_transformers
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding_model_dict = {
    "ernie-tiny": "nghuyong/ernie-3.0-nano-zh",
    "ernie-base": "nghuyong/ernie-3.0-base-zh",
    "text2vec": "GanymedeNil/text2vec-large-chinese",
    "text2vec2": "uer/sbert-base-chinese-nli",
    "text2vec3": "shibing624/text2vec-base-chinese",
    "gte-base-zh": "pretrained_models/gte-base-zh",
    "gte-large-zh": "pretrain/gte-large-zh"
}

EMBEDDING_MODEL = "gte-base-zh"
# 初始化 hugginFace 的 embeddings 对象
embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[EMBEDDING_MODEL], )
embeddings.client = sentence_transformers.SentenceTransformer(
    embeddings.model_name, device='cuda')

def make_db(text_path,persist_directory,chunk_size=500):
    # 读取原始文档
    raw_documents_logs = TextLoader(text_path, encoding='utf-8').load()
    # 分割文档
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    documents_sanguo = text_splitter.split_documents(raw_documents_logs)
    documents = documents_sanguo
    print("documents nums:", documents.__len__())
    # 生成向量（embedding）
    db = Chroma.from_documents(documents, embedding=embeddings,persist_directory=persist_directory)
    # 持久化
    db.persist()

def search_in_db(persist_directory,query,k_lin=2):
    # 检索
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    docs = db.similarity_search(query, k=k_lin)
    # 打印结果
    result = ""
    for doc in docs:
        # print("===")
        # print("metadata:", doc.metadata)
        # print("page_content:", doc.page_content)
        result += doc.page_content
    return result

if __name__ == '__main__':
    persist_directory = "chroma_database/database/geng"
    #make_db(text_path="logs/mp4_text.txt",persist_directory=persist_directory)
    search_in_db(persist_directory,"曹操盖饭是什么梗？")