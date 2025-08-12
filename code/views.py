import requests
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class RunCodeView(APIView):
    def post(self, request):
        try:
            # 验证必需参数
            source_code = request.data.get("source_code")
            language_id = request.data.get("language_id")
            
            if not source_code:
                return Response({"error": "缺少必需参数: source_code"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not language_id:
                return Response({"error": "缺少必需参数: language_id"}, status=status.HTTP_400_BAD_REQUEST)
            
            stdin = request.data.get("stdin", "")

            submission_url = "https://judge0-ce.p.rapidapi.com/submissions"

            headers = {
                "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
                "x-rapidapi-key": "76720345bfmsha48b5d6bd12c910p1a4946jsn87edb9d8e75d",  # 用户提供的RapidAPI密钥
                "content-type": "application/json"
            }

            payload = {
                "source_code": source_code,
                "language_id": language_id,
                "stdin": stdin
            }

            logger.info(f"提交代码执行请求: language_id={language_id}")

            # 创建提交任务
            res = requests.post(submission_url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()  # 检查请求是否成功
            
            response_data = res.json()
            token = response_data.get("token")
            
            if not token:
                logger.error(f"API响应中没有token: {response_data}")
                return Response({"error": "API响应格式错误"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 查询运行结果
            result_url = f"{submission_url}/{token}"
            result_res = requests.get(result_url, headers=headers, timeout=30)
            result_res.raise_for_status()  # 检查请求是否成功
            result = result_res.json()

            logger.info(f"代码执行完成: token={token}")
            return Response(result)
            
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            return Response({"error": "请求超时，请稍后重试"}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return Response({"error": "请求失败", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return Response({"error": "发生未知错误", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
