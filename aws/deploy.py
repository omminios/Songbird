"""
AWS deployment script for Songbird
Handles CloudFormation stack deployment and Lambda code updates
"""
import os
import json
import zipfile
import boto3
import argparse
from pathlib import Path


class SongbirdDeployer:
    """Handles deployment to AWS"""

    def __init__(self, environment='prod'):
        self.environment = environment
        self.project_name = 'songbird'
        self.region = 'us-east-1'  # Default region

        # AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)

        # Paths
        self.project_root = Path(__file__).parent.parent
        self.aws_dir = Path(__file__).parent

    def deploy_infrastructure(self):
        """Deploy CloudFormation stack"""
        print(f"🚀 Deploying infrastructure for {self.environment}...")

        stack_name = f'{self.project_name}-{self.environment}'
        template_path = self.aws_dir / 'cloudformation.yaml'

        try:
            with open(template_path, 'r') as f:
                template_body = f.read()

            # Check if stack exists
            try:
                self.cloudformation.describe_stacks(StackName=stack_name)
                stack_exists = True
            except self.cloudformation.exceptions.ClientError:
                stack_exists = False

            parameters = [
                {'ParameterKey': 'ProjectName', 'ParameterValue': self.project_name},
                {'ParameterKey': 'Environment', 'ParameterValue': self.environment}
            ]

            if stack_exists:
                print(f"📋 Updating existing stack: {stack_name}")
                response = self.cloudformation.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )
            else:
                print(f"📋 Creating new stack: {stack_name}")
                response = self.cloudformation.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )

            print(f"✅ Stack operation initiated: {response['StackId']}")
            self._wait_for_stack_complete(stack_name)

        except Exception as e:
            print(f"❌ Infrastructure deployment failed: {e}")
            return False

        return True

    def deploy_lambda_code(self):
        """Package and deploy Lambda function code"""
        print("📦 Packaging Lambda function...")

        # Create deployment package
        zip_path = self._create_lambda_package()
        if not zip_path:
            return False

        # Upload to Lambda
        function_name = f'{self.project_name}-sync-{self.environment}'

        try:
            with open(zip_path, 'rb') as f:
                zip_content = f.read()

            print(f"📤 Uploading code to Lambda function: {function_name}")
            response = self.lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )

            print(f"✅ Lambda code updated: {response['Version']}")

            # Clean up zip file
            os.remove(zip_path)

        except Exception as e:
            print(f"❌ Lambda deployment failed: {e}")
            return False

        return True

    def _create_lambda_package(self):
        """Create Lambda deployment package"""
        package_dir = self.aws_dir / 'package'
        zip_path = self.aws_dir / 'lambda_package.zip'

        try:
            # Create package directory
            package_dir.mkdir(exist_ok=True)

            # Copy Songbird source code
            src_dir = self.project_root / 'src' / 'songbird'
            self._copy_directory(src_dir, package_dir / 'songbird')

            # Copy Lambda function
            lambda_function_path = self.aws_dir / 'lambda_function.py'
            self._copy_file(lambda_function_path, package_dir / 'lambda_function.py')

            # Install dependencies
            self._install_dependencies(package_dir)

            # Create zip file
            self._create_zip(package_dir, zip_path)

            # Clean up package directory
            self._remove_directory(package_dir)

            print(f"📦 Package created: {zip_path}")
            return zip_path

        except Exception as e:
            print(f"❌ Package creation failed: {e}")
            return None

    def _copy_directory(self, src, dst):
        """Copy directory recursively"""
        import shutil
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    def _copy_file(self, src, dst):
        """Copy single file"""
        import shutil
        shutil.copy2(src, dst)

    def _remove_directory(self, path):
        """Remove directory recursively"""
        import shutil
        if path.exists():
            shutil.rmtree(path)

    def _install_dependencies(self, package_dir):
        """Install Python dependencies in package directory"""
        requirements_file = self.project_root / 'requirements.txt'

        if requirements_file.exists():
            import subprocess
            subprocess.run([
                'pip', 'install',
                '-r', str(requirements_file),
                '-t', str(package_dir),
                '--no-deps'  # Skip dependencies that are already in Lambda runtime
            ], check=True)

    def _create_zip(self, source_dir, zip_path):
        """Create zip file from directory"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

    def _wait_for_stack_complete(self, stack_name):
        """Wait for CloudFormation stack operation to complete"""
        print("⏳ Waiting for stack operation to complete...")

        waiter = self.cloudformation.get_waiter('stack_create_complete')
        try:
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            print("✅ Stack operation completed successfully")
        except Exception as e:
            print(f"❌ Stack operation failed or timed out: {e}")

    def get_stack_outputs(self):
        """Get CloudFormation stack outputs"""
        stack_name = f'{self.project_name}-{self.environment}'

        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]

            outputs = {}
            for output in stack.get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']

            return outputs

        except Exception as e:
            print(f"❌ Failed to get stack outputs: {e}")
            return {}

    def update_cli_config(self):
        """Update CLI configuration with AWS endpoints"""
        outputs = self.get_stack_outputs()

        if 'ApiGatewayUrl' in outputs:
            api_url = outputs['ApiGatewayUrl']
            print(f"🔧 API Gateway URL: {api_url}")

            # TODO: Update CLI configuration to use this endpoint
            # This would modify the sync manager to use the API Gateway URL

        return outputs


def main():
    parser = argparse.ArgumentParser(description='Deploy Songbird to AWS')
    parser.add_argument('--environment', '-e', default='prod',
                        choices=['dev', 'staging', 'prod'],
                        help='Deployment environment')
    parser.add_argument('--infrastructure-only', action='store_true',
                        help='Deploy infrastructure only, skip Lambda code')
    parser.add_argument('--lambda-only', action='store_true',
                        help='Deploy Lambda code only, skip infrastructure')

    args = parser.parse_args()

    deployer = SongbirdDeployer(args.environment)

    if args.lambda_only:
        success = deployer.deploy_lambda_code()
    elif args.infrastructure_only:
        success = deployer.deploy_infrastructure()
    else:
        # Deploy both
        success = deployer.deploy_infrastructure()
        if success:
            success = deployer.deploy_lambda_code()

    if success:
        print("\n🎉 Deployment completed successfully!")
        outputs = deployer.update_cli_config()

        print("\n📋 Stack Outputs:")
        for key, value in outputs.items():
            print(f"  {key}: {value}")

        print(f"\n🔧 Next steps:")
        print(f"1. Update SSM parameters with your API credentials")
        print(f"2. Test manual sync: songbird sync")
        print(f"3. Verify scheduled sync is working")

    else:
        print("\n❌ Deployment failed!")
        exit(1)


if __name__ == '__main__':
    main()