import time

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import sentence_transformers
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

embedding_model_dict = {
    "ernie-tiny": "nghuyong/ernie-3.0-nano-zh",
    "ernie-base": "nghuyong/ernie-3.0-base-zh",
    "text2vec": "GanymedeNil/text2vec-large-chinese",
    "text2vec2": "uer/sbert-base-chinese-nli",
    "text2vec3": "shibing624/text2vec-base-chinese",
    "gte-base-zh": "runtime/pretrained_models/gte-base-zh",
    "gte-large-zh": "runtime/pretrain_models/gte-large-zh"
}

EMBEDDING_MODEL = "gte-base-zh"
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print(f"[{formatted_time}]INFO 正在加载embedding模型，当前模型为:{EMBEDDING_MODEL}")
embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[EMBEDDING_MODEL], )
embeddings.client = sentence_transformers.SentenceTransformer(
    embeddings.model_name, device='cuda')

def make_db(text_path,persist_directory,chunk_size=500):
    '''

    :param text_path: 需要转换向量的文档路径
    :param persist_directory: 向量数据库持久化存储路径
    :param chunk_size: 文档切片长度

    '''
    raw_documents_logs = TextLoader(text_path, encoding='utf-8').load()
    #text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=20)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=10)
    documents_sanguo = text_splitter.split_documents(raw_documents_logs)
    print("documents_sanguo:",documents_sanguo)
    documents = documents_sanguo
    print("chunk_size:",chunk_size)
    print("documents nums:", documents.__len__())
    db = Chroma.from_documents(documents, embedding=embeddings,persist_directory=persist_directory)
    db.persist()


def search_in_db(persist_directory,query,k_lin=2):
    '''

    :param persist_directory: 需要进行搜索的向量数据库路径
    :param query: 你的问题
    :param k_lin: 查询最近的k个邻居
    :return: 返回这k个最相似的邻居
    '''
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    docs = db.similarity_search(query, k=k_lin)
    result = ""
    for doc in docs:
        # print("===")
        # print("metadata:", doc.metadata)
        # print("page_content:", doc.page_content)
        result += doc.page_content
    return result

if __name__ == '__main__':
    persist_directory = "data/chroma_database/database/生物"
    #make_db(text_path="logs/mp4_text.txt",persist_directory=persist_directory)
    #search_in_db(persist_directory,"怎么区分脊椎动物和无脊动物？？")
