variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "enabled" {
  type        = bool
  default     = false
  description = "Explicitly opt in to billable EC2 provisioning"
}

variable "ami_id" {
  type    = string
  default = ""
}

variable "vpc_id" {
  type    = string
  default = ""
}

variable "private_subnet_id" {
  type    = string
  default = ""
}

variable "existing_instance_profile_name" {
  type    = string
  default = ""
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "egress_cidr" {
  type        = string
  default     = "0.0.0.0/0"
  description = "HTTPS-only egress; scope to an approved CIDR for production"
}
