# SPRAG 客服对话系统 — 设计文档：用户权限系统

## 概述

为 SPRAG 系统增加用户认证和角色权限控制，实现两端（客服对话 + 管理后台）的登录保护与权限隔离。

## 角色

| 角色 | 权限 |
|------|------|
| `user` 普通用户 | 登录后可提问对话，不可访问管理后台 |
| `admin` 管理员 | 登录后可提问对话 + 访问管理后台全部功能 |

## 数据模型

### users 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| username | String(50) | 登录名，唯一 |
| email | String(100) | 邮箱 |
| password_hash | String(255) | bcrypt 哈希 |
| role | String(10) | "user" 或 "admin" |
| is_active | Boolean | 默认 True |
| created_at | DateTime | 注册时间 |

## API

### 认证接口

#### `POST /api/v1/auth/register`

注册新用户（普通用户角色）。

**请求体：**
```json
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "abc123456"
}
```

**响应：**
```json
{
  "id": 1,
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "role": "user",
  "created_at": "2026-06-16T12:00:00"
}
```

#### `POST /api/v1/auth/login`

登录并获取 JWT Token。

**请求体：**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应：**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

Token 有效期 7 天。

#### `GET /api/v1/auth/me`

获取当前登录用户信息（需 Authorization header）。

**响应：**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "created_at": "2026-06-16T12:00:00"
}
```

### 接口权限矩阵

| 接口 | user | admin |
|------|------|-------|
| `POST /auth/register` | 公开 | 公开 |
| `POST /auth/login` | 公开 | 公开 |
| `GET /auth/me` | ✅ | ✅ |
| `POST /chat` | ✅ | ✅ |
| `POST /feedback` | ✅ | ✅ |
| `GET /documents` | ❌ | ✅ |
| `POST /documents/upload` | ❌ | ✅ |
| `DELETE /documents/{id}` | ❌ | ✅ |
| `GET /logs` | ❌ | ✅ |
| `GET /feedback` | ❌ | ✅ |
| `GET /feedback/stats` | ❌ | ✅ |
| `GET /config` | ❌ | ✅ |
| `PUT /config` | ❌ | ✅ |
| `GET /stats/*` | ❌ | ✅ |
| `GET /alerts` | ❌ | ✅ |

## 认证机制

- **算法**：JWT (HS256)
- **密钥**：从环境变量读取 `JWT_SECRET_KEY`（默认自动生成）
- **过期时间**：7 天
- **密码存储**：bcrypt（passlib）

### 后端依赖链

```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> User
    # 验证 JWT → 查 User 表 → 返回 User 对象

def require_admin(user: User = Depends(get_current_user)) -> User
    # 检查 user.role == "admin", 否则 403
```

## 前端

### 新增页面

| 路径 | 页面 | 访问限制 |
|------|------|----------|
| `/login` | 登录页 | 公开（已登录则跳转首页） |
| `/register` | 注册页 | 公开（已登录则跳转首页） |

### 路由守卫

```javascript
router.beforeEach((to, from, next) => {
  const isLoggedIn = !!localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  const isAdmin = user?.role === 'admin'

  if (!isLoggedIn && to.path !== '/login' && to.path !== '/register') {
    next('/login')
  } else if (isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    next('/')
  } else if (to.path === '/admin' && !isAdmin) {
    next('/')
  } else {
    next()
  }
})
```

### 登录状态管理

```javascript
// auth store（响应式对象）
const auth = reactive({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
})

// computed 属性
auth.isLoggedIn  // !!token
auth.isAdmin     // role === 'admin'
```

- token 和 user 信息持久化到 localStorage
- axios 拦截器自动附带 `Authorization: Bearer <token>`
- 检测到 401 响应时自动清除 token 并跳转登录页

### 导航调整

- 未登录：仅显示登录/注册页
- 普通用户：对话界面显示用户名 + 退出，不显示「管理后台」链接
- 管理员：对话界面显示「管理后台」链接 + 用户名 + 退出

## 技术依赖

```txt
# requirements.txt 新增
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
```

## 初始化

- 首次启动时检查 `users` 表是否为空
- 若为空，自动创建默认管理员账号（admin / admin@example.com / admin123）
- 默认管理员密码可在 `.env` 中配置 `DEFAULT_ADMIN_PASSWORD`

## 文件变更清单

### 后端（新增/修改）

| 文件 | 操作 |
|------|------|
| `app/models/user.py` | 新增 User ORM |
| `app/schemas/user.py` | 新增 Pydantic schemas |
| `app/api/auth.py` | 新增 auth API 路由 |
| `app/services/auth_service.py` | 新增 JWT + 密码工具函数 |
| `app/main.py` | 注册 auth router |
| `app/config.py` | 新增 JWT_SECRET_KEY 配置 |
| `requirements.txt` | 新增 python-jose, passlib, bcrypt |
| `.env.example` | 新增 JWT_SECRET_KEY |
| `.env` | 新增 JWT_SECRET_KEY + DEFAULT_ADMIN_PASSWORD |

### 现有 API 修改

| 文件 | 修改 |
|------|------|
| `app/api/chat.py` | 添加 `get_current_user` 依赖 |
| `app/api/feedback.py` | POST 添加 user 依赖，GET 添加 admin 依赖 |
| `app/api/documents.py` | 添加 `require_admin` 依赖 |
| `app/api/logs.py` | 添加 `require_admin` 依赖 |
| `app/api/config.py` | 添加 `require_admin` 依赖 |
| `app/api/stats.py` | 添加 `require_admin` 依赖 |
| `app/api/alerts.py` | 添加 `require_admin` 依赖 |

### 前端（新增/修改）

| 文件 | 操作 |
|------|------|
| `src/views/LoginView.vue` | 新增登录页 |
| `src/views/RegisterView.vue` | 新增注册页 |
| `src/stores/auth.js` | 新增认证状态管理 |
| `src/router/index.js` | 新增路由守卫 + login/register 路由 |
| `src/api/index.js` | 新增 auth API + axios 拦截器 |
| `src/views/ChatView.vue` | 新增用户信息/退出按钮 |
| `src/views/AdminView.vue` | 新增退出按钮 |