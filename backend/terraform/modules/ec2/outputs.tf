output "public_ip" {
  description = "Public IP address of the EC2 instance."
  value       = var.enable_ec2 ? aws_instance.main[0].public_ip : null
}

output "instance_id" {
  description = "Instance ID of the EC2 instance."
  value       = var.enable_ec2 ? aws_instance.main[0].id : null
}
