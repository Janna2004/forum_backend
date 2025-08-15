# 个性化路径推荐接口API文档

## 接口概述

个性化路径推荐接口基于用户的目标岗位信息，使用LLM智能推荐匹配的公司-岗位组合和题库，帮助用户制定个性化的职业发展路径。

## 接口详情

### 获取个性化推荐

**接口地址**: `GET /api/users/recommendations/`

**请求方式**: GET

**认证要求**: 需要JWT Token认证

**请求头**:
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**请求参数**: 无

**响应格式**: JSON

**成功响应示例**:
```json
{
  "success": true,
  "data": {
    "currentGoal": {
      "title": "前端开发工程师",
      "company": "字节跳动",
      "salary": "25-35K",
      "matchRate": 85
    },
    "recommendedCompanies": [
      {
        "name": "字节跳动",
        "matchRate": 85,
        "position": "前端开发工程师"
      },
      {
        "name": "阿里巴巴",
        "matchRate": 82,
        "position": "前端开发工程师"
      },
      {
        "name": "腾讯",
        "matchRate": 78,
        "position": "前端开发工程师"
      },
      {
        "name": "美团",
        "matchRate": 75,
        "position": "前端开发工程师"
      },
      {
        "name": "滴滴",
        "matchRate": 72,
        "position": "前端开发工程师"
      }
    ],
    "recommendedTopics": [
      {
        "name": "React高级特性",
        "difficulty": "困难",
        "matchRate": 90,
        "count": 150
      },
      {
        "name": "TypeScript实战",
        "difficulty": "中等",
        "matchRate": 88,
        "count": 120
      },
      {
        "name": "前端性能优化",
        "difficulty": "困难",
        "matchRate": 85,
        "count": 189
      },
      {
        "name": "Vue3生态",
        "difficulty": "中等",
        "matchRate": 82,
        "count": 167
      },
      {
        "name": "微前端架构",
        "difficulty": "困难",
        "matchRate": 80,
        "count": 98
      }
    ]
  }
}
```

**错误响应示例**:
```json
{
  "success": false,
  "error": "获取推荐失败: LLM服务暂时不可用"
}
```

## 字段说明

### currentGoal (当前目标)
- `title`: 目标岗位名称
- `company`: 目标公司名称
- `salary`: 期望薪资范围
- `matchRate`: 匹配度 (0-100)

### recommendedCompanies (推荐公司)
- `name`: 公司名称
- `matchRate`: 匹配度 (0-100)
- `position`: 推荐岗位名称

### recommendedTopics (推荐题库)
- `name`: 题库名称
- `difficulty`: 难度等级 (简单/中等/困难)
- `matchRate`: 匹配度 (0-100)
- `count`: 题目数量

## 前端调用示例

### JavaScript (axios)
```javascript
import axios from 'axios';

const getPersonalizedRecommendations = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/users/recommendations/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.data.success) {
      const recommendations = response.data.data;
      console.log('当前目标:', recommendations.currentGoal);
      console.log('推荐公司:', recommendations.recommendedCompanies);
      console.log('推荐题库:', recommendations.recommendedTopics);
      return recommendations;
    } else {
      console.error('获取推荐失败:', response.data.error);
    }
  } catch (error) {
    console.error('请求失败:', error);
  }
};

// 使用示例
getPersonalizedRecommendations().then(recommendations => {
  if (recommendations) {
    // 处理推荐数据
    displayRecommendations(recommendations);
  }
});
```

### Python (requests)
```python
import requests

def get_personalized_recommendations(token):
    url = 'http://localhost:8000/api/users/recommendations/'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if data['success']:
            recommendations = data['data']
            print('当前目标:', recommendations['currentGoal'])
            print('推荐公司:', recommendations['recommendedCompanies'])
            print('推荐题库:', recommendations['recommendedTopics'])
            return recommendations
        else:
            print('获取推荐失败:', data['error'])
            
    except requests.exceptions.RequestException as e:
        print('请求失败:', e)

# 使用示例
token = 'your_jwt_token_here'
recommendations = get_personalized_recommendations(token)
```

## 注意事项

1. **认证要求**: 接口需要有效的JWT Token，用户必须已登录
2. **数据来源**: 推荐基于用户的目标岗位信息，请确保用户已设置目标岗位
3. **LLM依赖**: 推荐结果依赖LLM服务，如果服务不可用会返回默认推荐
4. **匹配度**: 匹配度范围0-100，数值越高表示匹配度越高
5. **缓存建议**: 推荐结果可以适当缓存，避免频繁调用LLM服务

## 错误码说明

- `401 Unauthorized`: Token无效或已过期
- `500 Internal Server Error`: 服务器内部错误，通常是LLM服务不可用

## 更新日志

- v1.0.0: 初始版本，支持基础个性化推荐功能
