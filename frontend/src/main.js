import { createApp } from 'vue'
import App from './App.vue'
import { ElTable, ElCascader, ElInput, ElButton, ElDialog } from 'element-plus';
import 'element-plus/dist/index.css';

const app = createApp(App)
app.use(ElTable).use(ElCascader).use(ElInput).use(ElButton).use(ElDialog)
app.mount('#app')