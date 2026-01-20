"""
用于定义错误码和错误信息
"""


class MessageStatus:
    """错误码中文说明"""
    # 成功
    SUCCESS = "成功"
    FAIL = "失败"

    # 文件
    FILE_ERROR = "文件操作异常"

    


# 预定义的错误码,目前只在业务中使用，没有下沉到底层，后续需要下沉
class MessageCode:
    """错误码定义"""
    SUCCESS = 200
    FAIL = 201
    
    # 文件
    FILE_ERROR = 30000
