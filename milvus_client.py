import os
from pymilvus import MilvusClient, DataType
from dotenv import load_dotenv

# 加载.env配置
load_dotenv()

# Milvus 连接配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "imagevector2")
VECTOR_DIM = int(os.getenv("MILVUS_VECTOR_DIM", "1152"))


def create_milvus_collection(
    collection_name: str = None,
    host: str = None,
    port: str = None,
    vector_dim: int = None,
    auto_id: bool = False
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
    host = host or MILVUS_HOST
    port = port or MILVUS_PORT
    collection_name = collection_name or MILVUS_COLLECTION
    vector_dim = vector_dim or VECTOR_DIM
    
    # 确保端口是整数类型（MilvusClient 需要整数端口）
    port = int(port) if isinstance(port, str) else port
    
    # 打印连接信息用于调试
    print(f"[Milvus] 正在连接到 {host}:{port}")
    print(f"[Milvus] 配置值 - HOST: {MILVUS_HOST}, PORT: {MILVUS_PORT}")
    print(f"[Milvus] 实际参数 - host='{host}', port={port} (type: {type(port).__name__})")
    
    # 创建 MilvusClient 连接
    # 尝试使用 URI 格式，明确指定完整的连接地址
    # 对于 gRPC，MilvusClient 可能需要在内部转换为 URI
    uri = f"http://{host}:{port}"
    print(f"[Milvus] 使用 URI: {uri}")
    client = MilvusClient(uri=uri)
    
    # 检查 collection 是否存在
    collection_exists = client.has_collection(collection_name)
    
    if not collection_exists:
        # 3.1. 创建 Schema（根据官方文档：使用 MilvusClient.create_schema）
        schema = MilvusClient.create_schema(
            auto_id=auto_id,
            enable_dynamic_field=False
        )
        
        # 3.2. 添加字段到 Schema
        schema.add_field(field_name="doc_id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=vector_dim)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=9000)
        
        # 3.3. 准备索引参数（可选，但推荐在创建时设置）
        index_params = client.prepare_index_params()
        
        # 3.4. 为向量字段添加索引（使用 AUTOINDEX）
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="L2"
        )
        
        # 3.5. 创建 Collection（同时传入 schema 和 index_params）
        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        print(f"[Milvus] Collection '{collection_name}' 创建成功（包含索引）")
    else:
        print(f"[Milvus] Collection '{collection_name}' 已存在")
    
    # 尝试加载 collection
    try:
        client.load_collection(collection_name=collection_name)
        print(f"[Milvus] Collection '{collection_name}' 已加载")
    except Exception as load_err:
        # 如果加载失败且是因为没有索引，尝试创建索引
        error_msg = str(load_err).lower()
        if "index not found" in error_msg or "700" in error_msg:
            print(f"[Milvus] Collection '{collection_name}' 没有索引，正在创建索引...")
            try:
                # 为已存在的 collection 创建索引
                index_params = client.prepare_index_params()
                index_params.add_index(
                    field_name="vector",
                    index_type="AUTOINDEX",
                    metric_type="L2"
                )
                
                client.create_index(
                    collection_name=collection_name,
                    field_name="vector",
                    index_params=index_params
                )
                print(f"[Milvus] 为 Collection '{collection_name}' 的 vector 字段创建索引成功")
                
                # 索引创建后再次尝试加载
                client.load_collection(collection_name=collection_name)
                print(f"[Milvus] Collection '{collection_name}' 已加载")
            except Exception as index_err:
                print(f"[Milvus] 创建索引失败: {index_err}")
                # 不抛出异常，允许继续，但记录错误
        else:
            print(f"[Milvus] 加载 collection '{collection_name}' 警告: {load_err}")
    
    return client


def get_milvus_client(
    host: str = None,
    port: str = None
) -> MilvusClient:
    """
    获取 Milvus 客户端连接（不创建 collection）
    
    Args:
        host: Milvus 主机地址，默认使用环境变量 MILVUS_HOST
        port: Milvus 端口，默认使用环境变量 MILVUS_PORT
    
    Returns:
        MilvusClient: 已连接的客户端实例
    """
    host = host or MILVUS_HOST
    port = port or MILVUS_PORT
    # 确保端口是整数类型
    port = int(port) if isinstance(port, str) else port
    
    # 打印连接信息用于调试
    print(f"[Milvus] 正在连接到 {host}:{port}")
    
    # 使用 URI 格式，明确指定完整的连接地址
    uri = f"http://{host}:{port}"
    print(f"[Milvus] 使用 URI: {uri}")
    return MilvusClient(uri=uri)

