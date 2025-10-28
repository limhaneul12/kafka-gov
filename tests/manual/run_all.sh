#!/bin/bash
# 모든 Consumer와 Producer를 한 번에 실행
# 각각 별도의 터미널 탭에서 실행됩니다 (macOS용)

echo "🚀 Starting all test consumers and producer..."
echo ""

# macOS Terminal에서 새 탭으로 실행
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Consumer 1
    osascript -e 'tell application "Terminal" to do script "cd '"$PWD"' && uv run python test_consumer_1.py"'
    sleep 1
    
    # Consumer 2
    osascript -e 'tell application "Terminal" to do script "cd '"$PWD"' && uv run python test_consumer_2.py"'
    sleep 1
    
    # Consumer 3
    osascript -e 'tell application "Terminal" to do script "cd '"$PWD"' && uv run python test_consumer_3.py"'
    sleep 1
    
    # Producer
    osascript -e 'tell application "Terminal" to do script "cd '"$PWD"' && uv run python test_producer.py"'
    
    echo "✅ All processes started in separate Terminal tabs!"
    echo "⚠️  Press Ctrl+C in each tab to stop"
else
    echo "❌ This script is designed for macOS Terminal"
    echo "Please run each script manually in separate terminals:"
    echo ""
    echo "Terminal 1: uv run python test_consumer_1.py"
    echo "Terminal 2: uv run python test_consumer_2.py"
    echo "Terminal 3: uv run python test_consumer_3.py"
    echo "Terminal 4: uv run python test_producer.py"
fi
