# modules/ec2/main.tf — EC2 Instance (default: t2.micro free tier)
# SECURITY: SSH port 22 is NOT open to 0.0.0.0/0 — policy engine blocks that.

# Auto-detect the latest Amazon Linux 2 AMI for the current region
# Used as fallback when ami_id is not provided
data "aws_ami" "amazon_linux_2" {
  count       = var.enable_ec2 && var.ami_id == "" ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_security_group" "ec2_sg" {
  count       = var.enable_ec2 ? 1 : 0
  name        = "ec2-security-group"
  description = "Security group for EC2 instance. No unrestricted inbound access."
  vpc_id      = var.vpc_id

  egress {
    description = "Allow all outbound traffic."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "ec2-sg"
  })
}

resource "aws_instance" "main" {
  count                  = var.enable_ec2 ? 1 : 0
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux_2[0].id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.ec2_sg[0].id]

  tags = merge(var.tags, {
    Name = var.instance_name
  })
}
