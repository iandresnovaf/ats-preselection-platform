#!/bin/bash
# ============================================================
# Script de verificación de seguridad local
# Uso: ./scripts/security-check.sh [--full]
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FULL_SCAN=false
REPORTS_DIR="security-reports"

# Parse arguments
if [ "$1" = "--full" ]; then
    FULL_SCAN=true
fi

# Crear directorio de reportes
mkdir -p $REPORTS_DIR

echo "=========================================="
echo "🔒 ATS Platform Security Check"
echo "=========================================="
echo ""

# ==================== Backend SAST ====================
echo "📦 [1/7] Running Bandit (SAST)..."
cd backend
pip install -q bandit[toml] 2>/dev/null || true
if command -v bandit &> /dev/null; then
    bandit -r app -c ../.bandit -f txt -o ../$REPORTS_DIR/bandit-report.txt || true
    bandit -r app -c ../.bandit -f screen || true
    echo -e "${GREEN}✅ Bandit scan complete${NC}"
else
    echo -e "${YELLOW}⚠️ Bandit not installed. Run: pip install bandit[toml]${NC}"
fi
cd ..

# ==================== Backend SCA ====================
echo ""
echo "📦 [2/7] Running Safety (SCA)..."
pip install -q safety 2>/dev/null || true
if command -v safety &> /dev/null; then
    safety check -r backend/requirements.txt --json --output $REPORTS_DIR/safety-report.json || true
    safety check -r backend/requirements.txt || true
    echo -e "${GREEN}✅ Safety scan complete${NC}"
else
    echo -e "${YELLOW}⚠️ Safety not installed. Run: pip install safety${NC}"
fi

# ==================== pip-audit ====================
echo ""
echo "📦 [3/7] Running pip-audit..."
pip install -q pip-audit 2>/dev/null || true
if command -v pip-audit &> /dev/null; then
    pip-audit -r backend/requirements.txt --format=json --output=$REPORTS_DIR/pip-audit-report.json || true
    pip-audit -r backend/requirements.txt || true
    echo -e "${GREEN}✅ pip-audit complete${NC}"
else
    echo -e "${YELLOW}⚠️ pip-audit not installed. Run: pip install pip-audit${NC}"
fi

# ==================== Frontend SCA ====================
echo ""
echo "📦 [4/7] Running npm audit..."
cd frontend
if [ -f package-lock.json ]; then
    npm audit --audit-level=moderate --json > ../$REPORTS_DIR/npm-audit-report.json 2>/dev/null || true
    npm audit --audit-level=moderate || true
    echo -e "${GREEN}✅ npm audit complete${NC}"
else
    echo -e "${YELLOW}⚠️ package-lock.json not found${NC}"
fi
cd ..

# ==================== Secret Detection ====================
echo ""
echo "📦 [5/7] Running secret detection..."
pip install -q detect-secrets 2>/dev/null || true
if command -v detect-secrets &> /dev/null; then
    detect-secrets scan --all-files --force-use-all-plugins > $REPORTS_DIR/secrets-report.json 2>/dev/null || true
    echo -e "${GREEN}✅ Secret detection complete${NC}"
else
    echo -e "${YELLOW}⚠️ detect-secrets not installed. Run: pip install detect-secrets${NC}"
fi

# ==================== Dependency Check ====================
if [ "$FULL_SCAN" = true ]; then
    echo ""
    echo "📦 [6/7] Running OWASP Dependency-Check..."
    if command -v dependency-check &> /dev/null; then
        dependency-check --project "ATS Platform" --scan backend/requirements.txt --format JSON --out $REPORTS_DIR/dependency-check-report.json || true
        echo -e "${GREEN}✅ Dependency-Check complete${NC}"
    else
        echo -e "${YELLOW}⚠️ dependency-check not installed${NC}"
    fi
fi

# ==================== Semgrep ====================
if [ "$FULL_SCAN" = true ]; then
    echo ""
    echo "📦 [7/7] Running Semgrep..."
    pip install -q semgrep 2>/dev/null || true
    if command -v semgrep &> /dev/null; then
        semgrep --config=auto . --json -o $REPORTS_DIR/semgrep-report.json || true
        semgrep --config=auto backend/app frontend/src || true
        echo -e "${GREEN}✅ Semgrep scan complete${NC}"
    else
        echo -e "${YELLOW}⚠️ semgrep not installed. Run: pip install semgrep${NC}"
    fi
fi

# ==================== Summary ====================
echo ""
echo "=========================================="
echo "📊 Security Check Summary"
echo "=========================================="
echo ""
echo "Reports generated in: $REPORTS_DIR/"
ls -lh $REPORTS_DIR/ 2>/dev/null || echo "No reports generated"
echo ""
echo -e "${GREEN}✅ Security checks completed!${NC}"
echo ""
echo "Next steps:"
echo "  - Review reports in $REPORTS_DIR/"
echo "  - Fix critical and high severity issues"
echo "  - Run with --full for complete scan"
echo ""
