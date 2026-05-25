output "vpc_id" {
  description = "ID of the created VPC."
  value       = var.enable_vpc ? aws_vpc.main[0].id : null
}

output "public_subnet_id" {
  description = "ID of the public subnet."
  value       = var.enable_vpc ? aws_subnet.public[0].id : null
}

output "private_subnet_id" {
  description = "ID of the private subnet."
  value       = var.enable_vpc ? aws_subnet.private[0].id : null
}
