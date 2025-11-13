#!/usr/bin/env python3
"""
Validate CI/CD Pipeline Configuration
This script validates the entire CI/CD pipeline setup and configuration.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class PipelineValidator:
    """Validate CI/CD pipeline configuration and setup."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors = []
        self.warnings = []
        self.info = []
        
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating CI/CD Pipeline Configuration...")
        print("=" * 60)
        
        # Validate different components
        self.validate_github_workflows()
        self.validate_terraform_configuration()
        self.validate_docker_configuration()
        self.validate_code_quality_config()
        self.validate_testing_configuration()
        self.validate_monitoring_setup()
        self.validate_documentation()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def validate_github_workflows(self):
        """Validate GitHub Actions workflows."""
        print("📋 Validating GitHub Actions workflows...")
        
        workflows_dir = self.project_root / ".github" / "workflows"
        
        if not workflows_dir.exists():
            self.errors.append("GitHub workflows directory not found")
            return
            
        # Check required workflow files
        required_workflows = [
            "ci-cd.yml",
            "security.yml"
        ]
        
        for workflow in required_workflows:
            workflow_path = workflows_dir / workflow
            if not workflow_path.exists():
                self.errors.append(f"Required workflow not found: {workflow}")
            else:
                self.validate_workflow_file(workflow_path)
                
        self.info.append(f"✓ Found {len(list(workflows_dir.glob('*.yml')))} workflow files")
    
    def validate_workflow_file(self, workflow_path: Path):
        """Validate individual workflow file."""
        if not HAS_YAML:
            self.warnings.append(f"PyYAML not available, skipping full validation of {workflow_path.name}")
            # Basic text validation
            with open(workflow_path, 'r') as f:
                content = f.read()
                if 'name:' in content and 'on:' in content and 'jobs:' in content:
                    self.info.append(f"✓ Basic structure found in {workflow_path.name}")
                else:
                    self.errors.append(f"Missing basic workflow structure in {workflow_path.name}")
            return
            
        try:
            with open(workflow_path, 'r') as f:
                workflow = yaml.safe_load(f)
            
            # Check required sections
            required_sections = ['name', 'on', 'jobs']
            for section in required_sections:
                if section not in workflow:
                    self.errors.append(f"Missing section '{section}' in {workflow_path.name}")
            
            # Check for environment protection
            jobs = workflow.get('jobs', {})
            deployment_jobs = [
                job for job_name, job in jobs.items() 
                if 'environment' in job and 'production' in str(job.get('environment', {}))
            ]
            
            if deployment_jobs:
                self.info.append(f"✓ Production environment protection found in {workflow_path.name}")
            
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in {workflow_path.name}: {e}")
        except Exception as e:
            self.warnings.append(f"Could not fully parse {workflow_path.name}: {e}")
    
    def validate_terraform_configuration(self):
        """Validate Terraform configuration."""
        print("🏗️  Validating Terraform configuration...")
        
        terraform_dir = self.project_root / "infrastructure"
        
        if not terraform_dir.exists():
            self.errors.append("Infrastructure directory not found")
            return
        
        # Check directory structure
        required_dirs = [
            "modules",
            "environments/dev",
            "environments/staging", 
            "environments/prod",
            "ephemeral"
        ]
        
        for dir_path in required_dirs:
            full_path = terraform_dir / dir_path
            if not full_path.exists():
                self.errors.append(f"Required directory not found: infrastructure/{dir_path}")
            else:
                self.validate_terraform_environment(full_path)
        
        # Validate modules
        modules_dir = terraform_dir / "modules"
        if modules_dir.exists():
            required_module_files = [
                "main.tf",
                "variables.tf",
                "outputs.tf",
                "networking.tf",
                "ecs.tf"
            ]
            
            for file_name in required_module_files:
                file_path = modules_dir / file_name
                if not file_path.exists():
                    self.errors.append(f"Required module file not found: {file_name}")
        
        self.info.append("✓ Terraform structure validated")
    
    def validate_terraform_environment(self, env_path: Path):
        """Validate individual Terraform environment."""
        required_files = ["main.tf", "variables.tf", "outputs.tf"]
        
        for file_name in required_files:
            file_path = env_path / file_name
            if not file_path.exists():
                self.warnings.append(f"Missing {file_name} in {env_path.name}")
    
    def validate_docker_configuration(self):
        """Validate Docker configuration."""
        print("🐳 Validating Docker configuration...")
        
        # Check API Dockerfile
        api_dockerfile = self.project_root / "api" / "Dockerfile"
        if not api_dockerfile.exists():
            self.errors.append("API Dockerfile not found")
        else:
            self.validate_dockerfile(api_dockerfile, "API")
        
        # Check Frontend Dockerfile
        frontend_dockerfile = self.project_root / "frontend" / "Dockerfile"
        if not frontend_dockerfile.exists():
            self.errors.append("Frontend Dockerfile not found")
        else:
            self.validate_dockerfile(frontend_dockerfile, "Frontend")
        
        # Check docker-compose files
        compose_files = [
            "docker-compose.yml",
            "docker-compose.dev.yml",
            "docker-compose.production.yml"
        ]
        
        for compose_file in compose_files:
            compose_path = self.project_root / compose_file
            if compose_path.exists():
                self.validate_docker_compose(compose_path)
            else:
                self.warnings.append(f"Docker compose file not found: {compose_file}")
        
        self.info.append("✓ Docker configuration validated")
    
    def validate_dockerfile(self, dockerfile_path: Path, component: str):
        """Validate individual Dockerfile."""
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            # Check for security best practices
            if 'USER ' in content:
                self.info.append(f"✓ {component} Dockerfile uses non-root user")
            else:
                self.warnings.append(f"{component} Dockerfile should use non-root user")
            
            if 'HEALTHCHECK' in content:
                self.info.append(f"✓ {component} Dockerfile includes health check")
            else:
                self.warnings.append(f"{component} Dockerfile should include health check")
                
        except Exception as e:
            self.errors.append(f"Error reading {dockerfile_path}: {e}")
    
    def validate_docker_compose(self, compose_path: Path):
        """Validate docker-compose file."""
        if not HAS_YAML:
            self.warnings.append(f"PyYAML not available, skipping docker-compose validation of {compose_path.name}")
            return
            
        try:
            with open(compose_path, 'r') as f:
                compose = yaml.safe_load(f)
            
            # Check for health checks in services
            services = compose.get('services', {})
            for service_name, service_config in services.items():
                if 'healthcheck' in service_config:
                    self.info.append(f"✓ Service '{service_name}' has health check in {compose_path.name}")
                    
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in {compose_path.name}: {e}")
        except Exception as e:
            self.warnings.append(f"Could not parse {compose_path.name}: {e}")
    
    def validate_code_quality_config(self):
        """Validate code quality configuration."""
        print("✨ Validating code quality configuration...")
        
        # Check Python code quality files
        python_configs = [
            ".flake8",
            "pyproject.toml",
            ".bandit"
        ]
        
        for config_file in python_configs:
            config_path = self.project_root / config_file
            if not config_path.exists():
                self.warnings.append(f"Code quality config not found: {config_file}")
            else:
                self.info.append(f"✓ Found {config_file}")
        
        # Check Frontend configs
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            frontend_configs = [
                "eslint.config.js",
                "tsconfig.json",
                ".eslintrc.json"
            ]
            
            for config_file in frontend_configs:
                config_path = frontend_dir / config_file
                if config_path.exists():
                    self.info.append(f"✓ Found frontend/{config_file}")
        
        self.info.append("✓ Code quality configuration validated")
    
    def validate_testing_configuration(self):
        """Validate testing configuration."""
        print("🧪 Validating testing configuration...")
        
        # Check API tests
        api_dir = self.project_root / "api"
        if api_dir.exists():
            test_files = list(api_dir.glob("test_*.py"))
            if test_files:
                self.info.append(f"✓ Found {len(test_files)} API test files")
            else:
                self.warnings.append("No API test files found")
        
        # Check integration tests
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            integration_dir = tests_dir / "integration"
            if integration_dir.exists():
                integration_tests = list(integration_dir.glob("*.py"))
                self.info.append(f"✓ Found {len(integration_tests)} integration test files")
            else:
                self.warnings.append("No integration tests directory found")
        
        # Check Frontend tests
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            frontend_tests = list(frontend_dir.glob("**/*test*"))
            if frontend_tests:
                self.info.append(f"✓ Found frontend test files")
        
        self.info.append("✓ Testing configuration validated")
    
    def validate_monitoring_setup(self):
        """Validate monitoring and alerting setup."""
        print("📊 Validating monitoring setup...")
        
        # Check monitoring configuration
        monitoring_dir = self.project_root / "monitoring"
        if monitoring_dir.exists():
            monitoring_files = [
                "prometheus.yml",
                "alerts.yml"
            ]
            
            for config_file in monitoring_files:
                config_path = monitoring_dir / config_file
                if config_path.exists():
                    self.info.append(f"✓ Found monitoring/{config_file}")
                else:
                    self.warnings.append(f"Monitoring config not found: {config_file}")
        
        # Check for monitoring in Terraform
        terraform_modules = self.project_root / "infrastructure" / "modules"
        if terraform_modules.exists():
            monitoring_tf = terraform_modules / "monitoring.tf"
            if monitoring_tf.exists():
                self.info.append("✓ Terraform monitoring configuration found")
            else:
                self.warnings.append("No Terraform monitoring configuration")
        
        self.info.append("✓ Monitoring setup validated")
    
    def validate_documentation(self):
        """Validate documentation."""
        print("📚 Validating documentation...")
        
        # Check for required documentation
        required_docs = [
            "README.md",
            "docs/DEPLOYMENT.md",
            "docs/RUNBOOK.md"
        ]
        
        for doc_path in required_docs:
            full_path = self.project_root / doc_path
            if not full_path.exists():
                self.warnings.append(f"Documentation not found: {doc_path}")
            else:
                self.info.append(f"✓ Found {doc_path}")
        
        # Check for deployment scripts
        scripts_dir = self.project_root / "scripts"
        if scripts_dir.exists():
            script_files = list(scripts_dir.glob("*.py"))
            self.info.append(f"✓ Found {len(script_files)} script files")
        
        self.info.append("✓ Documentation validated")
    
    def print_results(self):
        """Print validation results."""
        print("\n" + "=" * 60)
        print("📋 VALIDATION RESULTS")
        print("=" * 60)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.info:
            print(f"\n✅ SUCCESS ({len(self.info)}):")
            for info in self.info:
                print(f"   • {info}")
        
        print("\n" + "=" * 60)
        
        if self.errors:
            print("❌ VALIDATION FAILED - Please fix the errors above")
            return False
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS - Consider addressing warnings")
            return True
        else:
            print("✅ VALIDATION PASSED - Pipeline configuration looks good!")
            return True


def main():
    """Main function."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    validator = PipelineValidator(project_root)
    success = validator.validate_all()
    
    if not success:
        sys.exit(1)
    
    print("\n🚀 Ready to deploy! Your CI/CD pipeline is properly configured.")
    print("\nNext steps:")
    print("1. Configure GitHub repository secrets (AWS credentials)")
    print("2. Set up Terraform state backend S3 bucket")
    print("3. Configure domain name and SSL certificate (optional)")
    print("4. Push to GitHub to trigger the pipeline")


if __name__ == "__main__":
    main()