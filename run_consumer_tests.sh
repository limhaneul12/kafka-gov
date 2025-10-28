#!/bin/bash

# Consumer 모듈 테스트 실행 스크립트

set -e

echo "=========================================="
echo "Consumer 모듈 테스트 실행"
echo "=========================================="

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 옵션 파싱
COVERAGE=false
VERBOSE=false
PARALLEL=false
FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --coverage|-c)
      COVERAGE=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --parallel|-p)
      PARALLEL=true
      shift
      ;;
    --file|-f)
      FILE="$2"
      shift 2
      ;;
    --help|-h)
      echo "사용법: $0 [옵션]"
      echo ""
      echo "옵션:"
      echo "  -c, --coverage    커버리지 리포트 생성"
      echo "  -v, --verbose     상세 출력"
      echo "  -p, --parallel    병렬 실행 (pytest-xdist)"
      echo "  -f, --file FILE   특정 파일만 실행"
      echo "  -h, --help        도움말 표시"
      echo ""
      echo "예시:"
      echo "  $0                            # 기본 실행"
      echo "  $0 -c                         # 커버리지 포함"
      echo "  $0 -f test_use_cases.py      # 특정 파일만"
      echo "  $0 -c -v -p                   # 모든 옵션 활성화"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# pytest 명령어 구성
PYTEST_CMD="pytest tests/consumer/"

if [ -n "$FILE" ]; then
  PYTEST_CMD="pytest tests/consumer/$FILE"
fi

if [ "$VERBOSE" = true ]; then
  PYTEST_CMD="$PYTEST_CMD -vv"
else
  PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$PARALLEL" = true ]; then
  PYTEST_CMD="$PYTEST_CMD -n auto"
fi

if [ "$COVERAGE" = true ]; then
  PYTEST_CMD="$PYTEST_CMD --cov=app.consumer --cov-report=html:htmlcov/consumer --cov-report=term-missing"
fi

# 테스트 실행
echo -e "${BLUE}실행 명령어: $PYTEST_CMD${NC}"
echo ""

$PYTEST_CMD

# 결과 확인
if [ $? -eq 0 ]; then
  echo ""
  echo -e "${GREEN}=========================================="
  echo -e "✅ 모든 테스트 통과!"
  echo -e "==========================================${NC}"
  
  if [ "$COVERAGE" = true ]; then
    echo ""
    echo -e "${YELLOW}커버리지 리포트: htmlcov/consumer/index.html${NC}"
  fi
else
  echo ""
  echo -e "${RED}=========================================="
  echo -e "❌ 테스트 실패"
  echo -e "==========================================${NC}"
  exit 1
fi
