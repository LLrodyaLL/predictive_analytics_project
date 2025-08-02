import vuePlugin from 'eslint-plugin-vue';
import prettier from 'eslint-config-prettier';

export default [
  {
    files: ['**/*.vue', '**/*.js'],
    languageOptions: {
      parser: (await import('vue-eslint-parser')).default,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
    },
    plugins: {
      vue: vuePlugin,
    },
    rules: {
      ...vuePlugin.configs['base'].rules, // минимально рабочее
      'vue/comment-directive': 'off',
      // добавь вручную, если нужны строгие правила
    },
  },
  prettier,
];
