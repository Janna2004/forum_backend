import requests
from rest_framework.views import APIView
from rest_framework.response import Response

class RunCodeView(APIView):
    def post(self, request):
        source_code = request.data.get("source_code")
        language_id = request.data.get("language_id")
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

        # 创建提交任务
        res = requests.post(submission_url, json=payload, headers=headers)
        token = res.json().get("token")

        # 查询运行结果
        result_url = f"{submission_url}/{token}"
        result = requests.get(result_url, headers=headers).json()

        return Response(result)
