"""
AI 辅助内容创作服务

提供智能写作助手功能，包括文章大纲生成、段落扩写、标题优化等

功能:
1. 文章大纲生成
2. 段落扩写/缩写
3. 标题优化建议
4. 关键词提取
5. 自动 SEO 优化
6. Meta 描述生成
7. 关键词密度分析
8. 可读性评分
9. 内部链接建议
"""

from datetime import datetime
from typing import Dict, Any, List


class AIWritingAssistant:
    """
    AI 写作助手
    
    提供智能化的内容创作辅助功能
    """

    def __init__(self):
        self.generation_history: List[Dict[str, Any]] = []

    async def generate_article_outline(
            self,
            topic: str,
            target_audience: str = "general",
            article_length: str = "medium",
            tone: str = "professional"
    ) -> Dict[str, Any]:
        """
        生成文章大纲
        
        Args:
            topic: 文章主题
            target_audience: 目标读者
            article_length: 文章长度 (short/medium/long)
            tone: 语气风格 (professional/casual/academic)
            
        Returns:
            文章大纲
        """
        # 根据长度确定章节数量
        length_config = {
            "short": {"sections": 3, "word_count": "800-1200"},
            "medium": {"sections": 5, "word_count": "1500-2000"},
            "long": {"sections": 8, "word_count": "3000+"}
        }

        config = length_config.get(article_length, length_config["medium"])

        # TODO: 集成 LLM API 生成大纲
        outline = {
            "title": f"{topic}：完整指南",
            "meta": {
                "target_audience": target_audience,
                "estimated_length": config["word_count"],
                "tone": tone,
                "sections_count": config["sections"]
            },
            "sections": [
                {
                    "heading": "引言",
                    "subheadings": [
                        "背景介绍",
                        "为什么这个话题重要",
                        "本文将要讨论的内容"
                    ],
                    "key_points": [
                        "吸引读者注意力",
                        "建立主题相关性",
                        "概述文章结构"
                    ]
                },
                {
                    "heading": "核心概念解析",
                    "subheadings": [
                        f"{topic}的定义",
                        "基本原理",
                        "关键术语解释"
                    ],
                    "key_points": [
                        "清晰定义核心概念",
                        "使用简单易懂的语言",
                        "提供实际示例"
                    ]
                },
                {
                    "heading": "实践步骤详解",
                    "subheadings": [
                        "第一步：准备工作",
                        "第二步：实施过程",
                        "第三步：验证结果"
                    ],
                    "key_points": [
                        "分步骤说明",
                        "每步提供具体操作",
                        "包含注意事项"
                    ]
                },
                {
                    "heading": "最佳实践与技巧",
                    "subheadings": [
                        "常见错误及避免方法",
                        "专家建议",
                        "效率提升技巧"
                    ],
                    "key_points": [
                        "分享实用经验",
                        "提供可操作的建议",
                        "引用权威来源"
                    ]
                },
                {
                    "heading": "总结与下一步",
                    "subheadings": [
                        "要点回顾",
                        "行动建议",
                        "延伸阅读推荐"
                    ],
                    "key_points": [
                        "强化核心观点",
                        "鼓励读者行动",
                        "提供额外资源"
                    ]
                }
            ],
            "seo_suggestions": {
                "primary_keyword": topic,
                "secondary_keywords": [
                    f"{topic}教程",
                    f"{topic}指南",
                    f"如何{topic}"
                ],
                "recommended_headings": [
                    f"{topic}入门",
                    f"{topic}进阶技巧",
                    f"{topic}常见问题"
                ]
            }
        }

        # 记录生成历史
        self.generation_history.append({
            "type": "outline",
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "result": outline
        })

        return outline

    async def expand_paragraph(
            self,
            text: str,
            expansion_ratio: float = 1.5,
            style: str = "detailed"
    ) -> Dict[str, Any]:
        """
        扩写段落
        
        Args:
            text: 原始文本
            expansion_ratio: 扩展比例 (1.0-3.0)
            style: 扩展风格 (detailed/examples/analytical)
            
        Returns:
            扩写后的文本
        """
        original_length = len(text)

        # TODO: 集成 LLM API 扩写
        expanded_text = f"""{text}

【扩展内容】

在此基础上，我们可以进一步深入探讨相关的细节和背景信息。通过添加具体的例子、数据支持和专业见解，使内容更加丰富和有说服力。

关键要点：
1. 补充相关背景和上下文
2. 提供实际案例和应用场景
3. 加入数据支撑和专家观点
4. 增强逻辑连贯性和可读性

这样的扩展不仅增加了内容的深度，也提升了读者的理解和参与度。
"""

        result = {
            "original": text,
            "expanded": expanded_text,
            "original_length": original_length,
            "expanded_length": len(expanded_text),
            "expansion_ratio": round(len(expanded_text) / max(original_length, 1), 2),
            "style": style
        }

        # 记录生成历史
        self.generation_history.append({
            "type": "expand",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result

    async def optimize_title(
            self,
            title: str,
            optimization_type: str = "all"
    ) -> Dict[str, Any]:
        """
        优化标题
        
        Args:
            title: 原始标题
            optimization_type: 优化类型 (seo/clickbait/professional/all)
            
        Returns:
            优化建议列表
        """
        suggestions = []

        # SEO 优化版本
        if optimization_type in ["seo", "all"]:
            suggestions.append({
                "type": "seo",
                "title": f"{title}：完整指南与实用技巧",
                "reason": "包含关键词，提高搜索引擎排名",
                "score": 85
            })

        # 吸引力优化版本
        if optimization_type in ["clickbait", "all"]:
            suggestions.append({
                "type": "engagement",
                "title": f"如何掌握{title}：10个专家级技巧",
                "reason": "数字和承诺提高点击率",
                "score": 90
            })

        # 专业优化版本
        if optimization_type in ["professional", "all"]:
            suggestions.append({
                "type": "professional",
                "title": f"{title}的系统化方法与最佳实践",
                "reason": "专业术语提升可信度",
                "score": 80
            })

        # 问题式标题
        suggestions.append({
            "type": "question",
            "title": f"什么是{title}？为什么它如此重要？",
            "reason": "问题形式引发好奇心",
            "score": 75
        })

        # 列表式标题
        suggestions.append({
            "type": "listicle",
            "title": f"{title}的7个关键要点（2024最新版）",
            "reason": "列表格式易于阅读，年份增加时效性",
            "score": 88
        })

        result = {
            "original": title,
            "suggestions": suggestions,
            "best_practices": [
                "标题长度控制在 50-60 字符",
                "包含主要关键词",
                "使用数字增加吸引力",
                "避免过度承诺",
                "保持真实性和相关性"
            ]
        }

        # 记录生成历史
        self.generation_history.append({
            "type": "title_optimization",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result

    async def extract_keywords(
            self,
            content: str,
            max_keywords: int = 10
    ) -> Dict[str, Any]:
        """
        提取关键词
        
        Args:
            content: 文章内容
            max_keywords: 最大关键词数量
            
        Returns:
            提取的关键词列表
        """
        # TODO: 集成 NLP 库进行关键词提取
        # 这里使用简化的实现

        words = content.split()
        word_freq = {}

        for word in words:
            word = word.lower().strip('.,!?;:\"\'')
            if len(word) > 2:  # 忽略短词
                word_freq[word] = word_freq.get(word, 0) + 1

        # 按频率排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        keywords = [
            {
                "keyword": word,
                "frequency": freq,
                "density": round(freq / len(words) * 100, 2)
            }
            for word, freq in sorted_words[:max_keywords]
        ]

        result = {
            "keywords": keywords,
            "total_words": len(words),
            "unique_words": len(word_freq),
            "top_keywords": [k["keyword"] for k in keywords[:5]]
        }

        # 记录生成历史
        self.generation_history.append({
            "type": "keyword_extraction",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result


class SEOAutoOptimizer:
    """
    自动 SEO 优化器
    
    提供自动化的 SEO 优化功能
    """

    def __init__(self):
        self.optimization_history: List[Dict[str, Any]] = []

    async def generate_meta_description(
            self,
            content: str,
            title: str = "",
            max_length: int = 160
    ) -> Dict[str, Any]:
        """
        生成 Meta 描述
        
        Args:
            content: 文章内容
            title: 文章标题
            max_length: 最大长度
            
        Returns:
            生成的 Meta 描述
        """
        # 提取文章开头作为基础
        sentences = content.split('。')
        excerpt = sentences[0] if sentences else content[:100]

        # 如果包含标题，优先使用
        if title and title in content:
            description = f"{title} - {excerpt[:80]}"
        else:
            description = excerpt[:max_length]

        # 确保不超过最大长度
        if len(description) > max_length:
            description = description[:max_length - 3] + "..."

        result = {
            "description": description,
            "length": len(description),
            "optimal": len(description) <= max_length,
            "recommendations": []
        }

        # 提供优化建议
        if len(description) < 120:
            result["recommendations"].append("描述过短，建议增加到 120-160 字符")
        elif len(description) > 160:
            result["recommendations"].append("描述过长，可能被搜索引擎截断")

        if not any(keyword in description.lower() for keyword in ["指南", "教程", "技巧"]):
            result["recommendations"].append("考虑添加行动号召词（如'学习'、'发现'、'掌握'）")

        # 记录优化历史
        self.optimization_history.append({
            "type": "meta_description",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result

    async def analyze_keyword_density(
            self,
            content: str,
            target_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        分析关键词密度
        
        Args:
            content: 文章内容
            target_keywords: 目标关键词列表
            
        Returns:
            关键词密度分析结果
        """
        words = content.lower().split()
        total_words = len(words)

        analysis = []

        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            count = content.lower().count(keyword_lower)
            density = (count / total_words * 100) if total_words > 0 else 0

            # 评估密度是否合适
            status = "optimal"
            if density < 0.5:
                status = "too_low"
            elif density > 3.0:
                status = "too_high"

            analysis.append({
                "keyword": keyword,
                "count": count,
                "density": round(density, 2),
                "status": status,
                "recommendation": self._get_density_recommendation(status, density)
            })

        result = {
            "total_words": total_words,
            "keywords_analysis": analysis,
            "overall_score": self._calculate_seo_score(analysis),
            "suggestions": self._generate_keyword_suggestions(analysis)
        }

        # 记录优化历史
        self.optimization_history.append({
            "type": "keyword_density",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result

    async def check_readability(
            self,
            content: str
    ) -> Dict[str, Any]:
        """
        检查可读性
        
        Args:
            content: 文章内容
            
        Returns:
            可读性评分和建议
        """
        sentences = [s for s in content.split('。') if s.strip()]
        paragraphs = [p for p in content.split('\n\n') if p.strip()]

        avg_sentence_length = len(content) / max(len(sentences), 1)
        avg_paragraph_length = len(content) / max(len(paragraphs), 1)

        # 计算可读性评分（简化版）
        score = 100

        # 句子长度惩罚
        if avg_sentence_length > 30:
            score -= 20
        elif avg_sentence_length > 20:
            score -= 10

        # 段落长度惩罚
        if avg_paragraph_length > 500:
            score -= 15
        elif avg_paragraph_length > 300:
            score -= 5

        # 确定等级
        if score >= 80:
            grade = "excellent"
        elif score >= 60:
            grade = "good"
        elif score >= 40:
            grade = "fair"
        else:
            grade = "needs_improvement"

        result = {
            "score": score,
            "grade": grade,
            "metrics": {
                "sentence_count": len(sentences),
                "paragraph_count": len(paragraphs),
                "avg_sentence_length": round(avg_sentence_length, 2),
                "avg_paragraph_length": round(avg_paragraph_length, 2),
                "total_characters": len(content)
            },
            "recommendations": self._generate_readability_recommendations(
                avg_sentence_length,
                avg_paragraph_length
            )
        }

        # 记录优化历史
        self.optimization_history.append({
            "type": "readability",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result

    async def suggest_internal_links(
            self,
            content: str,
            available_articles: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        建议内部链接
        
        Args:
            content: 文章内容
            available_articles: 可用文章列表
            
        Returns:
            内部链接建议
        """
        # TODO: 基于内容相似度推荐相关文章
        suggestions = []

        if available_articles:
            # 模拟推荐逻辑
            for article in available_articles[:5]:
                suggestions.append({
                    "article_id": article.get("id"),
                    "title": article.get("title"),
                    "url": f"/article/{article.get('id')}",
                    "relevance_score": 85,
                    "anchor_text_suggestion": article.get("title")
                })

        result = {
            "suggestions": suggestions,
            "total_available": len(available_articles) if available_articles else 0,
            "best_practices": [
                "每篇文章包含 3-5 个内部链接",
                "使用描述性的锚文本",
                "链接到相关内容",
                "避免过度链接",
                "定期检查链接有效性"
            ]
        }

        # 记录优化历史
        self.optimization_history.append({
            "type": "internal_links",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

        return result

    # ==================== 辅助方法 ====================

    def _get_density_recommendation(self, status: str, density: float) -> str:
        """获取密度建议"""
        if status == "too_low":
            return f"密度过低 ({density}%)，建议适当增加关键词使用"
        elif status == "too_high":
            return f"密度过高 ({density}%)，可能被视为关键词堆砌，建议减少"
        else:
            return f"密度适中 ({density}%)，符合 SEO 最佳实践"

    def _calculate_seo_score(self, analysis: List[Dict]) -> int:
        """计算整体 SEO 评分"""
        if not analysis:
            return 0

        scores = []
        for item in analysis:
            if item["status"] == "optimal":
                scores.append(100)
            elif item["status"] == "too_low":
                scores.append(60)
            else:
                scores.append(40)

        return int(sum(scores) / len(scores))

    def _generate_keyword_suggestions(self, analysis: List[Dict]) -> List[str]:
        """生成关键词优化建议"""
        suggestions = []

        for item in analysis:
            if item["status"] == "too_low":
                suggestions.append(f"增加关键词 \"{item['keyword']}\" 的使用频率")
            elif item["status"] == "too_high":
                suggestions.append(f"减少关键词 \"{item['keyword']}\" 的使用，避免堆砌")

        if not suggestions:
            suggestions.append("关键词密度整体良好")

        return suggestions

    def _generate_readability_recommendations(
            self,
            avg_sentence_length: float,
            avg_paragraph_length: float
    ) -> List[str]:
        """生成可读性建议"""
        recommendations = []

        if avg_sentence_length > 25:
            recommendations.append("句子过长，建议拆分为更短的句子以提高可读性")

        if avg_paragraph_length > 400:
            recommendations.append("段落过长，建议适当分段")

        if avg_sentence_length < 10:
            recommendations.append("句子过短，可以考虑合并相关句子")

        if not recommendations:
            recommendations.append("可读性良好，继续保持")

        return recommendations


# 全局实例
ai_writing_assistant = AIWritingAssistant()
seo_optimizer = SEOAutoOptimizer()
