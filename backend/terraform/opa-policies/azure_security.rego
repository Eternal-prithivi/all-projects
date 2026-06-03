# opa-policies/azure_security.rego
# Phase 4 stub — Azure secure vault / storage policy hooks (extend in later phases).

package azure.security

import rego.v1

warn contains msg if {
    input.container_public == true
    msg := "WARN [opa_azure_public_container]: Storage container allows public blob access."
}

warn contains msg if {
    input.encryption_at_rest == false
    msg := "WARN [opa_azure_no_encryption]: Storage account lacks encryption-at-rest for blobs."
}
