#!/usr/bin/env bash
# Create Cloud Armor Security Policy for CUIDA+Care Command Center
# Based on document: 27 security mentions, OWASP Top 10, DDoS protection

set -e

PROJECT_ID="adc-agent"
POLICY_NAME="cuida-care-security-policy"

echo "🔐 Creating Cloud Armor Security Policy: $POLICY_NAME"
echo "=================================================="

# Create base security policy
echo "📝 Creating base security policy..."
gcloud compute security-policies create $POLICY_NAME \
  --description "CUIDA+Care Command Center - OWASP Top 10 + DDoS + Rate Limiting" \
  --project $PROJECT_ID

echo "✅ Base policy created"

# Rule 1: Rate Limiting - 100 req/min per IP
echo ""
echo "🚦 Adding rate limiting rule (100 req/min per IP)..."
gcloud compute security-policies rules create 1000 \
  --security-policy $POLICY_NAME \
  --action "rate-based-ban" \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60 \
  --conform-action allow \
  --exceed-action "deny-403" \
  --enforce-on-key IP \
  --ban-duration-sec 600 \
  --project $PROJECT_ID

echo "✅ Rate limiting rule added"

# Rule 2: SQL Injection Protection (OWASP)
echo ""
echo "🛡️  Adding OWASP SQL Injection protection..."
gcloud compute security-policies rules create 3000 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('sqli-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block SQL Injection" \
  --project $PROJECT_ID

echo "✅ SQL Injection protection added"

# Rule 3: XSS Protection (OWASP)
echo ""
echo "🛡️  Adding OWASP XSS protection..."
gcloud compute security-policies rules create 3100 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('xss-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block XSS" \
  --project $PROJECT_ID

echo "✅ XSS protection added"

# Rule 4: Local File Inclusion (OWASP)
echo ""
echo "🛡️  Adding OWASP LFI protection..."
gcloud compute security-policies rules create 3200 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('lfi-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block Local File Inclusion" \
  --project $PROJECT_ID

echo "✅ LFI protection added"

# Rule 5: Remote File Inclusion (OWASP)
echo ""
echo "🛡️  Adding OWASP RFI protection..."
gcloud compute security-policies rules create 3300 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('rfi-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block Remote File Inclusion" \
  --project $PROJECT_ID

echo "✅ RFI protection added"

# Rule 6: Remote Code Execution (OWASP)
echo ""
echo "🛡️  Adding OWASP RCE protection..."
gcloud compute security-policies rules create 3400 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('rce-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block Remote Code Execution" \
  --project $PROJECT_ID

echo "✅ RCE protection added"

# Rule 7: Method Enforcement (OWASP)
echo ""
echo "🛡️  Adding OWASP Method Enforcement..."
gcloud compute security-policies rules create 3500 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('methodenforcement-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Enforce valid HTTP methods" \
  --project $PROJECT_ID

echo "✅ Method enforcement added"

# Rule 8: Scanner Detection (OWASP)
echo ""
echo "🛡️  Adding OWASP Scanner Detection..."
gcloud compute security-policies rules create 3600 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('scannerdetection-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block security scanners" \
  --project $PROJECT_ID

echo "✅ Scanner detection added"

# Rule 9: Protocol Attack (OWASP)
echo ""
echo "🛡️  Adding OWASP Protocol Attack protection..."
gcloud compute security-policies rules create 3700 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('protocolattack-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block protocol attacks" \
  --project $PROJECT_ID

echo "✅ Protocol attack protection added"

# Rule 10: Session Fixation (OWASP)
echo ""
echo "🛡️  Adding OWASP Session Fixation protection..."
gcloud compute security-policies rules create 3800 \
  --security-policy $POLICY_NAME \
  --expression "evaluatePreconfiguredExpr('sessionfixation-v33-stable')" \
  --action "deny-403" \
  --description "OWASP: Block session fixation" \
  --project $PROJECT_ID

echo "✅ Session fixation protection added"

# Enable Adaptive Protection (DDoS)
echo ""
echo "🌐 Enabling Adaptive Protection (DDoS)..."
gcloud compute security-policies update $POLICY_NAME \
  --enable-layer7-ddos-defense \
  --layer7-ddos-defense-rule-visibility=STANDARD \
  --project $PROJECT_ID

echo "✅ Adaptive Protection (DDoS) enabled"

# Set logging
echo ""
echo "📊 Configuring logging..."
gcloud compute security-policies update $POLICY_NAME \
  --log-level=NORMAL \
  --project $PROJECT_ID

echo "✅ Logging configured"

echo ""
echo "=================================================="
echo "✅ Cloud Armor Security Policy Created Successfully!"
echo "=================================================="
echo ""
echo "📋 Policy Summary:"
echo "  - Policy Name: $POLICY_NAME"
echo "  - Rate Limiting: 100 req/min per IP (10min ban)"
echo "  - OWASP Rules: 9 rules (SQL Injection, XSS, LFI, RFI, RCE, etc.)"
echo "  - Adaptive Protection: DDoS defense enabled"
echo "  - Logging: NORMAL level"
echo ""
echo "🔗 View policy:"
echo "  gcloud compute security-policies describe $POLICY_NAME --project=$PROJECT_ID"
echo ""
echo "📈 Next steps:"
echo "  1. Attach policy to backend service or Cloud Run"
echo "  2. Monitor Cloud Armor logs in Cloud Logging"
echo "  3. Adjust rules based on traffic patterns"
echo "  4. Add geographic restrictions if needed"
