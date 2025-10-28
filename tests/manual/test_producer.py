#!/usr/bin/env python3
"""Test Producer - Addition Topic

addition 토픽에 더하기 문제 메시지 생성
"""

import json
import random
import time
from confluent_kafka import Producer

# Producer 설정
PRODUCER_CONFIG = {
    "bootstrap.servers": "kafka1:19092,kafka2:29092,kafka3:39092",
    "client.id": "addition-producer",
}

TOPIC = "addition"


def delivery_callback(err, msg):
    """메시지 전송 콜백"""
    if err:
        print(f"❌ Failed to deliver message: {err}")
    else:
        print(
            f"✅ Message delivered to {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()}"
        )


def produce_messages(producer: Producer, count: int = 100):
    """더하기 문제 메시지 생성"""
    print(f"🚀 Producing {count} messages to '{TOPIC}' topic...")
    print("-" * 60)

    for i in range(count):
        # 랜덤 더하기 문제
        a = random.randint(1, 100)
        b = random.randint(1, 100)

        message = {
            "id": i + 1,
            "a": a,
            "b": b,
            "timestamp": time.time(),
        }

        # 메시지 전송
        producer.produce(
            topic=TOPIC,
            value=json.dumps(message),
            callback=delivery_callback,
        )

        # 버퍼 플러시 (일부만)
        if i % 10 == 0:
            producer.poll(0)

        # 속도 조절 (초당 10개 정도)
        time.sleep(0.1)

    # 남은 메시지 전송 완료 대기
    print("\n⏳ Flushing remaining messages...")
    producer.flush()
    print(f"✅ All {count} messages sent!")


def main():
    producer = Producer(PRODUCER_CONFIG)

    try:
        # 기본 100개 메시지 생성
        produce_messages(producer, count=100)

        # 추가 메시지 계속 생성 (선택)
        print("\n" + "=" * 60)
        print("Continue producing? (Press Ctrl+C to stop)")
        print("=" * 60 + "\n")

        msg_id = 101
        while True:
            a = random.randint(1, 100)
            b = random.randint(1, 100)

            message = {
                "id": msg_id,
                "a": a,
                "b": b,
                "timestamp": time.time(),
            }

            producer.produce(
                topic=TOPIC,
                value=json.dumps(message),
                callback=delivery_callback,
            )
            producer.poll(0)

            msg_id += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n👋 Producer shutting down...")
    finally:
        producer.flush()
        print("✅ Producer closed")


if __name__ == "__main__":
    main()
