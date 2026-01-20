from fastapi import Request

def get_milvus_client(request: Request):

    return request.app.state.milvus_client