import Vue from 'vue'
import App from './App.vue'
import router from './router'
import request from "@/utils/request"
import 'element-ui/lib/theme-chalk/index.css';
import { 
  Button, 
  Select,
  Table,
  TableColumn,
  Dialog, 
  Popconfirm,
  Form,
  FormItem,
  Input,
  Switch,
  Option,
  Notification,
  Row,
  Col,
  Card,
} from 'element-ui';

// import Notifications from "vue-notification"

// 关闭生产模式下的提示
Vue.config.productionTip = false

// 设置为Vue的原型属性
Vue.prototype.$axios = request
Vue.prototype.$notify = Notification;

// Vue.use(ElementUI);
Vue.use(Button);
Vue.use(Select);
Vue.use(Table);
Vue.use(TableColumn);
Vue.use(Dialog);
Vue.use(Popconfirm);
Vue.use(Form);
Vue.use(FormItem);
Vue.use(Input);
Vue.use(Switch);
Vue.use(Option);
Vue.use(Row);
Vue.use(Col);
Vue.use(Card)

new Vue({
  router,
  render: function (h) { return h(App) }
}).$mount('#app')
