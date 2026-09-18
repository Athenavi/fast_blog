"""
翻译管理服务

功能：
1. 翻译字符串管理
2. 语言包管理
3. 翻译进度追踪
4. 自动翻译集成（可选）
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class TranslationService:
    """
    翻译管理服务

    参考 Transifex 和 Crowdin 的设计模式
    """

    def __init__(self, translations_dir: str = 'translations'):
        self.translations_dir = Path(translations_dir)
        self.translations_dir.mkdir(parents=True, exist_ok=True)

        # 支持的语言
        self.supported_locales = ['zh-CN', 'en', 'ar', 'he', 'ja', 'ko', 'fr', 'de', 'es']

    def _locale_file(self, locale: str) -> Path:
        """返回指定语言的翻译文件路径"""
        return self.translations_dir / f'{locale}.json'

    def _load_locale(self, locale: str) -> Optional[Dict]:
        """读取指定语言的翻译文件；文件缺失或内容损坏时返回 None"""
        locale_file = self._locale_file(locale)

        if not locale_file.is_file():
            return None

        try:
            with locale_file.open(encoding='utf-8') as stream:
                return json.load(stream)
        except (OSError, ValueError):
            return None

    def _save_locale(self, locale: str, translations: Dict) -> None:
        """写入指定语言的翻译文件"""
        with self._locale_file(locale).open('w', encoding='utf-8') as stream:
            json.dump(translations, stream, ensure_ascii=False, indent=2)

    def get_translation(self, locale: str, key: str, default: Optional[str] = None) -> str:
        """
        获取翻译

        Args:
            locale: 语言代码
            key: 翻译键
            default: 默认值

        Returns:
            翻译文本
        """
        translations = self._load_locale(locale)

        if translations is None:
            return default or key

        # 支持嵌套键（如 "header.title"）
        keys = key.split('.')
        value = translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default or key

            if value is None:
                return default or key

        return value if isinstance(value, str) else (default or key)

    def set_translation(self, locale: str, key: str, value: str):
        """
        设置翻译

        Args:
            locale: 语言代码
            key: 翻译键
            value: 翻译值
        """
        # 加载现有翻译
        translations = self._load_locale(locale) or {}

        # 支持嵌套键
        keys = key.split('.')
        current = translations

        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

        # 保存翻译
        self._save_locale(locale, translations)

    def get_all_translations(self, locale: str) -> Dict:
        """
        获取所有翻译

        Args:
            locale: 语言代码

        Returns:
            翻译字典
        """
        return self._load_locale(locale) or {}

    def get_translation_progress(self, source_locale: str = 'zh-CN') -> Dict[str, float]:
        """
        获取翻译进度

        Args:
            source_locale: 源语言

        Returns:
            各语言的翻译进度（百分比）
        """
        # 获取源语言的所有键
        source_translations = self._load_locale(source_locale)
        if source_translations is None:
            return {}

        source_keys = self._flatten_keys(source_translations)
        total_keys = len(source_keys)

        if total_keys == 0:
            return {}

        progress = {}

        for locale in self.supported_locales:
            if locale == source_locale:
                progress[locale] = 100.0
                continue

            translations = self._load_locale(locale)
            if translations is None:
                progress[locale] = 0.0
                continue

            translated_keys = self._flatten_keys(translations)
            translated_count = sum(1 for key in source_keys if key in translated_keys)

            progress[locale] = round((translated_count / total_keys) * 100, 2)

        return progress

    def _flatten_keys(self, d: Dict, parent_key: str = '', sep: str = '.') -> List[str]:
        """
        将嵌套字典展平为键列表
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_keys(v, new_key, sep=sep))
            else:
                items.append(new_key)
        return items

    def export_translations(self, format: str = 'json') -> bytes:
        """
        导出所有翻译

        Args:
            format: 导出格式 ('json', 'po', 'xlsx')

        Returns:
            导出的文件内容
        """
        if format == 'json':
            all_translations = {}

            for locale in self.supported_locales:
                translations = self._load_locale(locale)

                if translations is not None:
                    all_translations[locale] = translations

            return json.dumps(all_translations, ensure_ascii=False, indent=2).encode('utf-8')

        elif format == 'yaml':
            try:
                import yaml
                return yaml.dump(all_translations, allow_unicode=True, default_flow_style=False).encode('utf-8')
            except ImportError:
                raise ImportError("PyYAML not installed. Install with: pip install pyyaml")

        elif format == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['key', 'locale', 'value'])

            for locale, translations in all_translations.items():
                flat_translations = self._flatten_keys(translations)
                for key, value in flat_translations.items():
                    writer.writerow([key, locale, value])

            return output.getvalue().encode('utf-8')

        elif format == 'po':
            # GNU gettext PO format
            output_lines = []
            output_lines.append('# Translation file generated by FastBlog')
            output_lines.append(f'# Generated at: {datetime.now().isoformat()}')
            output_lines.append('')

            for locale, translations in all_translations.items():
                output_lines.append(f'# Language: {locale}')
                flat_translations = self._flatten_keys(translations)
                for key, value in flat_translations.items():
                    output_lines.append(f'msgctxt "{locale}"')
                    output_lines.append(f'msgid "{key}"')
                    output_lines.append(f'msgstr "{value}"')
                    output_lines.append('')

            return '\n'.join(output_lines).encode('utf-8')

        else:
            raise NotImplementedError(f"Format {format} not implemented. Supported formats: json, yaml, csv, po")

    def import_translations(self, locale: str, translations: Dict):
        """
        导入翻译

        Args:
            locale: 语言代码
            translations: 翻译字典
        """
        self._save_locale(locale, translations)

    def get_missing_translations(self, locale: str, source_locale: str = 'zh-CN') -> List[str]:
        """
        获取缺失的翻译

        Args:
            locale: 目标语言
            source_locale: 源语言

        Returns:
            缺失的翻译键列表
        """
        source_translations = self._load_locale(source_locale)
        target_translations = self._load_locale(locale)

        if source_translations is None or target_translations is None:
            return []

        source_keys = set(self._flatten_keys(source_translations))
        target_keys = set(self._flatten_keys(target_translations))

        return list(source_keys - target_keys)


# 全局实例
translation_service = TranslationService()
