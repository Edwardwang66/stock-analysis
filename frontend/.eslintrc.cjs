module.exports = {
  root: true,
  extends: ["next/core-web-vitals"],
  ignorePatterns: [".next/**", "out/**", "node_modules/**", "public/feed/**"],
  rules: {
    // Stage 1B preserves the behavior of the existing effect-heavy pages.
    // Re-enabling this rule requires a separate hook-dependency audit.
    "react-hooks/exhaustive-deps": "off",
  },
};
