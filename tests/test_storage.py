from datetime import datetime, timedelta, timezone

import pytest

from detection.risk_score import RiskScore
from detection.storage import get_latest_scores, init_db, save_scores


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "ledgerlens.db")


def _score(wallet="GABC", asset_pair="XLM/USDC", score=80, timestamp=None) -> RiskScore:
    return RiskScore(
        wallet=wallet,
        asset_pair=asset_pair,
        score=score,
        benford_flag=score > 50,
        ml_flag=score > 50,
        confidence=90,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


def test_init_db_creates_table(db_path):
    init_db(db_path)
    assert get_latest_scores(db_path=db_path) == []


def test_save_and_get_latest_scores(db_path):
    save_scores([_score()], db_path)
    scores = get_latest_scores(db_path=db_path)
    assert len(scores) == 1
    assert scores[0].wallet == "GABC"
    assert scores[0].score == 80


def test_get_latest_scores_returns_most_recent_per_wallet_asset_pair(db_path):
    older = _score(score=30, timestamp=datetime.now(timezone.utc) - timedelta(hours=1))
    newer = _score(score=90, timestamp=datetime.now(timezone.utc))
    save_scores([older, newer], db_path)

    scores = get_latest_scores(db_path=db_path)
    assert len(scores) == 1
    assert scores[0].score == 90


def test_get_latest_scores_filters_by_wallet(db_path):
    save_scores([_score(wallet="GABC"), _score(wallet="GXYZ")], db_path)

    scores = get_latest_scores(wallet="GXYZ", db_path=db_path)
    assert len(scores) == 1
    assert scores[0].wallet == "GXYZ"


def test_save_scores_noop_on_empty_list(db_path):
    save_scores([], db_path)
    assert get_latest_scores(db_path=db_path) == []
