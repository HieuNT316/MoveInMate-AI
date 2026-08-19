import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Các trang client tải dữ liệu sau khi session/user id sẵn sàng. Việc
      // cập nhật loading/data/error trong callback async là đồng bộ hoá với
      // API bên ngoài, đúng mục đích của effect; rule React 19 hiện vẫn đánh
      // dấu cả lời gọi gián tiếp này như setState đồng bộ.
      "react-hooks/set-state-in-effect": "off",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
