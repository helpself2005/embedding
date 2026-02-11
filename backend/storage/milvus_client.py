import os
import sys
import copy
from pathlib import Path

# 如果是直接运行此文件，添加项目根目录到 Python 路径
if __name__ == "__main__" or not any("backend" in p for p in sys.path):
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from pymilvus import MilvusClient, DataType
from dotenv import load_dotenv
from backend.core.configs import settings
from backend.core.logs.logger import logger


class MilvusDB:
    def __init__(self,
            ):
        self.host = settings.milvus_host
        self.port = int(settings.milvus_port)
        self.collection_name = settings.milvus_collection_name
        self.vector_dim = settings.milvus_vector_dim
        self.auto_id = settings.milvus_auto_id
        # self.init_milvus_db(host, port, collection_name, vector_dim, auto_id)


    def init_milvus_db(
        self,
        host: str = None,
        port: str = None,
        collection_name: str = None,
        vector_dim: int = None,
        auto_id: bool = None,
    ) -> MilvusClient:
        """
        创建 Milvus collection 的封装接口
        
        Args:
            collection_name: Collection 名称，默认使用环境变量 MILVUS_COLLECTION
            host: Milvus 主机地址，默认使用环境变量 MILVUS_HOST
            port: Milvus 端口，默认使用环境变量 MILVUS_PORT
            vector_dim: 向量维度，默认使用环境变量 MILVUS_VECTOR_DIM
            auto_id: 是否自动生成 ID，默认为 False
        
        Returns:
            MilvusClient: 已连接并创建好 collection 的客户端实例
            
        Raises:
            Exception: 连接或创建 collection 失败时抛出异常
        """
        # 使用传入参数或环境变量默认值
        host = host or self.host
        port = int(port or self.port)
        collection_name = collection_name or self.collection_name
        vector_dim = vector_dim or self.vector_dim
        auto_id = auto_id or self.auto_id
         
        # 创建 MilvusClient 连接
        milvus_uri = f"http://{host}:{port}"

        # 打印连接信息用于调试
        logger.info(f"[Milvus] 正在连接到 {milvus_uri}")

        self.client = MilvusClient(uri=milvus_uri)
        
        # 检查 collection 是否存在
        collection_exists = self.client.has_collection(collection_name)
        
        if not collection_exists:
            # 3.1. 创建 Schema（根据官方文档：使用 MilvusClient.create_schema）
            schema = MilvusClient.create_schema(
                enable_dynamic_field=True,
            )
            # 显式添加自增主键（注意：这里 auto_id 是字段属性，不是 schema 参数！）
            schema.add_field(
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True,
                auto_id=True  # 👈 关键：在字段级别设置 auto_id
            )

            # 3.2. 添加字段到 Schema
            schema.add_field(field_name="class_id", datatype=DataType.VARCHAR, max_length=1024)
            schema.add_field(field_name="class_name", datatype=DataType.VARCHAR, max_length=1024)
            schema.add_field(field_name="file_path", datatype=DataType.VARCHAR, max_length=1024)
            schema.add_field(field_name="file_description", datatype=DataType.VARCHAR, max_length=8192)  # 文件描述信息
            schema.add_field(field_name="file_url", datatype=DataType.VARCHAR, max_length=2048)  # 文件访问 URL
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=vector_dim)

            
            # 3.3. 准备索引参数（可选，但推荐在创建时设置）
            index_params = self.client.prepare_index_params()
            
            # 3.4. 为向量字段添加索引（使用 AUTOINDEX）
            index_params.add_index(
                field_name="vector",
                index_type="AUTOINDEX",
                metric_type="COSINE"
            )
            
            # 3.5. 创建 Collection（同时传入 schema 和 index_params）
            self.client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )
            logger.info(f"[Milvus] Collection '{collection_name}' 创建成功（包含索引）")
        else:
            logger.info(f"[Milvus] Collection '{collection_name}' 已存在")
    

        self.client.load_collection(collection_name=collection_name)
        print(f"[Milvus] Collection '{collection_name}' 已加载")
               
        # return self.client


    # 插入数据到 Milvus
    def insert_data(self, data, collection_name=None):
        collection_name = collection_name or self.collection_name
        result = self.client.insert(collection_name=collection_name, data=data)
        return result

    # 插入数据到 Milvus
    def search_data(self, data, top_k=5, cosine=0.25, collection_name=None):
        # 执行向量搜索
        collection_name = collection_name or self.collection_name
        results = self.client.search(
                collection_name=collection_name,
                data=[data],  # 查询向量列表
                limit=top_k,  # 返回 top_k 个结果
                output_fields=["class_name", "file_path", "file_description", "file_url"]  # 返回的字段
            )
        
        filtered_results = [
            [r for r in result if r["distance"] > 0.8]
            for result in results
        ]

          
        return filtered_results

    def delete_collection(self, collection_name: str = None) -> bool:
        """
        删除指定的 Milvus collection
        
        Args:
            collection_name: Collection 名称，如果为 None 则使用默认的 collection_name
        
        Returns:
            bool: 删除是否成功
        
        Raises:
            Exception: 删除 collection 失败时抛出异常
        """
        try:
            collection_name = collection_name or self.collection_name
            
            if not collection_name:
                logger.error("[Milvus] 删除 collection 失败: collection_name 不能为空")
                return False
            
            # 检查 collection 是否存在
            if not self.client.has_collection(collection_name):
                logger.warning(f"[Milvus] Collection '{collection_name}' 不存在，无需删除")
                return False
            
            # 如果 collection 已加载，先卸载
            try:
                self.client.release_collection(collection_name=collection_name)
                logger.info(f"[Milvus] Collection '{collection_name}' 已卸载")
            except Exception as e:
                logger.warning(f"[Milvus] 卸载 collection '{collection_name}' 时出现警告: {e}")
            
            # 删除 collection
            self.client.drop_collection(collection_name=collection_name)
            logger.info(f"[Milvus] Collection '{collection_name}' 删除成功")
            return True
            
        except Exception as e:
            logger.error(f"[Milvus] 删除 collection '{collection_name}' 失败: {e}")
            raise

def create_milvus_client(
    host: str = None,
    port: str = None,
    collection_name: str = None,
    vector_dim: int = None,
    auto_id: bool = None,
) -> MilvusClient:
    """
    获取 Milvus 客户端连接（不创建 collection）
    
    Args:
        host: Milvus 主机地址，默认使用环境变量 MILVUS_HOST
        port: Milvus 端口，默认使用环境变量 MILVUS_PORT
    
    Returns:
        MilvusClient: 已连接的客户端实例
    """
    milvus_client = MilvusDB()
    milvus_client.init_milvus_db(host, port, collection_name, vector_dim, auto_id)
    return milvus_client


if __name__ == "__main__":
    """
    主方法：删除名为 'imagesearch' 的 collection
    """
    try:
        # 创建 MilvusDB 实例
        milvus_db = MilvusDB()
        
        # 创建 MilvusClient 连接（仅连接，不创建 collection）
        milvus_uri = f"http://{milvus_db.host}:{milvus_db.port}"
        logger.info(f"[Milvus] 正在连接到 {milvus_uri}")
        milvus_db.client = MilvusClient(uri=milvus_uri)
        
        # 删除名为 'imagesearch' 的 collection
        collection_name = "product_image"
        logger.info(f"[Milvus] 准备删除 collection: {collection_name}")
        result = milvus_db.delete_collection(collection_name=collection_name)
        
        if result:
            print(f"✓ Collection '{collection_name}' 删除成功")
        else:
            print(f"✗ Collection '{collection_name}' 删除失败或不存在")
            
    except Exception as e:
        logger.exception(f"删除 collection 时发生错误: {e}")
        print(f"✗ 删除 collection 时发生错误: {e}")
