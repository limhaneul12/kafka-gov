import pytest
from pydantic import ValidationError

from app.topic.interface.schema import TopicBatchRequest
from app.topic.interface.types import Environment, TopicAction


def test_topic_batch_request_env_mismatch_triggers_validation_error():
    payload = {
        "env": Environment.PROD,
        "change_id": "chg-env-001",
        "items": [
            {
                "name": "stg.orders.created",  # env prefix mismatch vs env=prod
                "action": TopicAction.UPSERT,
                "config": {"partitions": 3, "replication_factor": 3},
                "metadata": {"owner": "team-commerce"},
            }
        ],
    }

    with pytest.raises(ValidationError) as exc:
        TopicBatchRequest.model_validate(payload)

    assert "does not match batch environment" in str(exc.value)
