# 代码题答案评析接口文档

## 接口概述

代码题答案评析接口用于批量评析用户提交的代码题答案，包括测试用例验证和AI智能评析。

## 接口信息

- **接口地址**: `POST /code/evaluate-code/`
- **认证方式**: 需要用户登录认证
- **Content-Type**: `application/json`

## 请求参数

### 请求体格式

```json
{
    "problem_answers": [
        {
            "problem_id": "algo-001",
            "source_code": "def twoSum(nums, target):\n    # 用户代码..."
        },
        {
            "problem_id": "algo-002", 
            "source_code": "class ListNode:\n    def __init__(self, val=0, next=None):\n        # 用户代码..."
        }
    ]
}
```

### 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| problem_answers | Array | 是 | 题目答案列表 |
| problem_answers[].problem_id | String | 是 | 题目ID |
| problem_answers[].source_code | String | 是 | 用户提交的源代码 |

## 响应格式

### 成功响应

```json
{
    "success": true,
    "data": [
        {
            "problem_id": "algo-001",
            "problem_title": "两数之和",
            "test_results": {
                "public_cases": [
                    {
                        "input": "[2,7,11,15]\n9",
                        "expected": "[0,1]",
                        "actual": "[0,1]",
                        "error": "",
                        "passed": true
                    }
                ],
                "hidden_cases": [
                    {
                        "input": "[1,2,3,4,5,6,7,8,9,10]\n15",
                        "expected": "[4,9]",
                        "actual": "[4,9]",
                        "error": "",
                        "passed": true
                    }
                ],
                "summary": {
                    "public_passed": 3,
                    "public_total": 3,
                    "hidden_passed": 3,
                    "hidden_total": 3
                }
            },
            "evaluation": {
                "score": 25,
                "test_analysis": "所有测试用例均通过，代码正确性良好",
                "strengths": "逻辑清晰，代码结构合理",
                "problems": "时间复杂度较高，可以使用哈希表优化",
                "suggestions": "建议使用哈希表将时间复杂度从O(n²)优化到O(n)"
            }
        }
    ]
}
```

### 失败响应

```json
{
    "success": false,
    "error": "错误信息"
}
```

## 响应字段说明

### test_results 字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| public_cases | Array | 公开测试用例结果 |
| hidden_cases | Array | 隐藏测试用例结果 |
| summary | Object | 测试结果汇总 |

### evaluation 字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| score | Integer | 总分（0-30分） |
| test_analysis | String | 测试分析 |
| strengths | String | 代码优点 |
| problems | String | 代码问题 |
| suggestions | String | 改进建议 |

## 评分标准

- **代码正确性** (0-10分): 基于测试用例通过情况
- **算法效率** (0-10分): 时间空间复杂度评估
- **代码质量** (0-10分): 可读性、规范性评估
- **总分** (0-30分): 三项评分之和

## 使用示例

### Python 示例

```python
import requests
import json

# 请求数据
data = {
    "problem_answers": [
        {
            "problem_id": "algo-001",
            "source_code": """
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""
        }
    ]
}

# 发送请求
response = requests.post(
    'http://localhost:8000/code/evaluate-code/',
    json=data,
    headers={'Authorization': 'Bearer your_token_here'}
)

# 处理响应
if response.status_code == 200:
    result = response.json()
    if result['success']:
        for problem_result in result['data']:
            print(f"题目: {problem_result['problem_title']}")
            print(f"总分: {problem_result['evaluation']['score']}/30")
            print(f"改进建议: {problem_result['evaluation']['suggestions']}")
    else:
        print(f"评析失败: {result['error']}")
else:
    print(f"请求失败: {response.status_code}")
```

### JavaScript 示例

```javascript
// 请求数据
const data = {
    problem_answers: [
        {
            problem_id: "algo-001",
            source_code: `
function twoSum(nums, target) {
    const seen = new Map();
    for (let i = 0; i < nums.length; i++) {
        const complement = target - nums[i];
        if (seen.has(complement)) {
            return [seen.get(complement), i];
        }
        seen.set(nums[i], i);
    }
    return [];
}
`
        }
    ]
};

// 发送请求
fetch('/code/evaluate-code/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer your_token_here'
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(result => {
    if (result.success) {
        result.data.forEach(problemResult => {
            console.log(`题目: ${problemResult.problem_title}`);
            console.log(`总分: ${problemResult.evaluation.score}/30`);
            console.log(`改进建议: ${problemResult.evaluation.suggestions}`);
        });
    } else {
        console.error(`评析失败: ${result.error}`);
    }
})
.catch(error => {
    console.error('请求失败:', error);
});
```

## 注意事项

1. **题目限制**: 仅支持算法题目（`is_algorithm=True`）
2. **代码格式**: 源代码应为完整的函数或类定义
3. **执行环境**: 代码在安全的沙箱环境中执行，有5秒超时限制
4. **批量处理**: 支持同时评析多道题目，减少LLM调用次数
5. **错误处理**: 如果某道题目不存在或格式错误，会跳过该题目继续处理其他题目

## 错误码说明

| 错误信息 | 说明 |
|----------|------|
| 缺少必需参数: problem_answers | 请求体中缺少problem_answers字段 |
| problem_answers 格式错误，应为字典列表 | problem_answers不是数组格式 |
| 每个答案必须包含 problem_id 和 source_code | 答案对象缺少必需字段 |
| problem_id 和 source_code 不能为空 | 必需字段为空 |
| 没有找到有效的算法题目 | 所有题目都不是算法题或不存在 |
| LLM调用失败 | AI评析服务暂时不可用 |
| 运行测试用例失败 | 代码执行出错 |

## 性能优化

1. **批量处理**: 一次请求可处理多道题目，减少网络开销
2. **LLM调用优化**: 合并多个题目的评析请求，减少AI调用次数
3. **缓存机制**: 相同代码的评析结果会被缓存
4. **异步处理**: 支持异步评析，避免长时间等待
