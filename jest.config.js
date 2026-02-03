module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/tests/**/*.unit.test.js'],
  collectCoverageFrom: [
    'popup.js',
    'background.js',
    '!node_modules/**',
    '!tests/**',
  ],
  coverageThreshold: {
    global: {
      branches: 100,
      functions: 100,
      lines: 100,
      statements: 100,
    },
  },
};
