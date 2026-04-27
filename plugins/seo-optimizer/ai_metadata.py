"""
AI-Friendly 元数据服务

为文章内容生成语义标签、关键词提取、自动摘要等AI友好的元数据
"""

import re
from collections import Counter
from typing import Dict, List, Any


class AIMetadataService:
    """
    AI 元数据服务
    
    提供文章内容的智能分析功能,生成AI友好的元数据
    """

    def __init__(self):
        # 中文停用词表 (简化版)
        self.stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '他', '她', '它', '们', '那', '些', '什么', '怎么', '吗', '呢',
            '吧', '啊', '哦', '嗯', '这个', '那个', '这样', '那样', '这里', '那里'
        }

        # 常见技术关键词
        self.tech_keywords = {
            'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'fastapi', 'django', 'flask', 'nodejs', 'express',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'mysql', 'postgresql', 'mongodb', 'redis',
            'git', 'github', 'gitlab', 'ci/cd', 'devops',
            'machine learning', 'deep learning', 'ai', '人工智能',
            'blockchain', '区块链', 'web3', 'crypto',
            'frontend', 'backend', 'fullstack', '全栈'
        }

    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        从文章内容中提取关键词
        
        Args:
            content: 文章内容
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        if not content:
            return []

        # 清理文本
        text = self._clean_text(content)

        # 分词 (简化版:按空格和标点分割)
        words = re.findall(r'\b\w+\b', text.lower())

        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if word not in self.stopwords
               and len(word) > 2
        ]

        # 统计词频
        word_counts = Counter(filtered_words)

        # 获取最常见的词
        common_words = word_counts.most_common(max_keywords * 2)

        # 优先选择技术关键词
        keywords = []
        tech_keywords_found = []
        other_keywords = []

        for word, count in common_words:
            if word in self.tech_keywords:
                tech_keywords_found.append(word)
            else:
                other_keywords.append(word)

        # 组合结果:技术关键词优先
        keywords = tech_keywords_found[:max_keywords // 2] + other_keywords[:max_keywords - len(tech_keywords_found)]

        return keywords[:max_keywords]

    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        生成文章摘要
        
        Args:
            content: 文章内容
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        if not content:
            return ""

        # 清理文本
        text = self._clean_text(content)

        # 按句子分割
        sentences = re.split(r'[。！？.!?\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text[:max_length]

        # 取前几个句子组成摘要
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary += sentence + "。"
            else:
                break

        # 如果摘要太长,截断
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return summary

    def extract_semantic_tags(self, content: str, title: str = "") -> List[str]:
        """
        提取语义标签
        
        Args:
            content: 文章内容
            title: 文章标题
            
        Returns:
            语义标签列表
        """
        tags = set()

        # 从标题提取
        if title:
            title_tags = self._extract_topic_tags(title)
            tags.update(title_tags)

        # 从内容提取
        content_tags = self._extract_topic_tags(content)
        tags.update(content_tags)

        # 检测编程语言
        lang_tags = self._detect_programming_languages(content)
        tags.update(lang_tags)

        # 检测技术栈
        tech_tags = self._detect_tech_stack(content)
        tags.update(tech_tags)

        return list(tags)[:15]  # 最多15个标签

    def calculate_readability_score(self, content: str) -> Dict[str, Any]:
        """
        计算可读性评分
        
        Args:
            content: 文章内容
            
        Returns:
            可读性指标
        """
        if not content:
            return {"score": 0, "level": "unknown"}

        text = self._clean_text(content)

        # 基本统计
        char_count = len(text)
        word_count = len(re.findall(r'\b\w+\b', text))
        sentence_count = len(re.split(r'[。！？.!?\n]+', text))
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])

        # 平均句长
        avg_sentence_length = word_count / max(sentence_count, 1)

        # 计算可读性分数 (0-100)
        # 基于: 句长适中、段落分明
        score = 100

        # 句长惩罚
        if avg_sentence_length > 30:
            score -= 20
        elif avg_sentence_length > 20:
            score -= 10

        # 段落数奖励
        if paragraph_count > 5:
            score += 10

        # 长度适中奖励
        if 500 <= char_count <= 3000:
            score += 10

        score = max(0, min(100, score))

        # 确定难度级别
        if score >= 80:
            level = "easy"
        elif score >= 60:
            level = "medium"
        else:
            level = "hard"

        return {
            "score": score,
            "level": level,
            "char_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "avg_sentence_length": round(avg_sentence_length, 2)
        }

    def detect_content_type(self, content: str, title: str = "") -> str:
        """
        检测内容类型
        
        Args:
            content: 文章内容
            title: 文章标题
            
        Returns:
            内容类型: tutorial, article, news, review, opinion, other
        """
        text = (title + " " + content).lower()

        # 教程特征
        tutorial_keywords = ['教程', '指南', 'how to', 'tutorial', '入门', '步骤', 'step by step']
        if any(kw in text for kw in tutorial_keywords):
            return "tutorial"

        # 新闻特征
        news_keywords = ['新闻', '发布', 'announcement', 'news', '更新', 'update']
        if any(kw in text for kw in news_keywords):
            return "news"

        # 评论/观点
        opinion_keywords = ['观点', '看法', 'opinion', 'review', '评测', '对比']
        if any(kw in text for kw in opinion_keywords):
            return "opinion"

        # 默认文章类型
        return "article"

    def generate_ai_metadata(self, title: str, content: str, excerpt: str = "") -> Dict[str, Any]:
        """
        生成完整的 AI 友好元数据
        
        Args:
            title: 文章标题
            content: 文章内容
            excerpt: 文章摘要(可选)
            
        Returns:
            元数据字典
        """
        # 如果没有提供摘要,自动生成
        if not excerpt:
            excerpt = self.generate_summary(content, max_length=150)

        # 提取关键词
        keywords = self.extract_keywords(content, max_keywords=10)

        # 提取语义标签
        tags = self.extract_semantic_tags(content, title)

        # 计算可读性
        readability = self.calculate_readability_score(content)

        # 检测内容类型
        content_type = self.detect_content_type(content, title)

        # 估计阅读时间 (假设每分钟阅读 300 字)
        char_count = len(self._clean_text(content))
        reading_time_minutes = max(1, round(char_count / 300))

        metadata = {
            "title": title,
            "excerpt": excerpt,
            "keywords": keywords,
            "tags": tags,
            "content_type": content_type,
            "readability": readability,
            "reading_time_minutes": reading_time_minutes,
            "language": self._detect_language(content),
            "generated_at": None,  # 由调用方设置
            "ai_friendly": True
        }

        return metadata

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除 Markdown 标记
        text = re.sub(r'#+\s*', '', text)  # 标题
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # 粗体
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # 斜体
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # 链接
        text = re.sub(r'`{1,3}(.+?)`{1,3}', r'\1', text)  # 代码
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # 图片
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # 列表

        return text.strip()

    def _extract_topic_tags(self, text: str) -> List[str]:
        """从文本中提取主题标签"""
        # 查找大写字母开头的词组 (英文主题)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

        # 查找中文主题 (2-4字词)
        chinese_topics = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)

        topics = []
        for topic in capitalized + chinese_topics:
            if len(topic) >= 2 and topic.lower() not in self.stopwords:
                topics.append(topic)

        return list(set(topics))[:10]

    def _detect_programming_languages(self, content: str) -> List[str]:
        """检测编程语言"""
        languages = {
            'python': ['python', 'pip', 'pytorch', 'tensorflow'],
            'javascript': ['javascript', 'js', 'npm', 'node'],
            'typescript': ['typescript', 'ts', 'tsx'],
            'java': ['java', 'spring', 'jvm'],
            'go': ['golang', 'go language'],
            'rust': ['rust', 'cargo'],
            'cpp': ['c++', 'cpp'],
            'c': ['c language'],
        }

        detected = []
        content_lower = content.lower()

        for lang, keywords in languages.items():
            if any(kw in content_lower for kw in keywords):
                detected.append(lang)

        return detected

    def _detect_tech_stack(self, content: str) -> List[str]:
        """检测技术栈"""
        tech_stack = {
            'react': ['react', 'jsx', 'hooks'],
            'vue': ['vue', 'vuejs', 'vuex'],
            'angular': ['angular', 'ng'],
            'django': ['django', 'django-rest'],
            'flask': ['flask'],
            'fastapi': ['fastapi'],
            'docker': ['docker', 'container'],
            'kubernetes': ['kubernetes', 'k8s'],
            'aws': ['aws', 'amazon web services', 's3', 'ec2'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb'],
        }

        detected = []
        content_lower = content.lower()

        for tech, keywords in tech_stack.items():
            if any(kw in content_lower for kw in keywords):
                detected.append(tech)

        return detected

    def _detect_language(self, content: str) -> str:
        """检测语言"""
        # 简单检测:中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)

        if total_chars == 0:
            return "unknown"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "zh-CN"
        else:
            return "en"


# 全局服务实例
ai_metadata_service = AIMetadataService()


def generate_article_metadata(title: str, content: str, excerpt: str = "") -> Dict[str, Any]:
    """
    便捷函数:生成文章元数据
    
    Args:
        title: 文章标题
        content: 文章内容
        excerpt: 文章摘要
        
    Returns:
        AI友好的元数据字典
    """
    from datetime import datetime

    metadata = ai_metadata_service.generate_ai_metadata(title, content, excerpt)
    metadata["generated_at"] = datetime.now().isoformat()

    return metadata
