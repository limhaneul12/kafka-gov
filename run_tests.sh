#!/bin/bash

# Topic 모듈 테스트 실행 스크립트

echo "🧪 Topic 모듈 테스트 시작..."

# 1. 도메인 모델 테스트
echo "📋 1. 도메인 모델 테스트 실행"
uv run pytest tests/topic/domain/test_models.py -v

# 2. 유스케이스 테스트  
echo "🎯 2. 유스케이스 테스트 실행"
uv run pytest tests/topic/application/test_use_cases.py -v

# 3. 인프라스트럭처 테스트
echo "🔧 3. 인프라스트럭처 테스트 실행"
uv run pytest tests/topic/infrastructure/test_mysql_repository.py -v

# 4. 전체 Topic 모듈 테스트 및 커버리지
echo "📊 4. 전체 Topic 모듈 테스트 및 커버리지"
uv run pytest tests/topic/ -v --cov=app.topic --cov-report=html:htmlcov/topic --cov-report=term-missing

echo "✅ 테스트 완료!"
echo "📈 커버리지 리포트: htmlcov/topic/index.html"
