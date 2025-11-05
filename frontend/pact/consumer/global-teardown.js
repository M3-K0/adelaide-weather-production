/**
 * Global teardown for Pact consumer tests
 *
 * Validates and reports on generated contract files.
 */

const fs = require('fs');
const path = require('path');

module.exports = async () => {
  console.log('🧹 Cleaning up Pact consumer test environment...');

  // Validate generated pact files
  const pactsDir = path.resolve(process.cwd(), 'pacts');
  if (fs.existsSync(pactsDir)) {
    const files = fs.readdirSync(pactsDir);
    const pactFiles = files.filter(file => file.endsWith('.json'));

    console.log(`📄 Generated ${pactFiles.length} contract file(s):`);
    pactFiles.forEach(file => {
      const filePath = path.join(pactsDir, file);
      const stats = fs.statSync(filePath);
      const contract = JSON.parse(fs.readFileSync(filePath, 'utf8'));

      console.log(`  📝 ${file} (${Math.round(stats.size / 1024)}KB)`);
      console.log(`     Consumer: ${contract.consumer.name}`);
      console.log(`     Provider: ${contract.provider.name}`);
      console.log(`     Interactions: ${contract.interactions.length}`);
    });

    if (pactFiles.length === 0) {
      console.log(
        '⚠️  No contract files were generated. Check test execution.'
      );
    }
  }

  console.log('✅ Pact consumer test cleanup complete');
};
