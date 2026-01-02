---
name: terraform-iac
description: Infrastructure as Code with Terraform
version: 1.0.0
tags: [terraform, iac, aws, infrastructure]
size: atomic
domain: devops
---

# Terraform IaC

## Basic Structure

```hcl
# main.tf
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }

  backend "s3" {
    bucket         = "myapp-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}
```

## VPC Module

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "myapp-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true  # Cost saving for dev
}
```

## EKS Cluster

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.0.0"

  cluster_name    = "myapp-cluster"
  cluster_version = "1.28"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  eks_managed_node_groups = {
    main = {
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3
    }
  }
}
```

## Variables

```hcl
# variables.tf
variable "region" {
  default = "us-east-1"
}

variable "environment" {
  type = string
}

# terraform.tfvars
environment = "production"
```

## Commands

```bash
terraform init       # Initialize
terraform plan       # Preview changes
terraform apply      # Apply changes
terraform destroy    # Destroy resources
```
