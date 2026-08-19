"""多平台采集：城市/薪资映射与跨源去重。"""
from app.collectors.registry import get_adapter, supported_platforms
from app.collectors.zhipin import city_to_code, salary_to_code
from app.services.job_import_service import _dedup_hash, _salary_overlap


def test_zhipin_registered():
    assert "zhipin" in supported_platforms()
    assert "zhaopin" in supported_platforms()
    assert get_adapter("zhipin").platform == "zhipin"


def test_city_and_salary_mapping():
    assert city_to_code("北京") == "101010100"
    assert city_to_code("101020100") == "101020100"
    assert city_to_code(None) == "100010000"
    assert salary_to_code(None, None) is None
    assert salary_to_code(8000, 12000) == "404"
    assert salary_to_code(15000, 25000) == "405"
    assert salary_to_code(30000, 40000) == "406"


def test_cross_source_dedup():
    a = {"company_name": "字节跳动科技有限公司", "title": "Java 后端", "city": "北京"}
    b = {"company_name": "字节跳动", "title": "Java后端", "city": "北京"}
    c = {"company_name": "阿里巴巴", "title": "Java后端", "city": "北京"}
    assert _dedup_hash(a) == _dedup_hash(b)
    assert _dedup_hash(a) != _dedup_hash(c)


def test_salary_overlap():
    job = {"salary_min": 15000, "salary_max": 25000}
    assert _salary_overlap(job, 10000, 20000)
    assert not _salary_overlap(job, 30000, 40000)
    assert _salary_overlap(job, None, None)
