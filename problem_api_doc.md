# 题目接口API文档

## 概述

本文档描述了获取题库题目的相关接口。题库本身有类型区分，一个题库要么全是算法题，要么全是非算法题。题库的ID决定了应该返回什么类型的题目。

## 接口列表

### 1. 获取题库所有题目

**接口地址：** `GET /api/code/problem-banks/{problem_set_id}/problems/`

**功能描述：** 获取指定题库的所有题目，根据题库类型自动返回算法题或非算法题

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| difficulty | string | 否 | 难度：`Easy`、`Medium`、`Hard` |
| tags | array | 否 | 标签数组，支持多个标签 |

**请求示例：**
```bash
# 获取算法题库的题目（如：basic-algorithm）
GET /api/code/problem-banks/basic-algorithm/problems/

# 获取非算法题库的题目（如：non-algorithm-test）
GET /api/code/problem-banks/non-algorithm-test/problems/

# 获取简单难度的题目
GET /api/code/problem-banks/basic-algorithm/problems/?difficulty=Easy

# 获取包含特定标签的题目
GET /api/code/problem-banks/basic-algorithm/problems/?tags=数组&tags=哈希表
```

**算法题库响应示例：**
```json
{
  "success": true,
  "problem_bank": {
    "id": "basic-algorithm",
    "title": "算法题测试题库",
    "description": "包含各种算法题的测试题库",
    "category": "算法设计",
    "difficulty": "Medium",
    "problem_count": 1,
    "completed_count": 0,
    "completion_rate": 0.0,
    "tags": ["算法", "数据结构", "动态规划"],
    "color": "bg-blue-300",
    "is_algorithm": true
  },
  "problems": [
    {
      "id": "algo-001",
      "problem_set": "basic-algorithm",
      "problem_set_title": "算法题测试题库",
      "category": "算法设计",
      "title": "两数之和",
      "description": "给定一个整数数组 nums 和一个整数目标值 target...",
      "scenario": "在数组中查找两个数的和等于目标值",
      "difficulty": "Easy",
      "tags": ["数组", "哈希表"],
      "is_algorithm": true,
      "question": "请实现一个函数，找出数组中两个数的和等于目标值的下标。",
      "reference_answer": "使用哈希表存储已遍历的数字，时间复杂度O(n)",
      "analysis": "这是一道经典的哈希表应用题目",
      "test_cases": {
        "public": [
          {
            "id": 1,
            "name": "示例 1",
            "input": "[2,7,11,15]\n9",
            "expectedOutput": "[0,1]",
            "status": "pending",
            "actualOutput": "",
            "error": ""
          }
        ],
        "hidden": [
          {
            "id": 4,
            "name": "隐藏测试用例 1",
            "status": "pending"
          }
        ]
      },
      "constraints": {
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "array_length": "2 <= nums.length <= 10^4",
        "target_range": "-10^9 <= target <= 10^9"
      },
      "code_template": "def twoSum(nums, target):\n    # 在这里实现你的解决方案\n    pass",
      "knowledge_points": null,
      "scoring_criteria": null,
      "created_at": "2025-08-15T12:00:00Z",
      "updated_at": "2025-08-15T12:00:00Z"
    }
  ],
  "total": 1,
  "filters": {
    "difficulty": "Easy",
    "tags": ["数组"]
  }
}
```

**非算法题库响应示例：**
```json
{
  "success": true,
  "problem_bank": {
    "id": "non-algorithm-test",
    "title": "非算法题测试题库",
    "description": "包含各种非算法题的测试题库",
    "category": "后端开发",
    "difficulty": "Medium",
    "problem_count": 1,
    "completed_count": 0,
    "completion_rate": 0.0,
    "tags": ["Java", "Spring", "数据库"],
    "color": "bg-green-300",
    "is_algorithm": false
  },
  "problems": [
    {
      "id": "non-algo-001",
      "problem_set": "non-algorithm-test",
      "problem_set_title": "非算法题测试题库",
      "category": "后端开发",
      "title": "Spring Boot自动配置原理",
      "description": "请详细解释Spring Boot的自动配置机制是如何工作的。",
      "scenario": "面试中经常被问到的Spring Boot核心概念",
      "difficulty": "Medium",
      "tags": ["Spring Boot", "自动配置", "Java"],
      "is_algorithm": false,
      "question": "请详细解释Spring Boot的自动配置机制...",
      "reference_answer": "Spring Boot自动配置机制的核心原理...",
      "analysis": "这是Spring Boot的核心特性...",
      "test_cases": null,
      "constraints": null,
      "code_template": null,
      "knowledge_points": [
        "Spring Boot自动配置",
        "@EnableAutoConfiguration注解",
        "条件注解",
        "META-INF/spring.factories",
        "自定义自动配置"
      ],
      "scoring_criteria": {
        "excellent": {
          "score_range": [90, 100],
          "criteria": "能够详细解释自动配置的完整流程..."
        },
        "good": {
          "score_range": [70, 89],
          "criteria": "能够解释自动配置的基本原理..."
        }
      },
      "created_at": "2025-08-15T12:00:00Z",
      "updated_at": "2025-08-15T12:00:00Z"
    }
  ],
  "total": 1,
  "filters": {
    "difficulty": "Medium",
    "tags": ["Spring"]
  }
}
```

### 2. 获取单个题目详情

**接口地址：** `GET /api/code/problems/{problem_id}/`

**功能描述：** 获取单个题目的详细信息

**请求示例：**
```bash
GET /api/code/problems/algo-001/
GET /api/code/problems/non-algo-001/
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "algo-001",
    "title": "两数之和",
    "is_algorithm": true,
    "test_cases": {...},
    "constraints": {...},
    "code_template": "...",
    // ... 其他字段
  }
}
```

## 数据结构说明

### 算法题特有字段

- **test_cases**: 测试用例数据
  ```json
  {
    "public": [
      {
        "id": 1,
        "name": "示例 1",
        "input": "[2,7,11,15]\n9",
        "expectedOutput": "[0,1]",
        "status": "pending",
        "actualOutput": "",
        "error": ""
      }
    ],
    "hidden": [
      {
        "id": 4,
        "name": "隐藏测试用例 1",
        "status": "pending"
      }
    ]
  }
  ```

- **constraints**: 约束条件
  ```json
  {
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
    "array_length": "2 <= nums.length <= 10^4",
    "target_range": "-10^9 <= target <= 10^9"
  }
  ```

- **code_template**: 代码模板
  ```python
  def twoSum(nums, target):
      # 在这里实现你的解决方案
      pass
  ```

### 非算法题特有字段

- **knowledge_points**: 知识点数组
  ```json
  [
    "Spring Boot自动配置",
    "@EnableAutoConfiguration注解",
    "条件注解",
    "META-INF/spring.factories",
    "自定义自动配置"
  ]
  ```

- **scoring_criteria**: 评分标准
  ```json
  {
    "excellent": {
      "score_range": [90, 100],
      "criteria": "能够详细解释自动配置的完整流程..."
    },
    "good": {
      "score_range": [70, 89],
      "criteria": "能够解释自动配置的基本原理..."
    }
  }
  ```

## 设计说明

1. **题库类型决定题目类型**：题库的 `is_algorithm` 字段决定了该题库包含的题目类型
2. **自动过滤**：接口会根据题库类型自动过滤题目，无需额外参数
3. **统一接口**：使用同一个接口获取算法题和非算法题，简化前端调用
4. **保持兼容**：非算法题的答题评析接口保持不变

## 错误响应

```json
{
  "success": false,
  "error": "错误信息"
}
```

常见错误：
- `题库不存在`: 指定的题库ID不存在
- `题目不存在`: 指定的题目ID不存在
- `参数错误`: 请求参数格式错误
