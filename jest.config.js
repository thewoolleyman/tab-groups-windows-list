module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/tests/**/*.unit.test.js'],
  collectCoverageFrom: [
    'popup.js',
    '!node_modules/**',
    '!tests/**',
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50,
    },
  },
};
