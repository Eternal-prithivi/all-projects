# opa-policies/aws_security.rego
# OPA Rego policy file for AWS infrastructure security rules.
# These policies AUGMENT the YAML rules engine (they do not replace it).
# The YAML engine handles simple key-value checks.
# OPA handles richer, combinatorial logic and cross-field reasoning.

package aws.security

import rego.v1

# ─────────────────────────────────────────────
# BLOCK-LEVEL VIOLATIONS
# ─────────────────────────────────────────────

# Block: S3 bucket is publicly accessible
deny contains msg if {
    input.s3_bucket_public == true
    msg := "BLOCK [opa_public_s3]: S3 bucket is publicly accessible. This is a critical security violation."
}

# Block: SSH (port 22) is open to the world
deny contains msg if {
    input.ssh_open_to_world == true
    msg := "BLOCK [opa_open_ssh]: SSH port 22 is open to 0.0.0.0/0. This exposes the server to brute-force attacks."
}

# Block: RDP (port 3389) is open to the world
deny contains msg if {
    input.rdp_open_to_world == true
    msg := "BLOCK [opa_open_rdp]: RDP port 3389 is open to 0.0.0.0/0. This is a critical security risk."
}

# Block: IAM wildcard permissions
deny contains msg if {
    input.iam_wildcard == true
    msg := "BLOCK [opa_iam_wildcard]: IAM policy contains wildcard (*) permissions. Use least-privilege access."
}

# ─────────────────────────────────────────────
# COMBINED RISK RULES (OPA-only — not possible in YAML engine)
# ─────────────────────────────────────────────

# Block: Public S3 + no encryption is a CRITICAL combined risk
deny contains msg if {
    input.s3_bucket_public == true
    input.s3_encryption == false
    msg := "BLOCK [opa_public_unencrypted_s3]: CRITICAL — S3 bucket is both public AND unencrypted. Data is fully exposed."
}

# Block: Production deployment with CloudTrail disabled AND no tags
deny contains msg if {
    input.cloudtrail_enabled == false
    count(input.tags) == 0
    input.environment == "production"
    msg := "BLOCK [opa_production_no_audit]: Production deployment has no CloudTrail AND no resource tags. Cannot audit or attribute costs."
}

# ─────────────────────────────────────────────
# WARNING-LEVEL ADVISORIES
# ─────────────────────────────────────────────

warn contains msg if {
    input.cloudtrail_enabled == false
    msg := "WARN [opa_cloudtrail_disabled]: CloudTrail is not enabled. All API calls will be unaudited."
}

warn contains msg if {
    input.s3_encryption == false
    msg := "WARN [opa_s3_no_encryption]: S3 bucket has no server-side encryption. Sensitive data may be exposed."
}

warn contains msg if {
    count(input.tags) == 0
    msg := "WARN [opa_missing_tags]: No resource tags defined. Cost attribution and governance will be impossible."
}

# Warn: Expensive EC2 instance in production
warn contains msg if {
    not input.instance_type in {"t2.micro", "t3.micro", "t3.nano", "t3a.micro"}
    msg := sprintf("WARN [opa_expensive_ec2]: Instance type '%v' is not free-tier eligible.", [input.instance_type])
}

# ─────────────────────────────────────────────
# SUMMARY HELPERS
# ─────────────────────────────────────────────

# True if any block-level violations exist
is_blocked if {
    count(deny) > 0
}

# True if any warnings exist
has_warnings if {
    count(warn) > 0
}
