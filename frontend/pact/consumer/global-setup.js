/**
 * Global setup for Pact consumer tests
 *
 * Ensures clean environment before running contract tests.
 */

const fs = require('fs');
const path = require('path');

module.exports = async () => {
  console.log('🔧 Setting up Pact consumer test environment...');

  // Clean up any existing pact files
  const pactsDir = path.resolve(process.cwd(), 'pacts');
  if (fs.existsSync(pactsDir)) {
    const files = fs.readdirSync(pactsDir);
    files.forEach(file => {
      if (file.endsWith('.json')) {
        fs.unlinkSync(path.join(pactsDir, file));
        console.log(`🗑️  Cleaned up existing pact file: ${file}`);
      }
    });
  }

  // Clean up log files
  const logsDir = path.resolve(process.cwd(), 'logs');
  if (fs.existsSync(logsDir)) {
    const files = fs.readdirSync(logsDir);
    files.forEach(file => {
      if (file.endsWith('.log')) {
        fs.unlinkSync(path.join(logsDir, file));
        console.log(`🗑️  Cleaned up existing log file: ${file}`);
      }
    });
  }

  console.log('✅ Pact consumer test environment ready');
};
