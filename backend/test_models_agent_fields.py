from datetime import datetime

from models import ParsedQuery, Product, SearchResult, SkillRun


def test_product_has_recommendation_metadata_defaults():
    product = Product(
        id="p1",
        title="华为 FreeBuds 蓝牙耳机",
        price=499,
        brand="华为",
        platform="taobao",
    )

    assert product.recommendation_score == 0.0
    assert product.recommendation_reason is None


def test_search_result_has_agent_metadata_defaults():
    result = SearchResult(
        task_id="task-1",
        query="蓝牙耳机",
        parsed_query=ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"]),
        products=[],
        total_count=0,
        status="processing",
        created_at=datetime.now(),
    )

    assert result.agent_trace == []
    assert result.memory_context == {}
    assert result.effective_query is None
    assert result.skill_runs == []


def test_search_result_serializes_skill_runs_and_agent_metadata():
    result = SearchResult(
        task_id="task-2",
        query="我想买 500 元左右的蓝牙耳机",
        parsed_query=ParsedQuery(
            category="蓝牙耳机",
            keywords=["蓝牙耳机"],
            price_min=400,
            price_max=600,
            features=["降噪"],
        ),
        products=[
            Product(
                id="p1",
                title="华为 FreeBuds 蓝牙耳机",
                price=499,
                brand="华为",
                platform="taobao",
                recommendation_score=1.2,
                recommendation_reason="命中你常看的华为品牌",
            )
        ],
        total_count=1,
        status="completed",
        agent_trace=["解析需求 -> 蓝牙耳机 · ¥400-600"],
        memory_context={
            "top_brands": [{"brand": "华为", "score": 0.9, "count": 3}],
            "matched_signals": {
                "brand": True,
                "feature": False,
                "price_range": True,
                "has_match": True,
            },
        },
        effective_query="蓝牙耳机 华为 降噪",
        skill_runs=[
            SkillRun(
                skill_name="jd_search",
                platform="jd",
                query="蓝牙耳机",
                status="completed",
                duration_seconds=94.0,
                wait_seconds=12.0,
                control_seconds=70.0,
                extract_seconds=12.0,
                product_count=8,
            )
        ],
        created_at=datetime.now(),
    )

    data = result.model_dump(mode="json")
    assert data["agent_trace"] == ["解析需求 -> 蓝牙耳机 · ¥400-600"]
    assert data["memory_context"]["matched_signals"]["has_match"] is True
    assert data["effective_query"] == "蓝牙耳机 华为 降噪"
    assert data["skill_runs"][0]["skill_name"] == "jd_search"
    assert data["skill_runs"][0]["wait_seconds"] == 12.0
    assert data["skill_runs"][0]["control_seconds"] == 70.0
    assert data["skill_runs"][0]["extract_seconds"] == 12.0
    assert data["products"][0]["recommendation_reason"] == "命中你常看的华为品牌"
