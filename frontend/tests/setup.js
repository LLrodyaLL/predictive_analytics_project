import { config } from '@vue/test-utils';
import { ElInput, ElTable, ElButton, ElCascader, ElDialog, ElTableColumn } from 'element-plus';

// Регистрация компонентов Element Plus для тестов
config.global.components = {
  ElInput,
  ElTable,
  ElButton,
  ElCascader,
  ElDialog,
  ElTableColumn,
};