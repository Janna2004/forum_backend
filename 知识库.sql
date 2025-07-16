INSERT INTO knowledge_base_knowledgebaseentry
(question, answer, category, difficulty_level, tags, company_name, position_type, created_at, updated_at)
VALUES
('请介绍一下Django的MVT架构模式？',
 'Django采用MVT（Model-View-Template）架构模式：1. Model：数据模型层，负责数据库操作 2. View：视图层，处理业务逻辑 3. Template：模板层，负责页面展示',
 'technical', 2, '["python", "django", "架构"]', '字节跳动', 'backend', NOW(), NOW()),

('React和Vue的区别是什么？你更倾向于使用哪个？',
 'React和Vue的主要区别：1. 学习曲线：Vue更简单易学 2. 生态系统：React更丰富 3. 灵活性：React更灵活 4. 性能：两者都很优秀',
 'technical', 2, '["react", "vue", "前端框架"]', '腾讯', 'frontend', NOW(), NOW()),

('你如何设计一个新产品的需求文档？',
 '需求文档应包括：目标用户、核心功能、用户流程、界面原型、技术可行性分析、上线计划等。',
 'project', 3, '["产品设计", "需求分析"]', '美团', 'pm', NOW(), NOW()),

('请描述测试用例的设计方法。',
 '常见测试用例设计方法有：等价类划分、边界值分析、因果图法、判定表法、场景法等。',
 'technical', 2, '["测试", "用例设计"]', '阿里巴巴', 'qa', NOW(), NOW()),

('什么是二分查找？时间复杂度是多少？',
 '二分查找是一种在有序数组中查找目标值的算法，时间复杂度为O(log n)。',
 'technical', 1, '["算法", "查找"]', '百度', 'algo', NOW(), NOW());