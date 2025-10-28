#!/usr/bin/env python3
"""Multi-threaded Test Consumers - Addition Topic

3개의 Consumer를 멀티스레드로 동시 실행
"""

import json
import threading
import time
from confluent_kafka import Consumer, KafkaError

BOOTSTRAP_SERVERS = "kafka1:19092,kafka2:29092,kafka3:39092"
GROUP_ID = "addition-calculator-group"
TOPIC = "addition"

# Consumer별 처리 시간 (lag 생성용)
CONSUMER_DELAYS = {
    "addition-consumer-1": 0.1,  # 빠름
    "addition-consumer-2": 0.15,  # 보통
    "addition-consumer-3": 0.5,  # 느림 (lag 생성)
}


def process_message(consumer_id: str, msg_value: str, delay: float) -> None:
    """메시지 처리: JSON 파싱 후 더하기"""
    try:
        data = json.loads(msg_value)
        a = data.get("a", 0)
        b = data.get("b", 0)
        result = a + b
        print(f"✅ {consumer_id} | a={a}, b={b} → {result}")

        # 처리 시뮬레이션 (각 Consumer별 다른 속도)
        time.sleep(delay)

    except json.JSONDecodeError:
        print(f"❌ {consumer_id} | Invalid JSON: {msg_value}")
    except Exception as e:
        print(f"❌ {consumer_id} | Error: {e}")


def run_consumer(consumer_id: str, delay: float, stop_event: threading.Event) -> None:
    """Consumer 스레드 실행 함수"""
    config = {
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": GROUP_ID,
        "client.id": consumer_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 1000,
        "session.timeout.ms": 30000,
    }

    consumer = Consumer(config)
    consumer.subscribe([TOPIC])

    print(f"🚀 {consumer_id} started (delay={delay}s)")

    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"📭 {consumer_id} | End of partition {msg.partition()}")
                else:
                    print(f"❌ {consumer_id} | Error: {msg.error()}")
                continue

            # 메시지 처리
            msg_value = msg.value().decode("utf-8")
            print(f"📨 {consumer_id} | P{msg.partition()} | Offset {msg.offset()}")
            process_message(consumer_id, msg_value, delay)

    except Exception as e:
        print(f"❌ {consumer_id} | Thread error: {e}")
    finally:
        consumer.close()
        print(f"✅ {consumer_id} closed")


def main():
    print("=" * 70)
    print("🎯 Starting 3 Consumers in same group with different speeds")
    print("=" * 70)
    print(f"Group: {GROUP_ID}")
    print(f"Topic: {TOPIC}")
    print(f"Bootstrap: {BOOTSTRAP_SERVERS}")
    print("-" * 70)

    stop_event = threading.Event()
    threads: list[threading.Thread] = []

    # 3개의 Consumer 스레드 시작
    for consumer_id, delay in CONSUMER_DELAYS.items():
        thread = threading.Thread(
            target=run_consumer,
            args=(consumer_id, delay, stop_event),
            daemon=True,
            name=consumer_id,
        )
        thread.start()
        threads.append(thread)
        time.sleep(0.5)  # 스레드 시작 간격

    print("-" * 70)
    print("✅ All 3 consumers started!")
    print("⚠️  Press Ctrl+C to stop all consumers")
    print("=" * 70)

    try:
        # 메인 스레드에서 대기
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("👋 Shutting down all consumers...")
        print("=" * 70)
        stop_event.set()

        # 모든 스레드 종료 대기
        for thread in threads:
            thread.join(timeout=5)
            print(f"✅ {thread.name} stopped")

        print("=" * 70)
        print("✅ All consumers closed")
        print("=" * 70)


if __name__ == "__main__":
    main()
