variable "enabled" {
  type = bool
  default = false
}
variable "approved_change" {
  type = bool
  default = false
}
variable "aws_region" {
  type = string
  default = "us-east-2"
}
variable "vpc_id" { type = string }
variable "private_subnet_id" { type = string }
variable "private_route_table_ids" {
  type = list(string)
}
variable "ami_id" {
  type = string
  description = "Approved private Ubuntu image, SSM agent, Python venv installed"
}
variable "instance_type" {
  type = string
  default = "t3.small"
}
variable "existing_instance_profile_name" {
  type = string
}
variable "enable_s3_gateway" {
  type = bool
  default = true
}
