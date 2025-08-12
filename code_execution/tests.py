from django.urls import reverse
from rest_framework.test import APITestCase

class TestJudge0API(APITestCase):
    def test_run_code_python(self):
        url = '/code/run-code/'
        data = {
            "source_code": "print('Hello, Judge0!')",
            "language_id": 71,
            "stdin": ""
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('stdout', response.data)
        self.assertIn('Hello, Judge0!', response.data.get('stdout', ''))
# 测试judge0的api是否正常