#!/bin/bash

# Setup script for git hooks and quality tooling
# This script should be run after initializing a git repository

set -e

echo "Setting up code quality tooling..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository. Please run 'git init' first."
    exit 1
fi

# Install husky
echo "Installing husky..."
npx husky install

# Make sure the .husky directory exists
mkdir -p .husky

# Add pre-commit hook
echo "Setting up pre-commit hook..."
npx husky add .husky/pre-commit "npx lint-staged"

# Add commit-msg hook for conventional commits
echo "Setting up commit-msg hook..."
npx husky add .husky/commit-msg 'npx --no -- commitlint --edit ${1}'

# Install commitlint
echo "Installing commitlint..."
npm install --save-dev @commitlint/cli @commitlint/config-conventional

# Add prepare script to package.json if it doesn't exist
echo "Adding prepare script to package.json..."
npm set-script prepare "husky install"

# Make scripts executable
chmod +x .husky/pre-commit
chmod +x .husky/commit-msg

echo "✅ Git hooks setup complete!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-commit: Runs linting and formatting checks"
echo "  - commit-msg: Validates commit message format"
echo ""
echo "Example valid commit messages:"
echo "  feat: add new weather component"
echo "  fix: resolve forecast API error"
echo "  docs: update README with setup instructions"
echo "  style: format code with prettier"
echo "  refactor: extract common utility functions"
echo "  test: add unit tests for forecast service"
echo "  chore: update dependencies"