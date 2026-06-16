import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import AdminView from '../views/AdminView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/register', name: 'register', component: RegisterView },
  { path: '/', name: 'chat', component: ChatView, meta: { requiresAuth: true } },
  { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('user'))
  } catch {
    return null
  }
}

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = getUser()
  const isLoggedIn = !!token && !!user
  const isAdmin = user?.role === 'admin'

  // 已登录访问登录/注册页 → 跳首页
  if (isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    return next('/')
  }

  // 未登录访问需要认证的页面 → 跳登录
  if (!isLoggedIn && to.meta.requiresAuth) {
    return next('/login')
  }

  // 非管理员访问 admin → 跳首页
  if (to.meta.requiresAdmin && !isAdmin) {
    return next('/')
  }

  next()
})

export default router