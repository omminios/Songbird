# Songbird Testing Guide

## Overview

This document describes the unit testing setup and CI/CD pipeline for Songbird.

## Test Suite Status

**Current Status**: ✅ 73 passing / ⚠️ 19 failing / 📊 25% code coverage

### Test Coverage by Module

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| `song_matcher.py` | 30 tests | 82% | ✅ Most passing |
| `config/manager.py` | 31 tests | 85% | ✅ Most passing |
| `sync/manager.py` | 31 tests | 21% | ⚠️ Needs work |

## Running Tests Locally

### Prerequisites

```bash
# Activate virtual environment
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install test dependencies
pip install pytest pytest-cov pytest-mock moto responses
```

### Run All Tests

```bash
# Run all unit tests
pytest tests/unit -v

# Run with coverage report
pytest tests/unit --cov=src/songbird --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_song_matcher.py -v

# Run specific test
pytest tests/unit/test_song_matcher.py::TestSongMatcher::test_clean_string_removes_parentheses -v
```

### Quick Test Commands

```bash
# Fast: Run without coverage
pytest tests/unit -q

# Verbose: Show detailed output
pytest tests/unit -vv

# Stop on first failure
pytest tests/unit -x

# Run only failed tests from last run
pytest tests/unit --lf
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/
│   ├── test_song_matcher.py     # 30 tests for fuzzy matching logic
│   ├── test_config_manager.py   # 31 tests for S3 config management
│   └── test_sync_manager.py     # 31 tests for sync orchestration
└── integration/             # (Future) End-to-end tests
```

## Test Fixtures

### Common Fixtures (from `conftest.py`)

- `test_env_vars` - Sets up test environment variables
- `mock_s3_bucket` - Mocked S3 bucket for testing
- `sample_spotify_track` - Sample Spotify track data
- `sample_youtube_track` - Sample YouTube Music track data
- `sample_config` - Sample Songbird configuration
- `mock_spotify_manager` - Mocked Spotify API manager
- `mock_youtube_manager` - Mocked YouTube API manager

### Using Fixtures

```python
def test_example(sample_spotify_track, mock_s3_bucket):
    """Test using fixtures"""
    # sample_spotify_track is automatically provided
    assert sample_spotify_track['name'] == 'Bohemian Rhapsody'

    # mock_s3_bucket is a mocked S3 client
    mock_s3_bucket.put_object(Bucket='test-bucket', Key='test.json', Body='{}')
```

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. CI - Test and Lint (`.github/workflows/ci.yml`)

**Triggers**: Push to `main` or `feature/*`, Pull Requests

**Steps**:
1. Run tests on Python 3.9, 3.10, and 3.11
2. Generate coverage reports
3. Upload to Codecov
4. Run flake8 linter
5. Check code formatting with Black

#### 2. CD - Deploy (`.github/workflows/deploy.yml`)

**Triggers**: Push to `main`, Tags `v*`, Manual

**Steps**:
1. Build Lambda deployment package
2. Run Terraform plan
3. Deploy to AWS Lambda
4. Test deployed function
5. Generate deployment summary

### Required GitHub Secrets

Configure in `Settings` → `Secrets and variables` → `Actions`:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
```

## Known Test Failures

### Current Issues

1. **Config Manager**: Cache isolation test needs fixing
   - Test: `test_load_config_returns_copy`
   - Issue: Config cache returns reference instead of copy

2. **Song Matcher**: String cleaning precision
   - Tests: `test_clean_string_removes_feat`, `test_build_search_query_cleans_both_fields`
   - Issue: Regex not fully removing "feat" variations

3. **Sync Manager**: Missing private methods
   - Tests: `test_normalize_track_*`, `test_deduplicate_tracks_*`
   - Issue: Tests written for methods that don't exist yet

### Fixing Failures

To fix the known failures:

```bash
# 1. Run failing tests to see details
pytest tests/unit -k "test_clean_string_removes_feat" -vv

# 2. Fix the code in src/songbird/

# 3. Re-run tests to verify
pytest tests/unit -k "test_clean_string_removes_feat" -v
```

## Writing New Tests

### Test Naming Convention

```python
class TestClassName:
    """Test suite for ClassName"""

    def test_method_name_scenario(self):
        """Test that method_name handles scenario correctly"""
        # Arrange
        input_data = create_test_data()

        # Act
        result = method_name(input_data)

        # Assert
        assert result == expected_value
```

### Testing Best Practices

1. **One assertion per test** (when possible)
2. **Use descriptive test names** that explain what's being tested
3. **Mock external dependencies** (APIs, S3, databases)
4. **Test edge cases** (empty lists, None values, errors)
5. **Use fixtures** for common test data

### Example Test

```python
def test_add_playlist_pair(config_manager):
    """Test adding a playlist pair creates correct structure"""
    # Arrange
    spotify_playlist = {
        'id': 'spotify123',
        'name': 'My Playlist',
        'uri': 'spotify:playlist:123'
    }
    youtube_playlist = {
        'id': 'youtube456',
        'name': 'My Playlist'
    }

    # Act
    config_manager.add_playlist_pair(spotify_playlist, youtube_playlist)

    # Assert
    pairs = config_manager.get_playlist_pairs()
    assert len(pairs) == 1
    assert pairs[0]['spotify']['id'] == 'spotify123'
```

## Mocking AWS Services

We use `moto` to mock AWS services in tests:

```python
from moto import mock_aws
import boto3

@mock_aws
def test_s3_operations():
    """Test S3 operations with mocked AWS"""
    # Create mock S3 client
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')

    # Test your code that uses S3
    s3.put_object(Bucket='test-bucket', Key='test.json', Body='{}')

    response = s3.get_object(Bucket='test-bucket', Key='test.json')
    assert response['Body'].read() == b'{}'
```

## Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| Core sync logic | 25% | 80% |
| Song matching | 82% | 90% |
| Config management | 85% | 90% |
| Overall | 25% | 75% |

## Continuous Improvement

### TODO: Testing Roadmap

- [ ] Fix failing unit tests (19 failures)
- [ ] Increase coverage to 75%
- [ ] Add integration tests for end-to-end flows
- [ ] Add performance tests for large playlists
- [ ] Add API mocking for Spotify/YouTube calls
- [ ] Set up test data generators for realistic scenarios

### Adding Integration Tests

Create `tests/integration/test_full_sync.py`:

```python
import pytest

@pytest.mark.integration
def test_full_sync_flow():
    """Test complete sync flow from start to finish"""
    # This would test with real-ish data but mocked APIs
    pass
```

Run integration tests separately:

```bash
pytest tests/integration -v -m integration
```

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python version (CI uses 3.9, 3.10, 3.11)
- Check environment variables
- Clear pytest cache: `pytest --cache-clear`

### Moto ImportError

If you see `cannot import name 'mock_s3'`:

```python
# Old (moto v4)
from moto import mock_s3

# New (moto v5)
from moto import mock_aws
```

### Coverage Not Generating

```bash
# Install coverage plugin
pip install pytest-cov

# Generate HTML report
pytest tests/unit --cov=src/songbird --cov-report=html

# Open htmlcov/index.html in browser
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [moto Documentation](https://docs.getmoto.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**Last Updated**: 2025-11-07
**Maintained By**: Development Team
