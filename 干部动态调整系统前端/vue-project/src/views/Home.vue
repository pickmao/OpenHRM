<template>
  <div class="home-container">
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h2>干部动态调整系统</h2>
        </div>
        <div class="header-right">
          <span class="welcome-text">欢迎，{{ userStore.userName }}</span>
          <el-button type="primary" @click="handleLogout" plain>
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="main">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <span>系统首页</span>
            </div>
          </template>

          <div class="user-info">
            <h3>用户信息</h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户名">
                {{ userStore.userInfo?.username || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="真实姓名">
                {{ userStore.userInfo?.real_name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="角色">
                {{ getRoleName(userStore.userInfo?.role) }}
              </el-descriptions-item>
              <el-descriptions-item label="手机号">
                {{ userStore.userInfo?.phone || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="最后登录时间">
                {{ formatTime(userStore.userInfo?.last_login) }}
              </el-descriptions-item>
              <el-descriptions-item label="最后登录IP">
                {{ userStore.userInfo?.last_login_ip || '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="permissions" v-if="userStore.permissions.length > 0">
            <h3>权限列表</h3>
            <el-tag
              v-for="perm in userStore.permissions"
              :key="perm"
              style="margin: 5px"
            >
              {{ perm }}
            </el-tag>
          </div>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const getRoleName = (role) => {
  const roleMap = {
    'SUPER_ADMIN': '系统超级管理员',
    'POLITICS_ADMIN': '政治处管理员',
    'DEPT_HEAD': '部门负责人',
    'ANALYST': '研判人员',
    'SELF': '本人账号'
  }
  return roleMap[role] || role || '未知'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch (error) {
    // 用户取消操作
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.header-left h2 {
  margin: 0;
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.welcome-text {
  font-size: 14px;
  color: #666;
}

.main {
  padding: 20px;
}

.welcome-card {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.user-info,
.permissions {
  margin-top: 20px;
}

.user-info h3,
.permissions h3 {
  margin-bottom: 15px;
  color: #333;
}
</style>
