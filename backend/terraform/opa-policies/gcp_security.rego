# opa-policies/gcp_security.rego
# Phase 4 stub — GCP secure vault / storage policy hooks (extend in later phases).

package gcp.security

import rego.v1

warn contains msg if {
    input.bucket_public == true
    msg := "WARN [opa_gcp_public_bucket]: GCS bucket allows public access."
}

warn contains msg if {
    input.default_encryption == false
    msg := "WARN [opa_gcp_no_encryption]: GCS bucket has no default encryption configured."
}
