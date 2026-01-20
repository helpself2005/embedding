"""
中间件管理模块
负责配置和管理FastAPI应用的中间件
"""
from fastapi import FastAPI
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware


class MiddlewareManager:
    """中间件管理器"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    def configure_cors(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_credentials: bool = True,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None
    ) -> None:
        """
        配置CORS中间件
        
        Args:
            allow_origins: 允许的源，默认为["*"]
            allow_credentials: 是否允许凭据
            allow_methods: 允许的HTTP方法，默认为["*"]
            allow_headers: 允许的HTTP头，默认为["*"]
        """
        if allow_origins is None:
            allow_origins = ["*"]
        if allow_methods is None:
            allow_methods = ["*"]
        if allow_headers is None:
            allow_headers = ["*"]
            
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
        )
    
    def configure_default_middleware(self) -> None:
        """
        配置默认中间件
        """
        self.configure_cors()


def configure_middleware(app: FastAPI) -> None:
    """
    配置应用中间件
    
    Args:
        app: FastAPI应用实例
    """
    middleware_manager = MiddlewareManager(app)
    middleware_manager.configure_default_middleware() 
    