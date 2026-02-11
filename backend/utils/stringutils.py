# -*- coding: utf-8 -*-
"""
字符串处理工具函数
"""
import os
import re
import uuid
from hashlib import md5


def contains_non_ascii(text: str) -> bool:
    """
    检查字符串是否包含非ASCII字符（如中文）
    
    Args:
        text: 要检查的字符串
    
    Returns:
        bool: 如果包含非ASCII字符返回 True，否则返回 False
    """
    if not text:
        return False
    try:
        text.encode('ascii')
        return False
    except UnicodeEncodeError:
        return True


def sanitize_folder_name(folder_name: str) -> str:
    """
    将文件夹名称转换为英文（如果包含中文则使用MD5哈希）
    
    Args:
        folder_name: 原始文件夹名称
    
    Returns:
        str: 英文文件夹名称
    """
    if not folder_name:
        return "uploads"
    
    # 如果包含非ASCII字符，使用MD5哈希
    if contains_non_ascii(folder_name):
        folder_hash = md5(folder_name.encode('utf-8')).hexdigest()[:12]
        return f"folder_{folder_hash}"
    
    # 如果已经是ASCII，只保留字母、数字、下划线和连字符
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', folder_name)
    return sanitized or "uploads"


def sanitize_filename(filename: str) -> str:
    """
    将文件名转换为英文（如果包含中文则使用UUID + 扩展名）
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 英文文件名
    """
    if not filename:
        return f"{uuid.uuid4().hex[:16]}.jpg"
    
    # 提取扩展名
    file_ext = os.path.splitext(filename)[1].lower()
    if not file_ext:
        file_ext = ".jpg"
    
    # 提取文件名（不含扩展名）
    file_basename = os.path.basename(os.path.splitext(filename)[0])
    
    # 如果文件名包含非ASCII字符，使用UUID + 扩展名
    if contains_non_ascii(file_basename):
        return f"{uuid.uuid4().hex[:16]}{file_ext}"
    
    # 如果已经是ASCII，只保留字母、数字、下划线、连字符和点号
    sanitized_basename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file_basename)
    return f"{sanitized_basename}{file_ext}" if sanitized_basename else f"{uuid.uuid4().hex[:16]}{file_ext}"
