# Code Quality Tooling Setup

This document describes the comprehensive code quality tooling setup for the Adelaide Weather Frontend application.

## 🛠️ Tools Configured

### 1. ESLint

- **Configuration**: `.eslintrc.json`
- **Features**:
  - React & React Hooks rules
  - TypeScript support
  - Accessibility (a11y) checks
  - Import organization
  - Code complexity limits
  - Custom rules for Next.js

### 2. Prettier

- **Configuration**: `.prettierrc.json`, `.prettierignore`
- **Features**:
  - Consistent code formatting
  - Integration with ESLint
  - Automatic formatting on save

### 3. TypeScript

- **Configuration**: `tsconfig.json`
- **Features**:
  - Strict type checking
  - Path mapping
  - Incremental compilation

### 4. Jest Testing

- **Configuration**: `jest.config.js`, `jest.setup.js`, `jest.polyfills.js`
- **Features**:
  - Code coverage thresholds (85% global, 90% for components)
  - Multiple coverage reporters
  - Test environment setup
  - Watch plugins for development

### 5. Pre-commit Hooks

- **Configuration**: `.lintstagedrc.json`, `commitlint.config.js`
- **Tools**: Husky, lint-staged, commitlint
- **Features**:
  - Automatic linting and formatting before commits
  - Conventional commit message validation
  - TypeScript type checking

### 6. GitHub Actions CI/CD

- **Workflows**:
  - `quality-gates.yml`: Comprehensive quality checks
  - `pr-quality-check.yml`: Pull request validation
  - `codeql-analysis.yml`: Security analysis

### 7. Bundle Analysis

- **Configuration**: `.bundlesize.config.json`
- **Tools**: bundlesize, @next/bundle-analyzer
- **Features**:
  - Bundle size monitoring
  - Performance analysis

## 📋 Available Scripts

### Development

```bash
npm run dev                    # Start development server
npm run build                  # Build for production
npm run start                  # Start production server
```

### Code Quality

```bash
npm run lint                   # Run ESLint
npm run lint:fix              # Fix ESLint issues
npm run lint:strict           # Strict linting (no warnings)

npm run format                # Format code with Prettier
npm run format:check          # Check code formatting

npm run type-check            # TypeScript type checking
npm run type-check:strict     # Strict type checking
npm run type-check:watch      # Watch mode for type checking
```

### Testing

```bash
npm run test                  # Run all tests
npm run test:watch           # Run tests in watch mode
npm run test:coverage        # Run tests with coverage
npm run test:unit            # Run unit tests only
npm run test:playwright      # Run e2e tests
```

### Quality Checks

```bash
npm run quality:check        # Full quality check
npm run quality:check:fast   # Quick quality check
npm run quality:fix          # Fix quality issues
npm run quality:analyze      # Comprehensive code analysis
```

### Analysis

```bash
npm run analyze:bundle       # Bundle analysis
npm run analyze:deps         # Dependency analysis
npm run analyze:complexity   # Code complexity analysis
npm run analyze:size         # Bundle size check
```

### Auditing

```bash
npm run audit:security       # Security audit
npm run audit:licenses       # License check
npm run audit:deps           # Check outdated dependencies
```

### CI/CD

```bash
npm run ci:all               # Run all CI checks
npm run ci:lint              # CI linting
npm run ci:test              # CI testing
npm run ci:build             # CI build
npm run ci:audit             # CI security audit
```

## 🚀 Quick Start

### Initial Setup

1. **Install dependencies**:

   ```bash
   npm ci
   ```

2. **Initialize git hooks** (if in a git repository):

   ```bash
   ./setup-git-hooks.sh
   ```

3. **Run quality checks**:
   ```bash
   npm run quality:check
   ```

### Development Workflow

1. **Start development server**:

   ```bash
   npm run dev
   ```

2. **Before committing** (automatic via pre-commit hooks):

   ```bash
   npm run quality:check:fast
   ```

3. **Fix issues automatically**:
   ```bash
   npm run quality:fix
   ```

## 📊 Quality Standards

### Code Coverage Thresholds

- **Global**: 85% (lines, branches, functions, statements)
- **Components**: 90% (lines, branches, functions, statements)
- **Libraries**: 80% (lines, branches, functions, statements)

### Code Quality Metrics

- **Complexity**: Maximum 10 per function
- **Max file length**: 300 lines
- **Max function length**: 50 lines
- **Max parameters**: 4 per function

### Bundle Size Limits

- **Page chunks**: 150kb (gzipped)
- **Other chunks**: 200kb (gzipped)
- **CSS files**: 50kb (gzipped)

## 🔧 Configuration Files

### Core Configuration

- `.eslintrc.json` - ESLint configuration
- `.prettierrc.json` - Prettier configuration
- `tsconfig.json` - TypeScript configuration
- `jest.config.js` - Jest testing configuration

### Quality Tooling

- `.lintstagedrc.json` - Pre-commit linting configuration
- `commitlint.config.js` - Commit message validation
- `.bundlesize.config.json` - Bundle size monitoring

### CI/CD

- `.github/workflows/` - GitHub Actions workflows
- `scripts/quality-check.sh` - Quality check script
- `scripts/analyze-code.sh` - Code analysis script

## 🚨 Pre-commit Hooks

The following checks run automatically before each commit:

1. **ESLint**: Code linting and auto-fixing
2. **Prettier**: Code formatting
3. **TypeScript**: Type checking
4. **Tests**: Related test execution

### Commit Message Format

We use [Conventional Commits](https://conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`

**Examples**:

- `feat: add weather forecast component`
- `fix: resolve API timeout issue`
- `docs: update README with setup instructions`

## 🔍 Code Analysis

### Automatic Analysis

- **Circular dependencies**: Detected and reported
- **Code complexity**: Measured and limited
- **Bundle size**: Monitored and enforced
- **Security vulnerabilities**: Scanned and reported
- **License compliance**: Checked automatically

### Manual Analysis

Run comprehensive code analysis:

```bash
npm run quality:analyze
```

This generates reports for:

- Complexity analysis
- Dependency analysis
- Bundle analysis
- Test coverage
- Security audit
- Performance metrics

## 🛡️ Security

### Security Measures

- **npm audit**: Automatic vulnerability scanning
- **CodeQL**: Static security analysis
- **Dependency review**: PR-based dependency changes
- **License checking**: Ensure license compliance

### Security Thresholds

- **Audit level**: Moderate and above
- **Vulnerability tolerance**: Zero critical, zero high in production

## 📈 Performance Monitoring

### Metrics Tracked

- Bundle size changes
- Build time
- Test execution time
- Coverage percentages
- Dependency update frequency

### Performance Gates

- Build must complete within reasonable time
- Bundle size must stay within limits
- All tests must pass
- Coverage thresholds must be met

## 🤝 Contributing

### Before Contributing

1. Run `npm run quality:check` to ensure code quality
2. Ensure all tests pass: `npm run test:coverage`
3. Check bundle size impact: `npm run analyze:size`
4. Review security implications: `npm run audit:security`

### Pull Request Process

1. **Automated checks**: All CI checks must pass
2. **Code review**: At least one approval required
3. **Quality gates**: All quality metrics must meet standards
4. **Documentation**: Update docs if needed

## 🆘 Troubleshooting

### Common Issues

#### ESLint Errors

```bash
# Fix auto-fixable issues
npm run lint:fix

# Check specific files
npx eslint src/components/MyComponent.tsx --fix
```

#### TypeScript Errors

```bash
# Run type checking
npm run type-check

# Watch mode for development
npm run type-check:watch
```

#### Test Failures

```bash
# Run tests in watch mode
npm run test:watch

# Run specific test file
npx jest MyComponent.test.tsx

# Update snapshots
npx jest --updateSnapshot
```

#### Pre-commit Hook Issues

```bash
# Manually run pre-commit checks
npx lint-staged

# Skip hooks if necessary (not recommended)
git commit --no-verify
```

### Getting Help

1. Check the error message and try suggested fixes
2. Run `npm run quality:check --help` for script options
3. Review configuration files for customization
4. Check GitHub Actions logs for CI failures

## 📚 Additional Resources

- [ESLint Documentation](https://eslint.org/docs/)
- [Prettier Documentation](https://prettier.io/docs/)
- [Jest Documentation](https://jestjs.io/docs/)
- [Husky Documentation](https://typicode.github.io/husky/)
- [Conventional Commits](https://conventionalcommits.org/)
- [Next.js Best Practices](https://nextjs.org/docs/basic-features/eslint)
