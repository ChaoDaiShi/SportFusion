<template>
  <div class="review-workbench">
    <h2 class="page-title">人工复核工作台</h2>

    <!-- 统计概览 -->
    <el-row :gutter="16" style="margin-bottom:16px" v-if="reviewStore.stats">
      <el-col :span="3">
        <div class="mini-stat">
          <div class="mini-value">{{ reviewStore.stats.total_tasks }}</div>
          <div class="mini-label">总计</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat pending">
          <div class="mini-value">{{ reviewStore.stats.pending }}</div>
          <div class="mini-label">待分配</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat reviewing">
          <div class="mini-value">{{ (reviewStore.stats.assigned || 0) + (reviewStore.stats.reviewing || 0) }}</div>
          <div class="mini-label">复核中</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat warning">
          <div class="mini-value">{{ reviewStore.stats.disputed }}</div>
          <div class="mini-label">待仲裁</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat success">
          <div class="mini-value">{{ (reviewStore.stats.confirmed || 0) + (reviewStore.stats.locked || 0) }}</div>
          <div class="mini-label">已确认/锁定</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat">
          <div class="mini-value">{{ reviewStore.stats.p1_count }}</div>
          <div class="mini-label">P1高风险</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat">
          <div class="mini-value">{{ reviewStore.stats.consensus_rate }}%</div>
          <div class="mini-label">一致性</div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="mini-stat">
          <div class="mini-value">{{ reviewStore.stats.arbitration_rate }}%</div>
          <div class="mini-label">仲裁率</div>
        </div>
      </el-col>
    </el-row>

    <!-- 操作栏 -->
    <el-card class="section-card" style="margin-bottom:16px">
      <el-row :gutter="12" align="middle">
        <el-col :span="4">
          <el-button type="primary" @click="generateTasks" :loading="reviewStore.loading">
            生成复核任务
          </el-button>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterPriority" placeholder="优先级" clearable style="width:100%">
            <el-option v-for="p in ['P1','P2','P3','P4']" :key="p" :label="p" :value="p" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterStatus" placeholder="状态" clearable style="width:100%">
            <el-option label="待分配" value="pending" />
            <el-option label="已分配" value="assigned" />
            <el-option label="复核中" value="reviewing" />
            <el-option label="待仲裁" value="disputed" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已锁定" value="locked" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-input v-model="filterAssignee" placeholder="复核员" clearable />
        </el-col>
        <el-col :span="4">
          <el-button @click="loadTasks">刷新</el-button>
        </el-col>
        <el-col :span="4">
          <el-tag v-if="reviewStore.stats" type="info">
            共 {{ reviewStore.stats.total_tasks }} 个任务
          </el-tag>
        </el-col>
      </el-row>
    </el-card>

    <!-- Tab区域 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: 任务池 -->
      <el-tab-pane label="任务池" name="pool">
        <el-table :data="filteredTasks" stripe border size="small" max-height="500" empty-text="暂无复核任务">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="enterprise_name" label="企业名称" min-width="160" />
          <el-table-column prop="priority" label="优先级" width="70" align="center">
            <template #default="{ row }">
              <el-tag :type="getPriorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status_label" label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sport_category" label="业态" width="100" />
          <el-table-column label="SportShare" width="100" align="center">
            <template #default="{ row }">
              {{ (row.sport_share * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="85" align="center">
            <template #default="{ row }">
              {{ row.confidence ? (row.confidence * 100).toFixed(0) + '%' : '—' }}
            </template>
          </el-table-column>
          <el-table-column label="分配" min-width="120">
            <template #default="{ row }">
              <span v-if="row.assigned_to_a" style="font-size:12px">
                A: {{ row.assigned_to_a }} | B: {{ row.assigned_to_b }}
              </span>
              <span v-else style="color:#c0c4cc">未分配</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openAssignDialog(row)">分配</el-button>
              <el-button type="success" link size="small" @click="openReviewForm(row)">复核</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 我的任务 -->
      <el-tab-pane label="我的任务" name="mine">
        <el-empty description="请先在任务池中领取复核任务" v-if="!myTasks.length">
          <template #image><el-icon :size="60"><UserFilled /></el-icon></template>
        </el-empty>
        <el-table v-else :data="myTasks" stripe border size="small">
          <el-table-column prop="enterprise_name" label="企业名称" min-width="160" />
          <el-table-column prop="priority" label="优先级" width="70" align="center">
            <template #default="{ row }">
              <el-tag :type="getPriorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sport_category" label="业态" width="100" />
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openReviewForm(row)">执行复核</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 3: 仲裁中心 -->
      <el-tab-pane label="仲裁中心" name="arbitration">
        <el-empty description="暂无需仲裁的任务" v-if="!disputedTasks.length" />
        <div v-else>
          <div v-for="task in disputedTasks" :key="task.id" style="margin-bottom:16px">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>{{ task.enterprise_name }}</span>
                  <el-tag type="danger" size="small">{{ task.priority }} · 待仲裁</el-tag>
                </div>
              </template>
              <el-row :gutter="16">
                <el-col :span="11">
                  <div class="opinion-box">
                    <div class="opinion-title">复核员A: {{ task.assigned_to_a }}</div>
                    <div class="opinion-content">{{ getRecordSummary(task.id, 'A') }}</div>
                  </div>
                </el-col>
                <el-col :span="2" style="text-align:center;line-height:80px">
                  <span style="font-size:24px;color:#f56c6c">VS</span>
                </el-col>
                <el-col :span="11">
                  <div class="opinion-box">
                    <div class="opinion-title">复核员B: {{ task.assigned_to_b }}</div>
                    <div class="opinion-content">{{ getRecordSummary(task.id, 'B') }}</div>
                  </div>
                </el-col>
              </el-row>
              <div style="margin-top:12px;text-align:center">
                <el-button type="primary" @click="openArbitrationForm(task)">进行仲裁</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 4: 动态名录 -->
      <el-tab-pane label="动态名录" name="directory">
        <el-empty description="暂无已确认/锁定的企业" v-if="!lockedTasks.length" />
        <el-table v-else :data="lockedTasks" stripe border size="small">
          <el-table-column prop="enterprise_name" label="企业名称" min-width="160" />
          <el-table-column prop="sport_category" label="最终业态" width="110" />
          <el-table-column label="最终比重" width="100" align="center">
            <template #default="{ row }">
              <span style="color:#67c23a;font-weight:bold">
                {{ getFinalShare(row) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="status_label" label="状态" width="90" align="center" />
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button type="warning" link size="small" @click="unlockTask(row)">解锁</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 分配对话框 -->
    <el-dialog v-model="assignVisible" title="分配复核员" width="400px">
      <el-form label-width="80px">
        <el-form-item label="复核员A">
          <el-input v-model="assignForm.reviewerA" placeholder="输入复核员姓名" />
        </el-form-item>
        <el-form-item label="复核员B">
          <el-input v-model="assignForm.reviewerB" placeholder="输入复核员姓名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" @click="doAssign">确认分配</el-button>
      </template>
    </el-dialog>

    <!-- 复核表单对话框 -->
    <el-dialog v-model="reviewVisible" title="人工复核" width="550px">
      <template v-if="reviewingTask">
        <el-descriptions :column="1" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="企业">{{ reviewingTask.enterprise_name }}</el-descriptions-item>
          <el-descriptions-item label="模型业态">{{ reviewingTask.sport_category }}</el-descriptions-item>
          <el-descriptions-item label="模型比重">{{ (reviewingTask.sport_share * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ reviewingTask.confidence ? (reviewingTask.confidence * 100).toFixed(0) + '%' : '—' }}</el-descriptions-item>
        </el-descriptions>
        <el-form :model="reviewForm" label-width="100px">
          <el-form-item label="复核角色">
            <el-radio-group v-model="reviewForm.role">
              <el-radio value="A">复核员A</el-radio>
              <el-radio value="B">复核员B</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="复核人员">
            <el-input v-model="reviewForm.reviewerName" placeholder="输入姓名" />
          </el-form-item>
          <el-form-item label="体育属性">
            <el-radio-group v-model="reviewForm.sportAttribute">
              <el-radio value="yes">是</el-radio>
              <el-radio value="no">否</el-radio>
              <el-radio value="uncertain">存疑</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="业态修正">
            <el-input v-model="reviewForm.categoryOverride" placeholder="如需修正模型业态，请输入" />
          </el-form-item>
          <el-form-item label="比重修正">
            <el-slider v-model="reviewForm.shareOverride" :min="0" :max="1" :step="0.01"
              show-input :format-tooltip="(v) => (v * 100).toFixed(1) + '%'" />
          </el-form-item>
          <el-form-item label="判断理由">
            <el-input v-model="reviewForm.reason" type="textarea" :rows="3" placeholder="请说明复核依据..." />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" @click="doSubmitReview" :loading="submitting">提交复核意见</el-button>
      </template>
    </el-dialog>

    <!-- 仲裁表单对话框 -->
    <el-dialog v-model="arbitrationVisible" title="分歧仲裁" width="550px">
      <el-form :model="arbitrationForm" label-width="100px">
        <el-form-item label="仲裁员">
          <el-input v-model="arbitrationForm.arbiterName" placeholder="输入仲裁员姓名" />
        </el-form-item>
        <el-form-item label="体育属性">
          <el-radio-group v-model="arbitrationForm.sportAttribute">
            <el-radio value="yes">是</el-radio>
            <el-radio value="no">否</el-radio>
            <el-radio value="uncertain">存疑</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="最终业态">
          <el-input v-model="arbitrationForm.category" />
        </el-form-item>
        <el-form-item label="最终比重">
          <el-slider v-model="arbitrationForm.share" :min="0" :max="1" :step="0.01"
            show-input :format-tooltip="(v) => (v * 100).toFixed(1) + '%'" />
        </el-form-item>
        <el-form-item label="裁决理由">
          <el-input v-model="arbitrationForm.reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="arbitrationVisible = false">取消</el-button>
        <el-button type="danger" @click="doSubmitArbitration">确认仲裁</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useReviewStore } from '../store/review'
import { useDataStore } from '../store/data'
import { useRecognitionStore } from '../store/recognition'

const reviewStore = useReviewStore()
const dataStore = useDataStore()
const recognitionStore = useRecognitionStore()

const activeTab = ref('pool')
const filterPriority = ref('')
const filterStatus = ref('')
const filterAssignee = ref('')
const submitting = ref(false)

// 对话框状态
const assignVisible = ref(false)
const assignTarget = ref(null)
const assignForm = reactive({ reviewerA: '', reviewerB: '' })

const reviewVisible = ref(false)
const reviewingTask = ref(null)
const reviewForm = reactive({
  role: 'A', reviewerName: '', sportAttribute: 'yes',
  categoryOverride: '', shareOverride: 0.5, reason: '',
})

const arbitrationVisible = ref(false)
const arbitrationTarget = ref(null)
const arbitrationForm = reactive({
  arbiterName: '', sportAttribute: 'yes',
  category: '', share: 0.5, reason: '',
})

// 筛选
const filteredTasks = computed(() => {
  let list = reviewStore.tasks
  if (filterPriority.value) list = list.filter((t) => t.priority === filterPriority.value)
  if (filterStatus.value) list = list.filter((t) => t.status === filterStatus.value)
  if (filterAssignee.value) {
    list = list.filter((t) =>
      t.assigned_to_a === filterAssignee.value || t.assigned_to_b === filterAssignee.value
    )
  }
  return list
})

const myTasks = computed(() =>
  reviewStore.tasks.filter((t) =>
    t.assigned_to_a === '当前用户' || t.assigned_to_b === '当前用户'
  )
)

const disputedTasks = computed(() =>
  reviewStore.tasks.filter((t) => t.status === 'disputed')
)

const lockedTasks = computed(() =>
  reviewStore.tasks.filter((t) => t.status === 'confirmed' || t.status === 'locked')
)

function getPriorityType(p) {
  return { P1: 'danger', P2: 'warning', P3: 'info', P4: '' }[p] || 'info'
}

function getStatusType(s) {
  return {
    pending: 'info', assigned: '', reviewing: 'warning',
    disputed: 'danger', confirmed: 'success', locked: 'success',
  }[s] || 'info'
}

function getRecordSummary(taskId, role) {
  const detail = reviewStore.tasks.find((t) => t.id === taskId)
  return detail ? `待查看详情` : '暂无记录'
}

function getFinalShare(task) {
  return task.sport_share ? (task.sport_share * 100).toFixed(1) + '%' : '—'
}

// 生成任务
async function generateTasks() {
  const fileId = dataStore.queryParams.fileId
  if (!fileId) { ElMessage.warning('请先在数据管理中上传数据'); return }

  try {
    await dataStore.fetchPreprocessResult(fileId)
    const sportRes = await dataStore.fetchSportEnterprises(fileId,
      { page: 1, page_size: 10000 })
    if (sportRes.code !== 200) { ElMessage.warning('获取数据失败'); return }

    const records = sportRes.data?.records || []
    const enterprises = records.map((r) => ({
      enterprise_id: r.id,
      enterprise_name: r['详细名称'] || r.name || '',
      credit_code: r['统一社会信用代码'] || r.credit_code || '',
      industry_code: r['行业代码'] || r.industry_code || '',
      business_text: r['主要业务活动'] || r.main_business || '',
    }))

    const recRes = await recognitionStore.recognizeBatch(
      enterprises.map((e) => ({
        enterprise_id: e.enterprise_id, enterprise_name: e.enterprise_name,
        industry_code: e.industry_code, business_text: e.business_text,
      }))
    )

    if (!recRes?.results) { ElMessage.error('识别失败'); return }

    await reviewStore.doGenerateTasks({
      batch_id: fileId,
      recognition_results: recRes.results,
    })
    ElMessage.success(`已生成 ${reviewStore.tasks.length} 个复核任务`)
  } catch (e) {
    ElMessage.error('生成失败: ' + (e.message || '未知错误'))
  }
}

async function loadTasks() {
  await reviewStore.fetchTasks({ page: 1, page_size: 100 })
}

onMounted(loadTasks)

// 分配
function openAssignDialog(task) {
  assignTarget.value = task
  assignForm.reviewerA = ''
  assignForm.reviewerB = ''
  assignVisible.value = true
}

async function doAssign() {
  if (!assignForm.reviewerA || !assignForm.reviewerB) {
    ElMessage.warning('请填写两位复核员'); return
  }
  await reviewStore.doAssignTask(assignTarget.value.id, {
    task_ids: [assignTarget.value.id],
    reviewer_a: assignForm.reviewerA,
    reviewer_b: assignForm.reviewerB,
  })
  ElMessage.success('复核员已分配')
  assignVisible.value = false
}

// 复核
function openReviewForm(task) {
  reviewingTask.value = task
  reviewForm.role = 'A'
  reviewForm.reviewerName = task.assigned_to_a || ''
  reviewForm.sportAttribute = 'yes'
  reviewForm.categoryOverride = task.sport_category || ''
  reviewForm.shareOverride = task.sport_share || 0.5
  reviewForm.reason = ''
  reviewVisible.value = true
}

async function doSubmitReview() {
  if (!reviewForm.reviewerName) { ElMessage.warning('请输入复核人员'); return }
  submitting.value = true
  try {
    await reviewStore.doSubmitRecord({
      review_task_id: reviewingTask.value.id,
      reviewer_name: reviewForm.reviewerName,
      reviewer_role: reviewForm.role,
      sport_attribute: reviewForm.sportAttribute,
      sport_category_override: reviewForm.categoryOverride || null,
      sport_share_override: reviewForm.shareOverride,
      reason: reviewForm.reason,
    })
    ElMessage.success('复核意见已提交')
    reviewVisible.value = false
  } catch {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

// 仲裁
function openArbitrationForm(task) {
  arbitrationTarget.value = task
  arbitrationForm.arbiterName = ''
  arbitrationForm.sportAttribute = 'yes'
  arbitrationForm.category = task.sport_category || ''
  arbitrationForm.share = task.sport_share || 0.5
  arbitrationForm.reason = ''
  arbitrationVisible.value = true
}

async function doSubmitArbitration() {
  if (!arbitrationForm.arbiterName) { ElMessage.warning('请输入仲裁员'); return }
  await reviewStore.doSubmitArbitration({
    review_task_id: arbitrationTarget.value.id,
    arbiter_name: arbitrationForm.arbiterName,
    final_sport_attribute: arbitrationForm.sportAttribute,
    final_sport_category: arbitrationForm.category || null,
    final_sport_share: arbitrationForm.share,
    decision_reason: arbitrationForm.reason,
  })
  ElMessage.success('仲裁完成，任务已锁定')
  arbitrationVisible.value = false
}

function unlockTask(task) {
  ElMessageBox.confirm('确认解锁该企业？解锁后将回到待复核状态。', '确认解锁', {
    confirmButtonText: '确认解锁', type: 'warning',
  }).then(() => {
    task.status = 'pending'
    task.status_label = '待分配'
    ElMessage.success('已解锁')
  }).catch(() => {})
}
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; color: #303133; }
.section-card { margin-bottom: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.mini-stat {
  text-align: center; padding: 12px 8px; background: #f5f7fa;
  border-radius: 8px; border-left: 3px solid #dcdfe6;
}
.mini-stat.pending { border-left-color: #909399; }
.mini-stat.reviewing { border-left-color: #409eff; }
.mini-stat.warning { border-left-color: #e6a23c; }
.mini-stat.success { border-left-color: #67c23a; }
.mini-value { font-size: 20px; font-weight: 700; color: #303133; }
.mini-label { font-size: 12px; color: #909399; margin-top: 2px; }
.opinion-box {
  padding: 12px; background: #f5f7fa; border-radius: 6px;
  min-height: 60px;
}
.opinion-title { font-weight: 600; font-size: 13px; margin-bottom: 6px; }
.opinion-content { font-size: 12px; color: #606266; }
</style>
