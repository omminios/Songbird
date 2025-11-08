# GitHub Actions CI/CD Workflows

This directory contains automated workflows for testing and deploying Songbird.

## Workflows

### 1. CI - Test and Lint (`ci.yml`)

**Trigger:** Push to `main` or `feature/*` branches, Pull Requests to `main`

**What it does:**
- Runs unit tests on Python 3.9, 3.10, and 3.11
- Generates code coverage reports
- Uploads coverage to Codecov
- Runs flake8 linter
- Checks code formatting with Black

**Status Badge:**
```markdown
![CI Status](https://github.com/YOUR_USERNAME/Songbird/actions/workflows/ci.yml/badge.svg)
```

### 2. CD - Deploy to AWS Lambda (`deploy.yml`)

**Trigger:**
- Push to `main` branch
- Tags matching `v*` (e.g., `v1.0.0`)
- Manual workflow dispatch

**What it does:**
- Builds Lambda deployment package
- Configures AWS credentials
- Runs Terraform to deploy infrastructure
- Updates Lambda function code
- Tests the deployed Lambda function
- Generates deployment summary

**Status Badge:**
```markdown
![Deploy Status](https://github.com/YOUR_USERNAME/Songbird/actions/workflows/deploy.yml/badge.svg)
```

## Required GitHub Secrets

To use these workflows, you must configure the following secrets in your repository:

### AWS Credentials
Navigate to: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key ID for deployment | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Access Key | `wJalrXUtn...` |
| `AWS_REGION` | AWS Region for deployment | `us-east-1` |

### Spotify API Credentials
| Secret Name | Description | Where to get it |
|-------------|-------------|-----------------|
| `SPOTIFY_CLIENT_ID` | Spotify OAuth Client ID | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Spotify OAuth Client Secret | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |

### Setting up GitHub Secrets

1. Go to your repository on GitHub
2. Click `Settings` → `Secrets and variables` → `Actions`
3. Click `New repository secret`
4. Add each secret listed above

## Workflow Details

### CI Workflow

**Test Matrix:**
- Tests run on multiple Python versions (3.9, 3.10, 3.11)
- Ensures compatibility across Python versions

**Coverage:**
- Generates coverage reports in XML and terminal formats
- Uploads to Codecov for tracking over time

**Linting:**
- **flake8**: Checks for Python syntax errors and code quality issues
- **black**: Ensures consistent code formatting

### CD Workflow

**Deployment Steps:**
1. **Build**: Creates Lambda deployment package using `terraform/build_lambda.py`
2. **Infrastructure**: Uses Terraform to create/update AWS resources:
   - Lambda function
   - IAM roles and policies
   - EventBridge scheduled rule
   - CloudWatch log groups
   - S3 bucket configurations
3. **Deploy**: Updates Lambda function code
4. **Test**: Invokes the deployed Lambda function to verify it works

**Safety Features:**
- `terraform plan` runs first to preview changes
- Only applies on `main` branch or version tags
- Manual approval can be added via GitHub Environments

## Local Development

### Run tests locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Run all unit tests
pytest tests/unit -v

# Run with coverage
pytest tests/unit --cov=src/songbird --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_song_matcher.py -v
```

### Run linters locally:
```bash
# flake8
flake8 src/songbird

# black (check)
black --check src/songbird

# black (fix)
black src/songbird
```

### Test deployment locally:
```bash
cd terraform

# Build package
python build_lambda.py

# Plan infrastructure changes
terraform plan

# Apply changes (requires AWS credentials)
terraform apply
```

## Troubleshooting

### CI Workflow Issues

**Tests failing:**
- Check test logs in GitHub Actions
- Run tests locally to reproduce
- Ensure all fixtures and mocks are properly configured

**Linting failures:**
- Run `black src/songbird` to auto-format code
- Fix flake8 warnings manually

### CD Workflow Issues

**AWS Authentication Failed:**
- Verify GitHub secrets are set correctly
- Check AWS credentials have necessary permissions
- Ensure IAM user has Lambda, S3, IAM, and CloudWatch permissions

**Terraform Apply Failed:**
- Check Terraform plan output
- Verify S3 bucket exists or can be created
- Ensure Lambda deployment package was built successfully

**Lambda Test Failed:**
- Check Lambda logs in CloudWatch
- Verify environment variables are set correctly
- Test Lambda function manually in AWS Console

## Adding More Workflows

You can add additional workflows for:
- **Staging environment**: Deploy to staging before production
- **Integration tests**: Run end-to-end tests against real APIs
- **Notifications**: Send Slack/Discord notifications on deployment
- **Rollback**: Automatically rollback failed deployments

## Best Practices

1. **Always run tests before merging**: PRs should pass CI before merge
2. **Use feature branches**: Work on `feature/*` branches
3. **Tag releases**: Use semantic versioning (`v1.0.0`, `v1.1.0`, etc.)
4. **Monitor deployments**: Check CloudWatch logs after deployment
5. **Keep secrets updated**: Rotate AWS credentials regularly

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda with GitHub Actions](https://docs.aws.amazon.com/lambda/latest/dg/lambda-github-actions.html)
- [pytest Documentation](https://docs.pytest.org/)
