<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <div class="error-icon">404</div>
      <h2 class="error-title">页面未找到</h2>
      <p class="error-desc">抱歉，您访问的页面不存在或已被删除</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.not-found-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
}

.not-found-content {
  text-align: center;
  padding: 60px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 80px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 20px;
}

.error-title {
  font-size: 28px;
  color: #303133;
  margin-bottom: 12px;
}

.error-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 30px;
}
</style>
