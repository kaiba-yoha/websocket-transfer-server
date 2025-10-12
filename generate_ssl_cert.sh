#!/bin/bash

# SSL証明書生成スクリプト
# 開発・テスト用の自己署名証明書を生成します

set -e

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 証明書ディレクトリを作成
CERT_DIR="ssl_certs"
mkdir -p "$CERT_DIR"

log_info "SSL証明書を生成中..."

# 自己署名証明書を生成
openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" -days 365 -nodes \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=WebSocketTransferServer/OU=Development/CN=localhost"

# 証明書の権限を設定
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

log_info "SSL証明書の生成が完了しました:"
log_info "  証明書ファイル: $CERT_DIR/server.crt"
log_info "  秘密鍵ファイル: $CERT_DIR/server.key"
log_warn "注意: これは自己署名証明書です。本番環境では正式な証明書を使用してください。"

echo ""
echo "使用方法:"
echo "  python3 server.py --cert $CERT_DIR/server.crt --key $CERT_DIR/server.key"
echo ""
echo "クライアント接続例:"
echo "  wss://localhost:8675"
echo "  wss://localhost:8775"
