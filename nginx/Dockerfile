FROM nginx:alpine

# 커스텀 nginx 설정 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 기본 nginx.conf 최적화
RUN echo 'worker_processes auto;' > /etc/nginx/nginx.conf && \
    echo 'error_log /var/log/nginx/error.log warn;' >> /etc/nginx/nginx.conf && \
    echo 'pid /var/run/nginx.pid;' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo 'events {' >> /etc/nginx/nginx.conf && \
    echo '    worker_connections 1024;' >> /etc/nginx/nginx.conf && \
    echo '    use epoll;' >> /etc/nginx/nginx.conf && \
    echo '    multi_accept on;' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo 'http {' >> /etc/nginx/nginx.conf && \
    echo '    include /etc/nginx/mime.types;' >> /etc/nginx/nginx.conf && \
    echo '    default_type application/octet-stream;' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo '    # 로그 포맷' >> /etc/nginx/nginx.conf && \
    echo '    log_format main' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'$remote_addr - $remote_user [$time_local] "$request" '"'"'' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'$status $body_bytes_sent "$http_referer" '"'"'' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'"$http_user_agent" "$http_x_forwarded_for" '"'"'' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'upstream: $upstream_addr '"'"'' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'upstream_status: $upstream_status '"'"'' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'request_time: $request_time '"'"'' >> /etc/nginx/nginx.conf && \
    echo '        '"'"'upstream_response_time: $upstream_response_time'"'"';' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo '    access_log /var/log/nginx/access.log main;' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo '    # 성능 최적화' >> /etc/nginx/nginx.conf && \
    echo '    sendfile on;' >> /etc/nginx/nginx.conf && \
    echo '    tcp_nopush on;' >> /etc/nginx/nginx.conf && \
    echo '    tcp_nodelay on;' >> /etc/nginx/nginx.conf && \
    echo '    keepalive_timeout 65;' >> /etc/nginx/nginx.conf && \
    echo '    types_hash_max_size 2048;' >> /etc/nginx/nginx.conf && \
    echo '    server_tokens off;' >> /etc/nginx/nginx.conf && \
    echo '' >> /etc/nginx/nginx.conf && \
    echo '    include /etc/nginx/conf.d/*.conf;' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf

# 로그 디렉토리 생성
RUN mkdir -p /var/log/nginx

# 헬스 체크용 curl 및 Basic Auth용 apache2-utils 설치
RUN apk add --no-cache curl apache2-utils

# Basic Auth용 .htpasswd 파일 생성 (선택적)
# 환경변수로 사용자명/비밀번호 설정 가능
# 기본값: admin / changeme (반드시 변경 필요!)
ARG DOCS_AUTH_USER=admin
ARG DOCS_AUTH_PASSWORD=changeme
RUN htpasswd -bc /etc/nginx/.htpasswd ${DOCS_AUTH_USER} ${DOCS_AUTH_PASSWORD}

# 포트 노출
EXPOSE 80

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# nginx 실행
CMD ["nginx", "-g", "daemon off;"]
