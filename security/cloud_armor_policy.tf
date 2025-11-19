"""
Cloud Armor Security Policy Configuration
Based on document requirements: 27 mentions of security/Cloud Armor
Implements: WAF, DDoS protection, rate limiting, OWASP Top 10 rules
"""

# Cloud Armor Security Policy for CUIDA+Care Command Center
resource "google_compute_security_policy" "cuida_care_policy" {
  name        = "cuida-care-security-policy"
  description = "Cloud Armor policy for CUIDA+Care Command Center - OWASP Top 10 + Rate Limiting"

  # Rule 1: Rate Limiting - 100 requests per minute per IP
  rule {
    action   = "rate_based_ban"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 600  # 10 minutes ban
    }
    description = "Rate limit: 100 req/min per IP, ban for 10min"
  }

  # Rule 2: Block known malicious IPs
  rule {
    action   = "deny(403)"
    priority = 2000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = [
          # Add known malicious IP ranges here
          # Example: "192.0.2.0/24"
        ]
      }
    }
    description = "Block known malicious IPs"
  }

  # Rule 3: OWASP ModSecurity Core Rule Set - SQL Injection
  rule {
    action   = "deny(403)"
    priority = 3000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }
    description = "OWASP: Block SQL Injection attempts"
  }

  # Rule 4: OWASP - Cross-Site Scripting (XSS)
  rule {
    action   = "deny(403)"
    priority = 3100
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }
    description = "OWASP: Block XSS attempts"
  }

  # Rule 5: OWASP - Local File Inclusion (LFI)
  rule {
    action   = "deny(403)"
    priority = 3200
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('lfi-stable')"
      }
    }
    description = "OWASP: Block Local File Inclusion"
  }

  # Rule 6: OWASP - Remote File Inclusion (RFI)
  rule {
    action   = "deny(403)"
    priority = 3300
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rfi-stable')"
      }
    }
    description = "OWASP: Block Remote File Inclusion"
  }

  # Rule 7: OWASP - Remote Code Execution (RCE)
  rule {
    action   = "deny(403)"
    priority = 3400
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rce-stable')"
      }
    }
    description = "OWASP: Block Remote Code Execution"
  }

  # Rule 8: OWASP - Method Enforcement
  rule {
    action   = "deny(403)"
    priority = 3500
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('methodenforcement-stable')"
      }
    }
    description = "OWASP: Enforce valid HTTP methods"
  }

  # Rule 9: OWASP - Scanner Detection
  rule {
    action   = "deny(403)"
    priority = 3600
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('scannerdetection-stable')"
      }
    }
    description = "OWASP: Block security scanners"
  }

  # Rule 10: OWASP - Protocol Attack
  rule {
    action   = "deny(403)"
    priority = 3700
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('protocolattack-stable')"
      }
    }
    description = "OWASP: Block protocol attacks"
  }

  # Rule 11: OWASP - PHP Injection
  rule {
    action   = "deny(403)"
    priority = 3800
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('php-stable')"
      }
    }
    description = "OWASP: Block PHP injection"
  }

  # Rule 12: OWASP - Session Fixation
  rule {
    action   = "deny(403)"
    priority = 3900
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sessionfixation-stable')"
      }
    }
    description = "OWASP: Block session fixation"
  }

  # Rule 13: Geographic restriction (optional)
  # Uncomment to restrict to specific countries
  # rule {
  #   action   = "deny(403)"
  #   priority = 4000
  #   match {
  #     expr {
  #       expression = "origin.region_code != 'US' && origin.region_code != 'BR'"
  #     }
  #   }
  #   description = "Geographic restriction: Allow only US and BR"
  # }

  # Rule 14: Allow health check probes
  rule {
    action   = "allow"
    priority = 9000
    match {
      expr {
        expression = "request.path.matches('/health') || request.path.matches('/readiness')"
      }
    }
    description = "Allow health check endpoints"
  }

  # Default rule: Allow all other traffic
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule: Allow legitimate traffic"
  }

  # Adaptive Protection (DDoS)
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable          = true
      rule_visibility = "STANDARD"
    }
  }

  # Advanced options
  advanced_options_config {
    json_parsing = "STANDARD"
    log_level    = "NORMAL"
  }
}

# Output the security policy
output "security_policy_id" {
  value       = google_compute_security_policy.cuida_care_policy.id
  description = "Cloud Armor security policy ID"
}

output "security_policy_self_link" {
  value       = google_compute_security_policy.cuida_care_policy.self_link
  description = "Cloud Armor security policy self link"
}
