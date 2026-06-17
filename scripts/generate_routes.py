"""
璺敱浠ｇ爜鐢熸垚鍣?鏍规嵁 routes.yaml 澹版槑鏂囦欢鑷姩鐢熸垚 Django Ninja 鍜?FastAPI 鐨勮矾鐢变唬鐮?
浣跨敤鏂规硶:
    python scripts/generate_routes.py

瀛愬懡浠?
    - generate-all: 鐢熸垚鎵€鏈変唬鐮侊紙榛樿锛?    - sync-to-django: 鍚屾 SQLAlchemy 妯″瀷鍒?Django ORM
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class RouteGenerator:
    """璺嚎浠ｇ爜鐢熸垚鍣?""

    # Module 鍚嶇О鍒?FastAPI 妯″潡璺緞鐨勬槧灏?    MODULE_MAPPING = {
        'articles': 'src.api.v1.articles',
        'blog': 'src.api.v1.blog',
        'media': 'src.api.v1.media',
        'category_management': 'src.api.v1.category_management',
        'user_management': 'src.api.v1.user_management',
        'dashboard': 'src.api.v1.dashboard',
        'admin_settings': 'src.api.v1.admin_settings',
        'users': 'src.api.v1.users',
        'notifications': 'src.api.v1.notifications',
        'backup': 'src.api.v1.backup',
        'misc': 'src.api.v1.misc',
        'home': 'src.api.v1.home',
        'category_ext': 'src.api.v1.category_ext',
        'comment_config': 'src.api.v1.comment_config',
        'user_settings': 'src.api.v1.user_settings',
    }

    def __init__(self, config_path: str = None):
        """
        初始化生成器

        Args:
            config_path: routes.yaml 配置文件路径（可选，不提供则仅从 models.yaml 加载模型）
        """
        self.project_root = Path(__file__).parent.parent

        # 鍔犺浇 routes.yaml 閰嶇疆锛堝彲閫夛級
        self.config_path = Path(config_path) if config_path else self.project_root / "config" / "routes.yaml"
        self.config = {}
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            print(f"宸插姞杞借矾鐢遍厤缃細{self.config_path}")
        else:
            print(f"鎻愮ず锛歳outes.yaml 涓嶅瓨鍦紙{self.config_path}锛夛紝浠呬娇鐢?models.yaml 涓殑閰嶇疆")

        # 鍔犺浇妯″瀷閰嶇疆锛坢odels.yaml锛?        self.models_config_path = self.project_root / "config" / "models.yaml"
        self.extra_models = {}
        if self.models_config_path.exists():
            with open(self.models_config_path, 'r', encoding='utf-8') as f:
                extra_config = yaml.safe_load(f)
                self.extra_models = extra_config.get('models', {})
                print(f"宸插姞杞芥ā鍨嬮厤缃細{len(self.extra_models)} 涓ā鍨?)

        # 璁剧疆妯℃澘鐩綍
        self.template_dir = self.project_root / "scripts" / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.jinja_env.filters['quote'] = lambda x: f"'{x}'"

        # 娉ㄥ唽鑷畾涔夎繃婊ゅ櫒
        import sys
        sys.path.insert(0, str(self.project_root))
        from scripts.jinja_filters import register_filters
        register_filters(self.jinja_env)

        # 鎻愬彇閰嶇疆淇℃伅
        self.api_version = self.config.get('api_version', 'v1')
        self.base_path = self.config.get('base_path', f'/api/{self.api_version}')
        # 鍚堝苟 models: routes.yaml 涓殑 + models.yaml 涓殑
        self.models = {**self.config.get('models', {}), **self.extra_models}
        self.endpoints = self.config.get('endpoints', [])
        self.generation_config = self.config.get('generation', {})

    def generate_all(self):
        """鐢熸垚鎵€鏈変唬鐮?""
        print("=" * 70)
        print("寮€濮嬬敓鎴愯矾鐢变唬鐮?..")
        print("=" * 70)
        print(f"\n閰嶇疆鏂囦欢锛歿self.config_path}")
        print(f"绔偣鏁伴噺锛歿len(self.endpoints)}")
        print(f"妯″瀷鏁伴噺锛歿len(self.models)}")

        # 1. 鐢熸垚 Django ORM Mixins锛堝凡浜嶸0.2娣樻卑锛?        # self._generate_orm_mixins()

        # 3. 鐢熸垚 FastAPI 璺敱
        self._generate_fastapi()

        # 4. 鐢熸垚 TypeScript 绫诲瀷鍜屽鎴风
        self._generate_typescript()

        # 5. 鐢熸垚 Shared SQLAlchemy Models
        self._generate_shared_models()

        # 6. 浼樺寲 SQLAlchemy 妯″瀷鐨勫鍏?        self._optimize_sqlalchemy_imports()

        # 7. 鑷姩鏍煎紡鍖栫敓鎴愮殑鏂囦欢
        self._format_generated_files()

        print("=" * 70)
        print("鉁?浠ｇ爜鐢熸垚瀹屾垚!")
        print("=" * 70)

    def _generate_orm_mixins(self):
        """鐢熸垚 Django ORM Mixin 鏂囦欢"""
        print("\n[1/4] 鐢熸垚 Django ORM Mixins...")

        from datetime import datetime
        output_path = self.project_root / "apps" / "generated" / "auto_orm.py"

        # 瀵煎叆 settings 浠ヨ幏鍙栬〃鍓嶇紑
        try:
            from src.setting import settings
            table_prefix = getattr(settings, 'db_table_prefix', '')
        except ImportError:
            table_prefix = ''

        # 涓嶅簲璇ョ敓鎴?Django ORM 鐨勬ā鍨嬪垪琛紙杩欎簺鏄函鍝嶅簲妯″瀷锛?        EXCLUDED_MODELS = {
            'ApiResponse',
            'PaginationInfo',
            'UserListResponse',
            'ArticleListResponse',
            'CategoryListResponse',
            'MediaListResponse',
            'CommentListResponse',
        }

        # 杩囨护鎺夋帓闄ょ殑妯″瀷锛屽苟涓烘瘡涓ā鍨嬭浆鎹?properties 涓?fields
        models_to_generate = {}
        for name, defn in self.models.items():
            if name not in EXCLUDED_MODELS:
                # 澶嶅埗涓€浠藉畾涔夛紝娣诲姞杞崲鍚庣殑 fields
                model_copy = defn.copy()
                properties = defn.get('properties', {})
                if properties:
                    # 浼犲叆妯″瀷鍚嶇О浠ユ娴嬭嚜寮曠敤
                    model_copy['fields'] = self._convert_properties_to_fields(properties, model_name=name)
                models_to_generate[name] = model_copy

        template_data = {
            'models': models_to_generate,
            'all_model_names': list(self.models.keys()),  # 浼犻€掓墍鏈夋ā鍨嬪悕绉帮紝鐢ㄤ簬妫€鏌ュ閿紩鐢?            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'table_prefix': table_prefix,  # 娣诲姞琛ㄥ墠缂€
        }

        content = self._render_template('django_orm_mixins.py.jinja2', template_data)
        self._write_file(output_path, content)
        print(f"  [OK] ORM Mixins: {output_path}")

    def _generate_fastapi(self):
        """鐢熸垚 FastAPI 璺敱鏂囦欢"""
        print("\n[3/4] 鐢熸垚 FastAPI 璺敱...")

        output_path = self._get_output_path('fastapi', 'router_file')
        if not output_path:
            print("  鈿?FastAPI 杈撳嚭璺緞鏈厤缃?)
            return

        # 鍑嗗妯℃澘鏁版嵁
        template_data = {
            'api_version': self.api_version,
            'base_path': self.base_path,
            'endpoints': self._filter_endpoints_by_module(),
            'models': self.models,
            'imports': self._collect_fastapi_imports(),
            'handler_mapping': self.config.get('handler_mapping', {}),
            'module_import_map': self.MODULE_MAPPING
        }

        # 娓叉煋妯℃澘
        content = self._render_template('fastapi_router.py.jinja2', template_data)

        # 鍚庡鐞嗭細淇鍙傛暟鏍煎紡闂
        import re
        # 鍦ㄩ€楀彿鍚庨潰娣诲姞鎹㈣绗﹀拰姝ｇ‘鐨勭缉杩涳紙褰撴娴嬪埌 Query/Form/Path 鏃讹級
        content = re.sub(r',\s*(page|per_page|search|category_id|user_id|status|article_id|slug|tag_name|name)\s*:',
                         r',\n        \1:', content)
        # 淇 request: Request锛屽悗闈㈢殑鍙傛暟
        content = re.sub(r'(request: Request,)\s*(\w+\s*:)', r'\1\n        \2', content)
        # 淇 db 鍙傛暟鍓嶇殑鏍煎紡
        content = re.sub(r'Query\(([^)]+)\),\s*(db: AsyncSession)', r'Query(\1),\n        \2', content)

        # 鍐欏叆鏂囦欢
        self._write_file(output_path, content)
        print(f"  [OK] FastAPI Router: {output_path}")

    def _generate_typescript(self):
        """鐢熸垚 TypeScript 绫诲瀷瀹氫箟鍜?API 瀹㈡埛绔?""
        print("\n[4/5] 鐢熸垚 TypeScript 绫诲瀷...")

        ts_config = self.generation_config.get('typescript', {})
        if not ts_config:
            print("  鈿?TypeScript 鐢熸垚鏈厤缃?)
            return

        output_dir = self.project_root / ts_config.get('output_dir', 'frontend-next/types/generated')
        output_dir.mkdir(parents=True, exist_ok=True)

        # 鐢熸垚绫诲瀷瀹氫箟
        types_file = output_dir / ts_config.get('types_file', 'api-types.ts')
        types_content = self._render_template('typescript_types.ts.jinja2', {
            'models': self.models,
            'endpoints': self.endpoints
        })
        self._write_file(types_file, types_content)
        print(f"  [OK] TypeScript Types: {types_file}")

        # 鐢熸垚 API 瀹㈡埛绔?        client_file = output_dir / ts_config.get('client_file', 'api-client.ts')
        client_content = self._render_template('typescript_client.ts.jinja2', {
            'endpoints': self.endpoints,
            'base_path': self.base_path
        })
        self._write_file(client_file, client_content)
        print(f"  [OK] TypeScript Client: {client_file}")

    def _generate_shared_models(self):
        """鐢熸垚 Shared SQLAlchemy 妯″瀷鏂囦欢锛堜粠 models[*].orm 璇诲彇閰嶇疆锛?""
        print("\n[5/5] 鐢熸垚 Shared SQLAlchemy Models...")

        # 瀵煎叆 settings 浠ヨ幏鍙栬〃鍓嶇紑
        try:
            from src.setting import settings
        except ImportError:
            settings = type('Settings', (), {'db_table_prefix': ''})()

        table_prefix = getattr(settings, 'db_table_prefix', '')

        # 鏀堕泦鎵€鏈夐渶瑕佺敓鎴?ORM 鐨勬ā鍨嬶紙orm: true锛?        orm_models = {}
        for model_name, model_def in self.models.items():
            if model_def.get('orm') is True:
                orm_models[model_name] = model_def

        if not orm_models:
            print("  鈿?娌℃湁闇€瑕佺敓鎴?ORM 鐨勬ā鍨嬶紝璺宠繃")
            return

        from datetime import datetime
        output_base = self.project_root / "shared" / "models"
        output_base.mkdir(parents=True, exist_ok=True)

        generated_count = 0
        success_models = []
        # 璁板綍浣跨敤浜嗗摢浜涘瓙妯″潡锛屼互渚垮悗缁垱寤?__init__.py
        used_modules = set()

        for model_name, model_def in orm_models.items():
            try:
                # 璇诲彇 module 灞炴€э紙鍙€夛級锛屽喅瀹氭ā鍨嬫枃浠剁殑瀛愮洰褰曚綅缃?                module_path = model_def.get('module', '').strip()
                if module_path:
                    # 瑙勮寖鍖栬矾寰勫垎闅旂锛堟敮鎸?"intel" 鎴?"intel/sub" 鏍煎紡锛?                    module_path = module_path.replace('\\', '/').strip('/')
                    used_modules.add(module_path)
                    output_dir = output_base / module_path
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = output_base

                # 姣忎釜妯″瀷鐢熸垚涓€涓崟鐙殑鏂囦欢
                output_path = output_dir / f"{self._model_name_to_filename(model_name)}.py"

                # 浠?properties 鑷姩鐢熸垚 SQLAlchemy 瀛楁锛屽苟浼犲叆鍏ㄩ噺妯″瀷閰嶇疆鐢ㄤ簬澶栭敭瑙ｆ瀽
                properties = model_def.get('properties', {})
                fields = self._convert_properties_to_fields(
                    properties,
                    model_name=model_name,
                    all_models=self.models,
                    table_prefix=table_prefix
                )

                # 鑾峰彇鑷畾涔夋柟娉?                def_list = model_def.get('def_list', [])
                custom_methods = {}
                if def_list:
                    defs_target = model_def.get('defs_target', f"{model_name.lower()}_defs.py")
                    custom_methods = self._load_custom_methods_from_target(model_name, def_list, defs_target)

                # 鍑嗗妯℃澘涓婁笅鏂?                class_def = {
                    'fields': fields,
                    'table': model_def.get('table'),
                    'description': model_def.get('description'),
                    'relationships': model_def.get('relationships', {}),
                    'indexes': model_def.get('indexes', []),
                    'unique_constraints': model_def.get('unique_constraints', []),
                }

                # 妫€娴?uuid 涓婚敭 / datetime 榛樿鍊硷紙鐢ㄤ簬鎺у埗椤跺眰 import锛?                has_uuid_pk = False
                has_datetime_default = False
                for fdef in fields.values():
                    if fdef.get('primary_key') and fdef.get('type') == 'string':
                        has_uuid_pk = True
                    if fdef.get('default') == 'datetime.utcnow':
                        has_datetime_default = True

                template_data = {
                    'model_name': model_name,
                    'classes': {model_name: class_def},
                    'table_prefix': table_prefix,
                    'all_models': self.models,
                    'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'has_numeric': self._check_decimal_fields_from_properties(properties),
                    'has_decimal': self._check_decimal_fields_from_properties(properties),
                    'has_text': self._check_text_fields_from_properties(properties),
                    'has_timestamps': self._check_timestamp_fields_from_properties(properties),
                    'has_foreign_keys': self._check_foreign_keys_in_fields(fields),
                    'has_relationships': self._check_relationships(model_def),
                    'is_unlogged': model_def.get('unlogged', False),
                    'custom_methods': custom_methods,
                    'table_has_indexes': bool(model_def.get('indexes')),
                    'table_has_unique_constraints': bool(model_def.get('unique_constraints')),
                    # 浼犲叆 jinja 妯℃澘鍐呬娇鐢ㄧ殑鍛藉悕绌洪棿鍙橀噺
                    'ns': {
                        'has_uuid_pk': has_uuid_pk,
                        'has_datetime_default': has_datetime_default,
                    },
                    # 瀛愭ā鍧楄矾寰勶紙鐢ㄤ簬鎺у埗 Base 瀵煎叆鏂瑰紡锛?                    'module_path': module_path,
                }

                content = self._render_template('sqlalchemy_model.py.jinja2', template_data)
                self._write_file(output_path, content)
                print(f"  [OK] Model: {output_path}")
                success_models.append(model_name)
                generated_count += 1

            except Exception as e:
                import traceback
                print(f"  [ERROR] 鐢熸垚 {model_name} 澶辫触锛歿e}")
                print(f"    璇︾粏淇℃伅锛歿traceback.format_exc()}")
                # 瀛樺湪澶辫触妯″瀷鏃剁洿鎺ラ€€鍑猴紝閬垮厤鐢熸垚涓嶅畬鏁寸殑 __init__.py
                raise SystemExit(1)

        # 涓烘瘡涓娇鐢ㄧ殑瀛愭ā鍧楀垱寤?__init__.py
        self._create_module_init_files(output_base, used_modules)

        # 鍏ㄩ儴鐢熸垚鎴愬姛鍚庢墠鏇存柊 __init__.py
        if success_models:
            successful_orm_config = {k: v for k, v in orm_models.items() if k in success_models}
            self._update_shared_models_init_from_orm(successful_orm_config)

        print(f"  鉁?鍏辩敓鎴?{generated_count} 涓ā鍨嬫枃浠?)

    def generate_single_model(self, model_names: List[str]):
        """
        浠呯敓鎴愭寚瀹氱殑鍗曚釜鎴栧涓?ORM 妯″瀷鏂囦欢锛堜笉閲嶆柊鐢熸垚鍏ㄩ儴妯″瀷锛?
        Args:
            model_names: 瑕佺敓鎴愮殑妯″瀷鍚嶇О鍒楄〃锛屽 ["TeamComment", "CustomPostContent"]
        """
        print(f"\n[鍗曟ā鍨嬬敓鎴怾 鎸囧畾妯″瀷: {model_names}")

        try:
            from src.setting import settings
        except ImportError:
            settings = type('Settings', (), {'db_table_prefix': ''})()

        table_prefix = getattr(settings, 'db_table_prefix', '')
        from datetime import datetime

        output_base = self.project_root / "shared" / "models"
        output_base.mkdir(parents=True, exist_ok=True)

        generated_count = 0
        success_models = []
        used_modules = set()

        for model_name in model_names:
            model_def = self.models.get(model_name)
            if not model_def:
                print(f"  鈿?妯″瀷 '{model_name}' 鏈湪 models.yaml 涓畾涔夛紝璺宠繃")
                continue
            if not model_def.get('orm'):
                print(f"  鈿?妯″瀷 '{model_name}' 鏈惎鐢?ORM (orm: true)锛岃烦杩?)
                continue

            try:
                module_path = model_def.get('module', '').strip()
                if module_path:
                    module_path = module_path.replace('\\', '/').strip('/')
                    used_modules.add(module_path)
                    output_dir = output_base / module_path
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    output_dir = output_base

                output_path = output_dir / f"{self._model_name_to_filename(model_name)}.py"

                properties = model_def.get('properties', {})
                fields = self._convert_properties_to_fields(properties, model_def)

                # 鏀堕泦绱㈠紩
                indexes = model_def.get('indexes', [])
                has_indexes = len(indexes) > 0
                has_foreign_keys = any(f.get('fk_column') for f in fields.values())
                has_unique_constraints = any(ix.get('unique') for ix in indexes)

                # 鏀堕泦鎵€鏈夊瓧娈电被鍨嬩俊鎭?                has_datetime_default = False
                has_numeric = False
                for field in fields.values():
                    if field.get('default') == 'datetime.utcnow':
                        has_datetime_default = True
                    if field.get('type') == 'Numeric':
                        has_numeric = True

                has_relationships = any(
                    field.get('is_rel') for field in fields.values()
                )

                # 娓叉煋妯＄増
                template = self.jinja_env.get_template('sqlalchemy_model.py.jinja2')
                rendered = template.render(
                    model_name=model_name,
                    generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    classes={model_name: {
                        'table_name': model_def.get('table', ''),
                        'description': model_def.get('description', ''),
                        'fields': fields,
                        'indexes': indexes,
                        'unique_constraints': [ix for ix in indexes if ix.get('unique')],
                    }},
                    module_path=module_path,
                    table_prefix=table_prefix,
                    table_has_indexes=has_indexes,
                    has_foreign_keys=has_foreign_keys,
                    has_unique_constraints=has_unique_constraints,
                    has_datetime_default=has_datetime_default,
                    has_numeric=has_numeric,
                    has_relationships=has_relationships,
                    is_unlogged=model_def.get('unlogged', False),
                    ns=type('NS', (), {'has_uuid_pk': any(
                        f.get('type') == 'String' and f.get('primary_key') for f in fields.values()
                    ), 'has_datetime_default': has_datetime_default})(),
                )

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rendered)

                generated_count += 1
                success_models.append(model_name)
                print(f"  [OK] {model_name}: {output_path}")

            except Exception as e:
                print(f"  [FAIL] {model_name}: {e}")
                import traceback
                traceback.print_exc()

        # 鏇存柊 __init__.py
        if used_modules:
            self._create_module_init_files(output_base, used_modules)
        if success_models:
            successful_orm_config = {k: v for k, v in self.models.items() if k in success_models}
            self._update_shared_models_init_from_orm(successful_orm_config)

        print(f"  鉁?鍏辩敓鎴?{generated_count} 涓ā鍨嬫枃浠?)

    def _get_output_path(self, framework: str, config_key: str) -> Path:
        """鑾峰彇杈撳嚭鏂囦欢璺緞"""
        gen_config = self.generation_config.get(framework, {})
        if not gen_config:
            return None

        output_dir = self.project_root / gen_config.get('output_dir', '')
        output_file = gen_config.get(config_key, '')

        if output_dir and output_file:
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir / output_file

        return None

    def _filter_endpoints_by_module(self) -> Dict[str, List[Dict]]:
        """鎸夋ā鍧楀垎缁勭鐐?""
        modules = {}
        for endpoint in self.endpoints:
            module_name = endpoint.get('module', 'default')
            if module_name not in modules:
                modules[module_name] = []
            modules[module_name].append(endpoint)
        return modules

    def _collect_django_imports(self) -> List[str]:
        """鏀堕泦 Django Ninja 闇€瑕佺殑瀵煎叆"""
        imports = set()

        # 鍩虹瀵煎叆
        imports.add("from ninja import Router, Form, Query, Path")
        imports.add("from django.http import HttpRequest")
        imports.add("from django_blog.django_ninja_compat import ApiResponse")

        # 鏍规嵁绔偣鍙傛暟绫诲瀷娣诲姞瀵煎叆
        for endpoint in self.endpoints:
            params = endpoint.get('parameters', [])
            for param in params:
                if param.get('location') == 'form':
                    imports.add("from ninja import Form")
                elif param.get('location') == 'query':
                    imports.add("from ninja import Query")
                elif param.get('location') == 'path':
                    imports.add("from ninja import Path")

        return sorted(list(imports))

    def _collect_fastapi_imports(self) -> List[str]:
        """鏀堕泦 FastAPI 闇€瑕佺殑瀵煎叆"""
        imports = set()

        # 鍩虹瀵煎叆
        imports.add("from fastapi import APIRouter, Depends, Form, Query, Path")
        imports.add("from src.api.v1.core.responses import ApiResponse")

        # 鏍规嵁绔偣鏄惁闇€瑕佽璇佹坊鍔犲鍏?        for endpoint in self.endpoints:
            if endpoint.get('django_ninja_auth', False) or endpoint.get('fastapi_dependencies', []):
                imports.add("from src.auth import jwt_required_dependency as jwt_required")

        return sorted(list(imports))

    def _model_name_to_filename(self, model_name: str) -> str:
        """灏嗘ā鍨嬪悕杞崲涓烘枃浠跺悕锛堥┘宄拌浆涓嬪垝绾匡級"""
        import re
        # 鍦ㄥぇ鍐欏瓧姣嶅墠鎻掑叆涓嬪垝绾?        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', model_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _check_list_fields(self, model_def: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鍒楄〃绫诲瀷瀛楁"""
        for field_def in model_def.get('fields', {}).values():
            if field_def.get('type') == 'array' or field_def.get('type') == 'list':
                return True
        return False

    def _check_numeric_fields(self, model_def: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鏁板€肩被鍨嬪瓧娈?""
        for field_def in model_def.get('fields', {}).values():
            if field_def.get('type') in ['number', 'float', 'decimal']:
                return True
        return False

    def _check_text_fields(self, model_def: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鏂囨湰绫诲瀷瀛楁"""
        for field_def in model_def.get('fields', {}).values():
            if field_def.get('type') == 'text':
                return True
        return False

    def _check_timestamp_fields(self, model_def: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鏃堕棿鎴冲瓧娈?""
        for field_def in model_def.get('fields', {}).values():
            if field_def.get('type') in ['datetime', 'timestamp']:
                return True
        return False

    def _check_foreign_keys(self, model_def: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁澶栭敭"""
        for field_def in model_def.get('fields', {}).values():
            if field_def.get('foreign_key'):
                return True
        return False

    def _check_foreign_keys_in_fields(self, fields: Dict) -> bool:
        """妫€鏌?fields 涓槸鍚︽湁澶栭敭"""
        for field_def in fields.values():
            if field_def.get('foreign_key'):
                return True
        return False

    def _check_relationships(self, model_def: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鍏崇郴瀹氫箟"""
        return bool(model_def.get('relationships', {}))

    def _load_custom_methods(self, model_name: str, def_list: list) -> dict:
        """
        浠?shared/defs/<model_name>_defs.py 鍔犺浇鑷畾涔夋柟娉曪紙鍚戝悗鍏煎锛?
        Args:
            model_name: 妯″瀷鍚嶇О锛堝 User锛?            def_list: 鏂规硶鍚嶇О鍒楄〃锛堝 ['is_vip']锛?
        Returns:
            鍖呭惈鏂规硶婧愮爜鐨勫瓧鍏?{method_name: source_code}
        """
        # 浣跨敤榛樿鐨勭洰鏍囨枃浠跺悕
        return self._load_custom_methods_from_target(model_name, def_list, f"{model_name.lower()}_defs.py")

    def _load_custom_methods_from_target(self, model_name: str, def_list: list, defs_target: str) -> dict:
        """
        浠庢寚瀹氱殑鏂囦欢鍔犺浇鑷畾涔夋柟娉?
        Args:
            model_name: 妯″瀷鍚嶇О锛堝 User锛?            def_list: 鏂规硶鍚嶇О鍒楄〃锛堝 ['is_vip']锛?            defs_target: 鐩爣鏂囦欢鍚嶏紙鐩稿浜?shared/defs/锛夛紝濡?'user_defs.py' 鎴?'mydef.py'

        Returns:
            鍖呭惈鏂规硶婧愮爜鐨勫瓧鍏?{method_name: source_code}
        """
        import importlib.util
        import inspect

        custom_methods = {}
        # 鏀寔缁濆璺緞鍜岀浉瀵硅矾寰?        if Path(defs_target).is_absolute():
            defs_file = Path(defs_target)
        else:
            defs_file = self.project_root / "shared" / "defs" / defs_target

        if not defs_file.exists():
            print(f"  鈿?璀﹀憡锛氳嚜瀹氫箟鏂规硶鏂囦欢涓嶅瓨鍦細{defs_file}")
            return custom_methods

        try:
            # 鍔ㄦ€佸姞杞芥ā鍧?            module_name = Path(defs_target).stem  # 涓嶅甫 .py 鐨勬枃浠跺悕
            spec = importlib.util.spec_from_file_location(module_name, defs_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 鎻愬彇鎸囧畾鐨勬柟娉?            for method_name in def_list:
                if hasattr(module, method_name):
                    method = getattr(module, method_name)
                    # 鑾峰彇鏂规硶婧愮爜
                    try:
                        source = inspect.getsource(method)
                        custom_methods[method_name] = source
                        print(f"  [OK] 鍔犺浇鑷畾涔夋柟娉曪細{model_name}.{method_name} (from {defs_target})")
                    except Exception as e:
                        print(f"  鈿?璀﹀憡锛氭棤娉曡幏鍙栨柟娉?{method_name} 鐨勬簮鐮侊細{e}")
                else:
                    print(f"  鈿?璀﹀憡锛氭柟娉?{method_name} 鍦?{defs_target} 涓湭鎵惧埌")

        except Exception as e:
            import traceback
            print(f"  [ERROR] 鍔犺浇鑷畾涔夋柟娉曞け璐ワ細{e}")
            print(f"    璇︾粏淇℃伅锛歿traceback.format_exc()}")

        return custom_methods

    # ==================== ORM 閰嶇疆妫€鏌ユ柟娉曪紙浠?models[*].orm 璇诲彇锛?====================

    def _convert_properties_to_fields(self, properties: Dict, model_name: str = None,
                                      all_models: Dict = None, table_prefix: str = '') -> Dict:
        """浠?API properties 杞崲涓?SQLAlchemy fields锛屾敮鎸佸畬鏁撮厤缃?""
        # SQLAlchemy 淇濈暀瀛楀垪琛?        RESERVED_NAMES = {
            'metadata', 'registry', 'declarative_base', 'Base',
            'query', 'session', 'mapper', 'column_property',
            'composite', 'synonym', 'relationship', 'backref',
            'validate', 'reconstructor', 'declared_attr',
            'hybrid_property', 'hybrid_method', 'AssociationProxy'
        }

        fields = {}
        first_integer_field = None  # 鐢ㄤ簬鏃?id 涓旀湭鏄庣‘澹版槑鑷鐨勪富閿嚜鍔ㄨ缃€掑

        # 鍏堟鏌ユ槸鍚︽湁鍚嶄负 id 鐨勫瓧娈?        has_id_field = any(k == 'id' for k in properties)

        for prop_name, prop_def in properties.items():
            raw_type = prop_def.get('type', 'string')
            field_type = self._map_property_type_to_sqlalchemy(raw_type)

            # 妫€鏌ユ槸鍚︿负淇濈暀瀛楋紝濡傛灉鏄垯閲嶅懡鍚?            python_field_name = prop_name
            db_column_name = None
            if prop_name.lower() in RESERVED_NAMES:
                # 鍦ㄥ瓧娈靛悕鍓嶆坊鍔犲墠缂€浠ラ伩鍏嶅啿绐?                python_field_name = f"extra_{prop_name}"
                db_column_name = prop_name  # 鏁版嵁搴撳垪鍚嶄繚鎸佸師鏍?
            field_info = {
                'type': field_type,
                'description': prop_def.get('description', prop_name),
                'doc': prop_def.get('description', prop_name),
                'python_name': python_field_name,  # Python 灞炴€у悕
                'db_column': db_column_name,  # 鏁版嵁搴撳垪鍚嶏紙濡傛灉闇€瑕侊級
            }

            # 鐗规畩澶勭悊锛歴tring + date-time 鏍煎紡 -> datetime
            if raw_type == 'string' and prop_def.get('format') == 'date-time':
                field_info['type'] = 'datetime'

            # 涓婚敭澶勭悊
            if prop_name == 'id':
                field_info['primary_key'] = True
                field_info['autoincrement'] = True
            elif prop_def.get('primaryKey'):
                field_info['primary_key'] = True
                # 濡傛灉娌℃湁 id 瀛楁锛屼笖璇ュ瓧娈垫槸 integer锛屽垯灏濊瘯鑷
                if not has_id_field and field_type == 'integer':
                    if first_integer_field is None:
                        field_info['autoincrement'] = True
                        first_integer_field = prop_name  # 璁板綍绗竴涓?                    else:
                        # 鍚庣画鐨勬暣鏁颁富閿笉鍐嶈嚜鍔ㄩ€掑
                        pass

            # 甯歌灞炴€?            if prop_def.get('nullable'):
                field_info['nullable'] = True
            if prop_def.get('maxLength'):
                field_info['max_length'] = prop_def['maxLength']
            if 'default' in prop_def:
                field_info['default'] = prop_def['default']
            if prop_def.get('unique'):
                field_info['unique'] = True
            if prop_def.get('index'):
                field_info['index'] = True
            if prop_def.get('sensitive'):
                field_info['sensitive'] = True

            # Decimal 绮惧害
            if raw_type in ('number', 'float', 'decimal'):
                field_info['type'] = 'decimal'  # 缁熶竴涓?decimal
                field_info['max_digits'] = prop_def.get('maxDigits', 10)
                field_info['decimal_places'] = prop_def.get('decimalPlaces', 2)

            # 澶栭敭澶勭悊锛氶瑙ｆ瀽鐩爣琛ㄥ叏鍚嶅強涓婚敭鍒楋紙榛樿涓?'id'锛?            if prop_def.get('foreignKey'):
                fk_model_name = prop_def['foreignKey']
                field_info['foreign_key'] = fk_model_name
                # 鏌ユ壘鐩爣妯″瀷閰嶇疆
                target_model = all_models.get(fk_model_name, {}) if all_models else {}
                target_table = target_model.get('table', self._model_name_to_filename(fk_model_name))
                field_info['fk_table'] = table_prefix + target_table
                # 绠€鍗曡捣瑙侊紝涓婚敭鍒楅粯璁や负 'id'锛屽椤圭洰涓粺涓€瑙勮寖鍗冲彲
                field_info['fk_column'] = 'id'
                if model_name and fk_model_name == model_name:
                    field_info['is_self_reference'] = True

            fields[python_field_name] = field_info

        return fields

    def _map_property_type_to_sqlalchemy(self, prop_type: str) -> str:
        """鏄犲皠 TypeScript/JSON 绫诲瀷鍒?SQLAlchemy 绫诲瀷"""
        type_mapping = {
            'integer': 'integer',
            'bigint': 'bigint',  # 澶ф暣鏁扮被鍨?            'number': 'decimal',  # number 绫诲瀷鏄犲皠涓?decimal锛岀敤浜?Django 鐨?DecimalField
            'float': 'decimal',  # float 涔熸槧灏勪负 decimal
            'string': 'string',
            'boolean': 'boolean',
            'array': 'string',  # 鏁扮粍閫氬父瀛樺偍涓?JSON 瀛楃涓?            'object': 'text',  # 瀵硅薄閫氬父瀛樺偍涓?JSON 鏂囨湰
            'text': 'text',  # 闀挎枃鏈被鍨?            'datetime': 'datetime',
            'timestamp': 'datetime',
            'date': 'datetime',
        }
        return type_mapping.get(prop_type, 'string')

    def _check_list_fields_from_properties(self, properties: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鍒楄〃绫诲瀷瀛楁锛堜粠 properties锛?""
        for prop_def in properties.values():
            if prop_def.get('type') == 'array':
                return True
        return False

    def _check_numeric_fields_from_properties(self, properties: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鏁板€肩被鍨嬪瓧娈碉紙浠?properties锛?""
        for prop_def in properties.values():
            if prop_def.get('type') in ['number', 'integer']:
                return True
        return False

    def _check_decimal_fields_from_properties(self, properties: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁 decimal 绫诲瀷瀛楁锛堜粠 properties锛?""
        for prop_def in properties.values():
            # number 鍜?float 绫诲瀷閮戒細琚槧灏勪负 decimal
            if prop_def.get('type') in ['number', 'float', 'decimal']:
                return True
        return False

    def _check_text_fields_from_properties(self, properties: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鏂囨湰绫诲瀷瀛楁锛堜粠 properties锛?""
        for prop_def in properties.values():
            if prop_def.get('type') == 'string' and prop_def.get('maxLength', 0) > 500:
                return True
        return False

    def _check_timestamp_fields_from_properties(self, properties: Dict) -> bool:
        """妫€鏌ユ槸鍚︽湁鏃堕棿鎴冲瓧娈碉紙浠?properties锛?""
        for prop_def in properties.values():
            if prop_def.get('format') == 'date-time':
                return True
        return False

    def _scan_association_tables(self) -> Dict[str, list]:
        """
        鑷姩鎵弿 shared/models 鐩綍涓嬬殑鍏宠仈琛紙Table 瀵硅薄锛?
        Returns:
            {'imports': [import_statements], 'exports': [export_names]}
        """
        models_dir = self.project_root / "shared" / "models"
        imports = []
        exports = []

        if not models_dir.exists():
            return {'imports': imports, 'exports': exports}

        # 鎵弿鎵€鏈?Python 鏂囦欢
        for py_file in models_dir.glob("*.py"):
            if py_file.name.startswith('_') or py_file.name == '__init__.py':
                continue

            # 璇诲彇鏂囦欢鍐呭锛屾煡鎵?Table 瀵硅薄瀹氫箟
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 浣跨敤姝ｅ垯琛ㄨ揪寮忔煡鎵?Table 瀵硅薄瀹氫箟
                # 鍖归厤妯″紡锛歵able_name = Table(
                import re
                pattern = r'^(\w+)\s*=\s*Table\('
                matches = re.findall(pattern, content, re.MULTILINE)

                if matches:
                    module_name = py_file.stem  # 涓嶅甫 .py 鐨勬枃浠跺悕
                    for table_name in matches:
                        imports.append(f"from .{module_name} import {table_name}")
                        exports.append(table_name)
                        print(f"  [OK] 妫€娴嬪埌鍏宠仈琛? {table_name} (from {module_name}.py)")
            except Exception as e:
                print(f"  [WARN] 鎵弿 {py_file.name} 澶辫触: {e}")

        return {'imports': imports, 'exports': exports}

    def _create_module_init_files(self, output_base: Path, used_modules: set):
        """涓烘瘡涓娇鐢ㄧ殑瀛愭ā鍧楃洰褰曞垱寤?__init__.py 鏂囦欢

        鎵弿瀛愭ā鍧楃洰褰曚腑鐨勬墍鏈?.py 鏂囦欢锛屾彁鍙栫被鍚嶏紝骞剁敓鎴愭纭殑
        閲嶆柊瀵煎嚭璇彞锛屼互鏀寔 `from shared.models.<module> import <Model>` 椋庢牸鐨勫鍏ャ€?
        Args:
            output_base: shared/models/ 鍩虹璺緞
            used_modules: 浣跨敤鐨勫瓙妯″潡璺緞闆嗗悎锛堝 {'intel', 'knowledge', 'workflow'}锛?        """
        import re as _re
        for module_path in sorted(used_modules):
            module_dir = output_base / module_path
            module_dir.mkdir(parents=True, exist_ok=True)
            init_file = module_dir / "__init__.py"

            # 鎵弿妯″潡鐩綍涓殑鎵€鏈?.py 鏂囦欢锛屾彁鍙栫被瀹氫箟
            imports = []
            exports = []
            for py_file in sorted(module_dir.iterdir()):
                if py_file.name.startswith('_') or py_file.suffix != '.py':
                    continue
                try:
                    content = py_file.read_text(encoding='utf-8')
                except (UnicodeDecodeError, OSError):
                    continue
                # 鎻愬彇 class XXX(Base): 鎴?class XXX(BaseMixin, Base): 绛夊舰寮?                class_matches = _re.findall(r'class\s+(\w+)\s*\([^)]*Base[^)]*\)\s*:', content)
                if class_matches:
                    module_name = py_file.stem  # 涓嶅甫 .py 鐨勬枃浠跺悕
                    for class_name in class_matches:
                        imports.append(f"from .{module_name} import {class_name}")
                        exports.append(class_name)

            if imports:
                imports_section = "\n".join(imports)
                all_section = ", ".join(f"'{name}'" for name in sorted(exports))
                init_content = f'''"""
{module_path} 瀛愭ā鍧?- 妯″瀷瀹氫箟
鐢变唬鐮佺敓鎴愬櫒鑷姩鐢熸垚 - 璇峰嬁鎵嬪姩淇敼
"""
{imports_section}

__all__ = [{all_section}]
'''
            else:
                init_content = f'''"""
{module_path} 瀛愭ā鍧?- 妯″瀷瀹氫箟
鐢变唬鐮佺敓鎴愬櫒鑷姩鐢熸垚 - 璇峰嬁鎵嬪姩淇敼
"""
'''
            self._write_file(init_file, init_content)
            print(f"  [OK] Module __init__.py: {init_file} ({len(exports)} 涓ā鍨?")

    def _update_shared_models_init_from_orm(self, orm_models_config: Dict):
        """鏇存柊 shared/models/__init__.py 鏂囦欢锛堟噿鍔犺浇鐗堟湰锛?
        鐢熸垚绾噿鍔犺浇缁撴瀯锛氶€氳繃 _LAZY_IMPORTS 瀛楀吀 + __getattr__ 瀹炵幇鎸夐渶瀵煎叆銆?        鏀寔妯″潡灞傜骇缁撴瀯锛氬鏋滄ā鍨嬪畾涔変簡 module 灞炴€э紝
        鎳掑姞杞借矾寰勪細浣跨敤宓屽鏍煎紡锛堝 .intel.data_source锛夈€?        """
        init_path = self.project_root / "shared" / "models" / "__init__.py"

        # 鏋勫缓鎳掑姞杞芥槧灏勬潯鐩拰 __all__ 鍒楄〃
        lazy_entries = []  # (model_name, module_path) 鍏冪粍鍒楄〃
        all_exports = ['Base']

        for model_name, model_def in orm_models_config.items():
            filename = self._model_name_to_filename(model_name)
            module_path = model_def.get('module', '').strip()

            if module_path:
                module_path = module_path.replace('\\', '/').strip('/')
                module_dotted = module_path.replace('/', '.')
                lazy_path = f'.{module_dotted}.{filename}'
            else:
                lazy_path = f'.{filename}'

            lazy_entries.append((model_name, lazy_path))
            all_exports.append(model_name)

        # 宸茬煡妯″瀷鍚嶉泦鍚堬紙鐢ㄤ簬鍘婚噸锛?        known_model_names = {name for name, _ in lazy_entries}

        # 鎵弿鍏变韩妯″瀷鐩綍涓墜鍔ㄥ垱寤轰絾鏈湪 models.yaml 涓畾涔夌殑妯″瀷鏂囦欢
        # 杩欎簺鏂囦欢浣跨敤 `from . import Base` 涓斿寘鍚?class XXX(Base): 瀹氫箟
        import re
        shared_models_dir = self.project_root / "shared" / "models"
        for py_file in sorted(shared_models_dir.rglob("*.py")):
            if py_file.name.startswith('_') or py_file.name == '__init__.py':
                continue
            try:
                content = py_file.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            # 妫€鏌ユ槸鍚︽槸浣跨敤 `from . import Base` 鐨勬墜鍔ㄦā鍨嬫枃浠?            if 'from . import Base' not in content and 'from . import Base' not in content.replace(' ', ''):
                continue
            # 鎻愬彇 class XXX(Base): 涓殑绫诲悕
            class_matches = re.findall(r'class\s+(\w+)\s*\(\s*Base\s*\)\s*:', content)
            for class_name in class_matches:
                if class_name in known_model_names:
                    continue
                # 璁＄畻鐩稿浜?shared/models/ 鐨勮矾寰?                rel_path = py_file.relative_to(shared_models_dir)
                parts = list(rel_path.with_suffix('').parts)
                if len(parts) == 1:
                    lazy_path = f'.{parts[0]}'
                else:
                    lazy_path = '.' + '.'.join(parts)
                lazy_entries.append((class_name, lazy_path))
                all_exports.append(class_name)
                known_model_names.add(class_name)
                print(f"  [INFO] 鍙戠幇鎵嬪姩妯″瀷鏂囦欢锛歿rel_path} -> {class_name}")

        # 鑷姩鎵弿鍏宠仈琛紙Table 瀵硅薄锛?        association_imports = self._scan_association_tables()
        for import_stmt in association_imports['imports']:
            # 瑙ｆ瀽 "from .xxx import yyy" 鏍煎紡
            match = re.search(r'from \.(\S+) import (\w+)', import_stmt)
            if match:
                lazy_path = f'.{match.group(1)}'
                table_name = match.group(2)
                lazy_entries.append((table_name, lazy_path))
                all_exports.append(table_name)

        # 鏍煎紡鍖栨噿鍔犺浇鏄犲皠琛?        max_name_len = max(len(name) for name, _ in lazy_entries) if lazy_entries else 20
        lazy_lines = []
        for name, path in sorted(lazy_entries, key=lambda x: x[0]):
            lazy_lines.append(f"    '{name}': '{path}',")
        lazy_section = "\n".join(lazy_lines)

        # 鏍煎紡鍖?__all__ 鍒楄〃
        all_lines = []
        for name in sorted(all_exports):
            all_lines.append(f"    '{name}',")
        all_section = "\n".join(all_lines)

        # 鐢熸垚瀹屾暣鐨?__init__.py 鍐呭
        new_content = f'''"""
Models 鍖?- 鎳掑姞杞界増鏈?
鎵€鏈夋ā鍨嬬被閫氳繃 __getattr__ 鎸夐渶瀵煎叆锛岄伩鍏嶅惎鍔ㄦ椂涓€娆℃€у姞杞芥墍鏈夋ā鍨嬫枃浠躲€?Base 淇濇寔绔嬪嵆瀵煎叆锛圫QLAlchemy 鍏冩暟鎹垵濮嬪寲蹇呴渶锛夈€?
鐢变唬鐮佺敓鎴愬櫒鑷姩鐢熸垚 - 璇峰嬁鎵嬪姩淇敼
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# ==================== 鎳掑姞杞芥槧灏勮〃 ====================
# 妯″瀷鍚?-> 鐩稿妯″潡璺緞锛堜笉鍚?shared.models 鍓嶇紑锛?_LAZY_IMPORTS = {{
{lazy_section}
}}

# 宸插姞杞界殑妯″瀷缂撳瓨锛堥伩鍏嶉噸澶嶅鍏ワ級
_loaded_models = {{}}


def __getattr__(name):
    """妯″潡绾?__getattr__锛氭寜闇€鎳掑姞杞芥ā鍨嬬被"""
    if name in _loaded_models:
        return _loaded_models[name]

    module_path = _LAZY_IMPORTS.get(name)
    if module_path is not None:
        import importlib
        module = importlib.import_module(module_path, package='shared.models')
        cls = getattr(module, name)
        # 缂撳瓨鍒版ā鍧楀懡鍚嶇┖闂达紝鍚庣画璁块棶鐩存帴鍛戒腑
        globals()[name] = cls
        _loaded_models[name] = cls
        return cls

    raise AttributeError(f"module 'shared.models' has no attribute {{name!r}}")


# ==================== 鑷姩鐢熸垚 - __all__ ====================
# 姝ら儴鍒嗙敱鑴氭湰鑷姩鐢熸垚 - 璇峰嬁鎵嬪姩淇敼

__all__ = [
{all_section}
]
# ============================================================================
'''

        self._write_file(init_path, new_content)
        print(f"  [OK] 鏇存柊 shared/models/__init__.py锛堟噿鍔犺浇妯″紡锛寋len(lazy_entries)} 涓ā鍨嬶級")

    def _update_shared_models_init(self, shared_models_config: Dict):
        """鏇存柊 shared/models/__init__.py 鏂囦欢"""
        init_path = self.project_root / "shared" / "models" / "__init__.py"

        # 鐢熸垚瀵煎叆璇彞
        imports = []
        all_exports = ['Base']

        for model_name, model_def in shared_models_config.items():
            filename = self._model_name_to_filename(model_name)
            # 浠?model_def 涓幏鍙栫被鍚嶏紝鍙兘鏈夊涓被
            class_names = [model_name]
            if 'additional_classes' in model_def:
                class_names.extend(model_def['additional_classes'])

            imports.append(f"from .{filename} import {', '.join(class_names)}")
            all_exports.extend(class_names)

        # 璇诲彇鐜版湁鏂囦欢锛屼繚鐣欓潪鑷姩鐢熸垚鐨勯儴鍒?        if init_path.exists():
            with open(init_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 淇濈暀 Base 瀹氫箟鍜屾墜鍔ㄧ淮鎶ょ殑瀵煎叆锛堝垹闄ゆ墍鏈夎嚜鍔ㄧ敓鎴愰儴鍒嗭級
            lines = content.split('\n')
            new_lines = []
            in_generated_section = False
            skip_next_empty = False

            for line in lines:
                # 妫€娴嬭嚜鍔ㄧ敓鎴愰儴鍒嗙殑寮€濮?                if '鐢?routes.yaml 鑷姩鐢熸垚' in line or 'GENERATED SECTION' in line or '鑷姩鐢熸垚鐨勫鍏? in line:
                    in_generated_section = True
                    continue
                if in_generated_section and (
                        '# ===' in line or '# ================================================================='):
                    skip_next_empty = True
                    continue
                if skip_next_empty and (line.strip() == '' or line.startswith('#')):
                    continue
                skip_next_empty = False

                # 濡傛灉涓嶅湪鑷姩鐢熸垚閮ㄥ垎锛屼繚鐣欒琛?                if not in_generated_section:
                    # 浣嗚烦杩囨棫鐨?from . 瀵煎叆锛堣繖浜涗細琚噸鏂扮敓鎴愶級
                    if not (line.startswith('from .') or (line.startswith('__all__') and '=' in line)):
                        new_lines.append(line)

                # 閬囧埌绌虹殑 __all__ 瀹氫箟涔熻烦杩?                if line.strip() == '__all__ = [':
                    in_generated_section = True
                    continue
                if in_generated_section and line.strip() == ']':
                    in_generated_section = False
                    continue

            # 閲嶆柊鏋勫缓鏂囦欢鍩虹鍐呭
            content = '\n'.join(new_lines)
            # 娓呯悊澶氫綑鐨勭┖琛?            while content.startswith('\n'):
                content = content[1:]
        else:
            content = "from sqlalchemy.orm import declarative_base\n\nBase = declarative_base()\n"

        # 娣诲姞鏂扮殑瀵煎叆
        import_section = "\n".join(imports)
        all_section = "\n__all__ = [\n    '" + "',\n    '".join(all_exports) + "'\n]"

        new_content = f"""{content}
{import_section}

# ==================== 鑷姩鐢熸垚鐨勫鍏?- 鐢?routes.yaml 绠＄悊 ====================
# 姝ら儴鍒嗙敱鑴氭湰鑷姩鐢熸垚 - 璇峰嬁鎵嬪姩淇敼
{all_section}
# ============================================================================
"""

        self._write_file(init_path, new_content)

    def _render_template(self, template_name: str, context: Dict) -> str:
        """娓叉煋 Jinja2 妯℃澘"""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            print(f"  鈿?妯℃澘鏈壘鍒帮細{template_name}")
            return ""

    def _write_file(self, file_path: Path, content: str):
        """鍐欏叆鏂囦欢锛岀‘淇濈紪鐮佷负 UTF-8"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    宸插啓鍏ワ細{file_path}")

    def _format_generated_files(self):
        """浣跨敤 black 鏍煎紡鍖栫敓鎴愮殑 Python 鏂囦欢"""
        print("\n姝ｅ湪鏍煎紡鍖栫敓鎴愮殑鏂囦欢...")

        try:
            import subprocess

            # 闇€瑕佹牸寮忓寲鐨勬枃浠跺垪琛?            files_to_format = [
                self.project_root / "apps" / "generated" / "auto_orm.py",
                self._get_output_path('django_ninja', 'router_file'),
                self._get_output_path('fastapi', 'router_file'),
            ]

            # 娣诲姞 SQLAlchemy 妯″瀷鏂囦欢
            sqlalchemy_models_dir = self.project_root / "shared" / "models"
            if sqlalchemy_models_dir.exists():
                for py_file in sqlalchemy_models_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        files_to_format.append(py_file)

            # 杩囨护鎺?None 鍊?            files_to_format = [f for f in files_to_format if f is not None]

            if not files_to_format:
                print("  鈿?娌℃湁闇€瑕佹牸寮忓寲鐨勬枃浠?)
                return

            # 妫€鏌?black 鏄惁鍙敤
            result = subprocess.run(
                ['black', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                print("  鈿?black 鏈畨瑁咃紝璺宠繃鏍煎紡鍖?)
                print("  鎻愮ず锛氳繍琛?'pip install black' 瀹夎 black 鏍煎紡鍖栧櫒")
                return

            # 鏍煎紡鍖栨瘡涓枃浠?            for file_path in files_to_format:
                if file_path.exists():
                    print(f"  鏍煎紡鍖栵細{file_path}")
                    subprocess.run(
                        ['black', '-q', str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                else:
                    print(f"  鈿?鏂囦欢涓嶅瓨鍦紝璺宠繃锛歿file_path}")

            print("  鉁?鏍煎紡鍖栧畬鎴?)

        except subprocess.TimeoutExpired:
            print("  鈿?鏍煎紡鍖栬秴鏃讹紝璺宠繃")
        except FileNotFoundError:
            print("  鈿?black 鏈壘鍒帮紝璺宠繃鏍煎紡鍖?)
        except Exception as e:
            print(f"  鈿?鏍煎紡鍖栧け璐ワ細{e}")

    def sync_to_django(self, app_name: str = None):
        """灏?SQLAlchemy 妯″瀷鍚屾涓?Django 妯″瀷"""
        print("馃攧 寮€濮嬪悓姝?SQLAlchemy 妯″瀷鍒?Django...\n")

        # 1. 鍏堢敓鎴?Mixins
        print("姝ラ 1: 鐢熸垚 Django Mixin...")
        self._generate_orm_mixins()

        # 2. 濡傛灉鏈夋寚瀹?app锛岀敓鎴愯 app 鐨?models.py
        if app_name:
            print(f"\n姝ラ 2: 涓?app '{app_name}' 鐢熸垚 models.py...")
            # 寰呭疄鐜帮細Django 妯″瀷鐢熸垚鍔熻兘
            print("  鈿狅笍  Django 妯″瀷鐢熸垚鍔熻兘灏氭湭瀹炵幇")
            print("  鎻愮ず锛氳鎵嬪姩鍦?apps/{app_name}/models.py 涓畾涔?Django 妯″瀷")
        else:
            print("\n鈩癸笍  鏈寚瀹?app 鍚嶇О锛屼粎鐢熸垚 Mixin")

        print("\n鉁?鍚屾瀹屾垚锛?)

    def _optimize_sqlalchemy_imports(self):
        """浼樺寲 SQLAlchemy 妯″瀷鏂囦欢鐨勫鍏ヨ鍙?""
        print("\n姝ｅ湪浼樺寲 SQLAlchemy 妯″瀷鐨勫鍏?..")

        try:
            import subprocess

            # 妫€鏌?isort 鏄惁鍙敤
            result = subprocess.run(
                ['isort', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                print("  鈿?isort 鏈畨瑁咃紝璺宠繃瀵煎叆浼樺寲")
                print("  鎻愮ず锛氳繍琛?'pip install isort' 瀹夎 isort")
                return

            # 浼樺寲 shared/models 鐩綍涓嬬殑鎵€鏈?Python 鏂囦欢
            sqlalchemy_models_dir = self.project_root / "shared" / "models"
            if not sqlalchemy_models_dir.exists():
                print("  鈿?shared/models 鐩綍涓嶅瓨鍦?)
                return

            py_files = list(sqlalchemy_models_dir.glob("*.py"))
            if not py_files:
                print("  鈿?娌℃湁闇€瑕佷紭鍖栧鍏ョ殑鏂囦欢")
                return

            # 浣跨敤 isort 浼樺寲瀵煎叆
            for file_path in py_files:
                print(f"  浼樺寲瀵煎叆锛歿file_path}")
                subprocess.run(
                    ['isort', '-q', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

            print("  鉁?瀵煎叆浼樺寲瀹屾垚")

        except subprocess.TimeoutExpired:
            print("  鈿?浼樺寲瀵煎叆瓒呮椂锛岃烦杩?)
        except FileNotFoundError:
            print("  鈿?isort 鏈壘鍒帮紝璺宠繃瀵煎叆浼樺寲")
        except Exception as e:
            print(f"  鈿?浼樺寲瀵煎叆澶辫触锛歿e}")


def main():
    """涓诲嚱鏁?""
    parser = argparse.ArgumentParser(description='璺敱浠ｇ爜鐢熸垚鍣?)
    parser.add_argument('--config', type=str, default=None, help='routes.yaml 閰嶇疆鏂囦欢璺緞')
    parser.add_argument('command', nargs='?', choices=['generate-all', 'sync-to-django', 'generate-model'], default='generate-all',
                        help='瑕佹墽琛岀殑鍛戒护锛堥粯璁わ細generate-all锛?)
    parser.add_argument('--app', type=str, help='app 鍚嶇О锛堢敤浜?sync-to-django 鍛戒护锛?)
    parser.add_argument('--model', type=str, nargs='+', help='瑕佺敓鎴愮殑妯″瀷鍚嶇О锛堢敤浜?generate-model 鍛戒护锛夛紝濡?--model User TeamComment')

    args = parser.parse_args()

    try:
        generator = RouteGenerator(config_path=args.config)

        if args.command == 'sync-to-django':
            generator.sync_to_django(app_name=args.app)
        elif args.command == 'generate-model':
            if not args.model:
                print("閿欒锛氳鎸囧畾瑕佺敓鎴愮殑妯″瀷鍚嶇О锛屽 --model User TeamComment")
                sys.exit(1)
            generator.generate_single_model(args.model)
        else:  # generate-all
            generator.generate_all()

    except FileNotFoundError as e:
        print(f"閿欒锛歿e}")
        sys.exit(1)
    except Exception as e:
        print(f"鐢熸垚澶辫触锛歿e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
