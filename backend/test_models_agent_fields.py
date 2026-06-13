from datetime import datetime

from models import ParsedQuery, Product, SearchResult


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


def test_search_result_serializes_agent_metadata():
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
        memory_context={"preferred_brands": [{"brand": "华为", "score": 0.9}]},
        effective_query="蓝牙耳机 华为 降噪",
        created_at=datetime.now(),
    )

    data = result.model_dump(mode="json")
    assert data["agent_trace"] == ["解析需求 -> 蓝牙耳机 · ¥400-600"]
    assert data["memory_context"]["preferred_brands"][0]["brand"] == "华为"
    assert data["effective_query"] == "蓝牙耳机 华为 降噪"
    assert data["products"][0]["recommendation_reason"] == "命中你常看的华为品牌"
