variable "enable_ec2" {
  description = "Whether to create an EC2 instance."
  type        = bool
  default     = false
}

variable "instance_type" {
  description = "EC2 instance type. Use t2.micro for free tier."
  type        = string
  default     = "t2.micro"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance. Use a region-appropriate Amazon Linux 2 AMI."
  type        = string
  default     = ""
}

variable "instance_name" {
  description = "Name tag for the EC2 instance."
  type        = string
  default     = "main-instance"
}

variable "subnet_id" {
  description = "Subnet ID to launch the EC2 instance in."
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "VPC ID for the security group. Required when EC2 is enabled."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to all resources for cost attribution and governance."
  type        = map(string)
  default     = {}
}
