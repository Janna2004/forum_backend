-- ========== 1 ==========
INSERT INTO interviews_codingproblem (
    number, title, description, difficulty, tags, companies, position_types, created_at, updated_at
) VALUES (
    'LC001',
    '两数之和',
    '给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值的那两个整数，并返回它们的数组下标。',
    'easy',
    '["数组", "哈希表"]',
    '["字节跳动", "腾讯"]',
    '["backend", "frontend"]',
    NOW(), NOW()
);
INSERT INTO interviews_codingexample (problem_id, input_data, output_data, explanation, `order`) VALUES
(1, 'nums = [2,7,11,15], target = 9', '[0,1]', '因为 nums[0] + nums[1] == 9 ，返回 [0, 1]', 1);

-- ========== 2 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC002', '两数相加', 
    '给你两个非空的链表，表示两个非负的整数。它们每位数字是按逆序存储的，每个节点只能存储一位数字。请将这两个数相加并以链表形式返回。', 
    'medium', '["链表", "数学"]', '["阿里巴巴", "谷歌"]', '["backend", "algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(2, 'l1 = [2,4,3], l2 = [5,6,4]', '[7,0,8]', '342 + 465 = 807', 1);

-- ========== 3 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC003', '无重复字符的最长子串', 
    '给定一个字符串 s，请你找出其中不含有重复字符的最长子串的长度。', 
    'medium', '["字符串", "滑动窗口"]', '["微软", "亚马逊"]', '["backend", "frontend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(3, 's = "abcabcbb"', '3', '最长子串是 "abc"，长度为 3', 1);

-- ========== 4 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC004', '寻找两个正序数组的中位数', 
    '给定两个大小分别为 m 和 n 的正序数组 nums1 和 nums2，请你找出这两个正序数组的中位数。', 
    'hard', '["数组", "二分查找"]', '["Google", "Facebook"]', '["algo", "data"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(4, 'nums1 = [1,3], nums2 = [2]', '2.0', '合并数组 [1,2,3] 中位数是 2', 1);

-- ========== 5 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC005', '最长回文子串', 
    '给你一个字符串 s，找到 s 中最长的回文子串。', 
    'medium', '["字符串", "动态规划"]', '["字节跳动"]', '["frontend", "algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(5, 's = "babad"', '"bab"', '"aba" 也是有效答案', 1);

-- ========== 6 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC006', 'Z 字形变换', 
    '将一个给定字符串根据给定的行数进行 Z 字形排列，然后逐行读取字符串。', 
    'medium', '["字符串"]', '["阿里巴巴"]', '["frontend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(6, 's = "PAYPALISHIRING", numRows = 3', '"PAHNAPLSIIGYIR"', '按 Z 字形排列后逐行读取', 1);

-- ========== 7 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC007', '整数反转', 
    '给你一个 32 位有符号整数 x，返回其反转后的结果，若溢出则返回 0。', 
    'easy', '["数学"]', '["腾讯"]', '["backend", "frontend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(7, 'x = 123', '321', '数字反转', 1);

-- ========== 8 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC008', '字符串转换整数 (atoi)', 
    '实现一个 myAtoi(string s) 函数，将字符串转换成整数。', 
    'medium', '["字符串"]', '["微软"]', '["backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(8, 's = "42"', '42', '转换为整数', 1);

-- ========== 9 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC009', '回文数', 
    '判断一个整数是否是回文数。', 
    'easy', '["数学"]', '["京东"]', '["backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(9, 'x = 121', 'true', '121 从左到右和从右到左读都是一样的', 1);

-- ========== 10 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC010', '正则表达式匹配', 
    '实现正则表达式匹配，支持 . 和 *。', 
    'hard', '["字符串", "动态规划"]', '["Google"]', '["algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(10, 's = "aa", p = "a*"', 'true', '"*" 匹配零个或多个前面的元素', 1);

-- ========== 11 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC011', '盛最多水的容器',
    '给你 n 个非负整数 a1, a2, ..., an，每个数代表坐标中的一个点 (i, ai)。画 n 条垂直线，使得两条线与 x 轴形成的容器可以容纳最多的水。',
    'medium', '["双指针", "贪心"]', '["美团", "字节跳动"]', '["algo", "backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(11, 'height = [1,8,6,2,5,4,8,3,7]', '49', '在第 2 根和第 9 根之间形成的容器容量最大', 1);

-- ========== 12 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC012', '整数转罗马数字',
    '将整数转换成罗马数字，输入保证在 1 到 3999 范围内。',
    'medium', '["字符串", "数学"]', '["百度"]', '["frontend", "pm"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(12, 'num = 1994', '"MCMXCIV"', '1994 = 1000 + 900 + 90 + 4', 1);

-- ========== 13 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC013', '罗马数字转整数',
    '将罗马数字转换为整数。',
    'easy', '["字符串", "数学"]', '["百度"]', '["frontend", "pm"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(13, '"LVIII"', '58', 'L=50, V=5, III=3', 1);

-- ========== 14 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC014', '最长公共前缀',
    '编写一个函数来查找字符串数组中的最长公共前缀。',
    'easy', '["字符串"]', '["华为"]', '["frontend", "pm"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(14, '["flower","flow","flight"]', '"fl"', '前三个字母中公共前缀为 "fl"', 1);

-- ========== 15 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC015', '三数之和',
    '给你一个包含 n 个整数的数组 nums，判断 nums 中是否存在三个元素 a, b, c 使得 a+b+c=0。',
    'medium', '["数组", "双指针"]', '["京东"]', '["backend", "algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(15, 'nums = [-1,0,1,2,-1,-4]', '[[-1,-1,2],[-1,0,1]]', '找到所有和为 0 的三元组', 1);

-- ========== 16 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC016', '最接近的三数之和',
    '给你一个包含 n 个整数的数组 nums 和一个目标值 target，找出三个整数，使它们的和与 target 最接近。',
    'medium', '["数组", "双指针"]', '["腾讯"]', '["backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(16, 'nums = [-1,2,1,-4], target = 1', '2', '最接近目标值 1 的三数和为 2', 1);

-- ========== 17 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC017', '电话号码的字母组合',
    '给定一个仅包含数字 2-9 的字符串，返回它能表示的所有字母组合。',
    'medium', '["回溯", "字符串"]', '["Google"]', '["frontend", "backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(17, '"23"', '["ad","ae","af","bd","be","bf","cd","ce","cf"]', '数字映射到电话按键字母', 1);

-- ========== 18 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC018', '四数之和',
    '给你一个整数数组 nums 和一个目标值 target，找出所有和为目标值的四元组。',
    'medium', '["数组", "双指针"]', '["字节跳动"]', '["algo", "backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(18, 'nums = [1,0,-1,0,-2,2], target = 0', '[[-2,-1,1,2],[-2,0,0,2],[-1,0,0,1]]', '所有不重复的四元组', 1);

-- ========== 19 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC019', '删除链表的倒数第 N 个结点',
    '给你一个链表，删除链表的倒数第 n 个节点，并且返回链表的头节点。',
    'medium', '["链表"]', '["腾讯"]', '["backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(19, 'head = [1,2,3,4,5], n = 2', '[1,2,3,5]', '删除倒数第 2 个节点', 1);

-- ========== 20 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC020', '有效的括号',
    '给定一个只包括 "(", ")", "{", "}", "[", "]" 的字符串，判断字符串是否有效。',
    'easy', '["栈"]', '["美团"]', '["frontend", "qa"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(20, '"()[]{}"', 'true', '所有括号均正确闭合', 1);

-- ========== 21 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC021', '合并两个有序链表',
    '将两个升序链表合并为一个新的升序链表并返回。',
    'easy', '["链表"]', '["百度"]', '["backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(21, 'l1 = [1,2,4], l2 = [1,3,4]', '[1,1,2,3,4,4]', '合并保持有序', 1);

-- ========== 22 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC022', '括号生成',
    '数字 n 代表生成括号的对数，返回所有可能且有效的括号组合。',
    'medium', '["回溯"]', '["Google"]', '["algo", "frontend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(22, 'n = 3', '["((()))","(()())","(())()","()(())","()()()"]', '回溯生成所有可能', 1);

-- ========== 23 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC023', '合并 K 个升序链表',
    '将 k 个升序链表合并为一个升序链表并返回。',
    'hard', '["链表", "堆"]', '["亚马逊"]', '["algo", "backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(23, 'lists = [[1,4,5],[1,3,4],[2,6]]', '[1,1,2,3,4,4,5,6]', '利用最小堆合并', 1);

-- ========== 24 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC024', '两两交换链表中的节点',
    '给你一个链表，两两交换其中相邻的节点，并返回链表的头节点。',
    'medium', '["链表"]', '["字节跳动"]', '["backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(24, 'head = [1,2,3,4]', '[2,1,4,3]', '两两交换相邻节点', 1);

-- ========== 25 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC025', 'K 个一组翻转链表',
    '给你一个链表，每 k 个节点一组进行翻转，请返回修改后的链表。',
    'hard', '["链表"]', '["微软"]', '["backend", "algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(25, 'head = [1,2,3,4,5], k = 2', '[2,1,4,3,5]', '每两个一组翻转', 1);

-- ========== 26 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC026', '删除有序数组中的重复项',
    '给你一个有序数组 nums，原地删除重复出现的元素，使得每个元素只出现一次，返回删除后数组的新长度。',
    'easy', '["数组"]', '["阿里巴巴"]', '["qa", "backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(26, 'nums = [1,1,2]', '2', '新数组长度为 2，内容为 [1,2]', 1);

-- ========== 27 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC027', '移除元素',
    '给你一个数组 nums 和一个值 val，移除所有数值等于 val 的元素，并返回移除后数组的新长度。',
    'easy', '["数组"]', '["京东"]', '["qa", "backend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(27, 'nums = [3,2,2,3], val = 3', '2', '新数组长度为 2，内容为 [2,2]', 1);

-- ========== 28 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC028', '实现 strStr()',
    '实现 strStr() 函数，在字符串 haystack 中找出 needle 第一次出现的下标。',
    'easy', '["字符串"]', '["华为"]', '["frontend"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(28, 'haystack = "hello", needle = "ll"', '2', '"ll" 第一次出现在索引 2', 1);

-- ========== 29 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC029', '两数相除',
    '给你两个整数，被除数 dividend 和除数 divisor，将两数相除，要求不使用乘法、除法和取余运算。',
    'medium', '["数学", "二分查找"]', '["阿里巴巴"]', '["backend", "algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(29, 'dividend = 10, divisor = 3', '3', '10 除以 3 得商 3', 1);

-- ========== 30 ==========
INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC030', '串联所有单词的子串',
    '给定一个字符串 s 和一个字符串数组 words，找出所有串联 words 中所有单词的子串的起始索引。',
    'hard', '["字符串", "哈希表"]', '["微软"]', '["backend", "algo"]', NOW(), NOW()
);
INSERT INTO interviews_codingexample VALUES
(30, 's = "barfoothefoobarman", words = ["foo","bar"]', '[0,9]', '子串 "barfoo" 从索引 0 开始，"foobar" 从索引 9 开始', 1);

