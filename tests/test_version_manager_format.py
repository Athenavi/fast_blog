"""批次 18：``version_manager`` 文件格式测试

覆盖一个实测出来的真实缺陷：该模块曾经"**读 INI、写 JSON**"，
于是 `bump_version()` / `update_database()` 调用一次就把 ``version.txt`` 变成 JSON，
而 ``scripts/build_release.py``、``scripts/cli.py`` 与部署脚本仍按 INI 解析 ——
版本号随即读不到（升级演练时复现：version.txt 变成 JSON 后 `version=` 行消失）。

现在的契约：

  - 写：**始终 INI**（``[RELEASE]`` / ``[DATABASE]`` / ``[AUTHOR]``）；
  - 读：JSON 优先（兼容历史上已被改写成 JSON 的文件），否则按 INI 解析。
"""

from shared.utils.version_manager import VersionManager

INI_SAMPLE = """[RELEASE]
version = 1.2.3
build_time = 2026-01-01T00:00:00Z

[DATABASE]
migration = abc123
status = up_to_date

[AUTHOR]
maintainer = Tester
repository = https://example.com/repo
"""


def test_reads_ini(tmp_path):
    path = tmp_path / "version.txt"
    path.write_text(INI_SAMPLE, encoding="utf-8")

    manager = VersionManager(str(path))

    assert manager.get_version() == "1.2.3"
    assert manager.get_database_info()["migration"] == "abc123"


def test_reads_legacy_json(tmp_path):
    path = tmp_path / "version.txt"
    path.write_text(
        '{"release": {"version": "9.0.0"}, "database": {"migration": "x"}}',
        encoding="utf-8",
    )

    assert VersionManager(str(path)).get_version() == "9.0.0"


def test_bump_version_keeps_ini_format(tmp_path):
    path = tmp_path / "version.txt"
    path.write_text(INI_SAMPLE, encoding="utf-8")

    manager = VersionManager(str(path))
    manager.bump_version("2.0.0")
    manager.update_database("def456", "up_to_date")

    text = path.read_text(encoding="utf-8")
    assert text.lstrip().startswith("[RELEASE]"), "bump 之后必须仍是 INI（不能变成 JSON）"
    assert "version = 2.0.0" in text
    assert "migration = def456" in text

    # 其它按 INI 解析的工具（scripts/build_release.py 等）必须还能读到版本号
    from configparser import ConfigParser

    parser = ConfigParser()
    parser.read_string(text)
    assert parser["RELEASE"]["version"] == "2.0.0"

    # 重新加载也要读得回来
    assert VersionManager(str(path)).get_version() == "2.0.0"


def test_missing_file_creates_ini_defaults(tmp_path):
    path = tmp_path / "version.txt"

    manager = VersionManager(str(path))

    assert manager.get_version() == "0.1.0"
    assert path.read_text(encoding="utf-8").lstrip().startswith("[RELEASE]")
