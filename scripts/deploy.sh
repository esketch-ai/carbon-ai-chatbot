#!/bin/bash
# =============================================
# Carbon AI Chatbot - Synology NAS 배포 스크립트
# =============================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 환경 변수 확인
check_env() {
    log_info "환경 변수 확인 중..."

    if [ ! -f ".env" ]; then
        log_error ".env 파일이 없습니다. .env.example을 복사하고 설정하세요."
        log_info "  cp .env.example .env"
        exit 1
    fi

    source .env

    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-api03-your-key-here" ]; then
        log_error "ANTHROPIC_API_KEY가 설정되지 않았습니다."
        exit 1
    fi

    log_info "환경 변수 확인 완료"
}

# 디렉토리 생성
setup_directories() {
    log_info "데이터 디렉토리 생성 중..."
    mkdir -p data/knowledge_base
    mkdir -p data/chroma_db
    mkdir -p nginx/ssl
    log_info "디렉토리 생성 완료"
}

# Docker 이미지 빌드
build_images() {
    log_info "Docker 이미지 빌드 중..."

    docker-compose build --no-cache

    log_info "Docker 이미지 빌드 완료"
}

# 서비스 시작
start_services() {
    log_info "서비스 시작 중..."

    docker-compose up -d

    log_info "서비스 시작 완료"
}

# 서비스 중지
stop_services() {
    log_info "서비스 중지 중..."
    docker-compose down --remove-orphans
    log_info "서비스 중지 완료"
}

# 서비스 재시작
restart_services() {
    log_info "서비스 재시작 중..."
    docker-compose restart
    log_info "서비스 재시작 완료"
}

# 로그 보기
show_logs() {
    docker-compose logs -f --tail=100 "$@"
}

# 상태 확인
check_status() {
    log_info "서비스 상태 확인 중..."
    docker-compose ps

    echo ""
    log_info "헬스체크..."

    # 백엔드 체크
    if curl -sf http://localhost:${BACKEND_PORT:-7860}/ok > /dev/null 2>&1; then
        log_info "백엔드: ${GREEN}정상${NC}"
    else
        log_error "백엔드: 응답 없음"
    fi

    # 프론트엔드 체크
    if curl -sf http://localhost:${FRONTEND_PORT:-3000} > /dev/null 2>&1; then
        log_info "프론트엔드: ${GREEN}정상${NC}"
    else
        log_error "프론트엔드: 응답 없음"
    fi

    # Redis 체크
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_info "Redis: ${GREEN}정상${NC}"
    else
        log_warn "Redis: 응답 없음 (선택적 서비스)"
    fi
}

# 정리
cleanup() {
    log_info "정리 중..."
    docker system prune -f
    docker volume prune -f
    log_info "정리 완료"
}

# 전체 배포
full_deploy() {
    check_env
    setup_directories
    stop_services
    build_images
    start_services

    log_info "배포 완료 대기 중 (30초)..."
    sleep 30

    check_status
}

# 도움말
show_help() {
    echo "Carbon AI Chatbot 배포 스크립트"
    echo ""
    echo "사용법: $0 <명령>"
    echo ""
    echo "명령:"
    echo "  deploy     전체 배포 (빌드 + 시작)"
    echo "  build      Docker 이미지 빌드"
    echo "  start      서비스 시작"
    echo "  stop       서비스 중지"
    echo "  restart    서비스 재시작"
    echo "  status     상태 확인"
    echo "  logs       로그 보기 (예: $0 logs backend)"
    echo "  cleanup    Docker 정리"
    echo "  help       이 도움말 표시"
}

# 메인
case "${1:-help}" in
    deploy)
        full_deploy
        ;;
    build)
        check_env
        build_images
        ;;
    start)
        check_env
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_status
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    cleanup)
        cleanup
        ;;
    help|*)
        show_help
        ;;
esac
