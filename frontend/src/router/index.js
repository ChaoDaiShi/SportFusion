import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/monitoring',
  },
  {
    path: '/monitoring',
    name: 'MonitoringCockpit',
    component: () => import('../views/MonitoringCockpit.vue'),
    meta: { title: '统计监测驾驶舱' },
  },
  {
    path: '/risks',
    name: 'RiskCenter',
    component: () => import('../views/RiskCenter.vue'),
    meta: { title: '风险事件中心' },
  },
  {
    path: '/industry-analysis',
    name: 'IndustryAnalysis',
    component: () => import('../views/IndustryDashboard.vue'),
    meta: { title: '产业规模分析' },
  },
  {
    path: '/assistant',
    name: 'AnalysisAssistant',
    component: () => import('../views/AnalysisAssistant.vue'),
    meta: { title: '智能决策问答' },
  },
  {
    path: '/model-evaluation',
    name: 'ModelEvaluation',
    component: () => import('../views/ModelEvaluation.vue'),
    meta: { title: '模型性能评估' },
  },
  {
    path: '/data',
    name: 'DataManage',
    component: () => import('../views/DataManage.vue'),
    meta: { title: '数据管理' },
  },
  {
    path: '/recognition',
    name: 'EnterpriseRecognition',
    component: () => import('../views/EnterpriseRecognition.vue'),
    meta: { title: '企业业务识别' },
  },
  {
    path: '/compare',
    name: 'MeasureCompare',
    component: () => import('../views/MeasureCompare.vue'),
    meta: { title: '测算对比验证' },
  },
  {
    path: '/share',
    name: 'SportShare',
    component: () => import('../views/SportShare.vue'),
    meta: { title: '经营比重测算' },
  },
  {
    path: '/scale',
    name: 'ScaleAnalysis',
    component: () => import('../views/ScaleAnalysis.vue'),
    meta: { title: '产业规模测算' },
  },
  {
    path: '/review',
    name: 'ReviewWorkbench',
    component: () => import('../views/ReviewWorkbench.vue'),
    meta: { title: '人工复核工作台' },
  },
  {
    path: '/dashboard',
    redirect: '/monitoring',
  },
  {
    path: '/export',
    name: 'ReportExport',
    component: () => import('../views/ReportExport.vue'),
    meta: { title: '报表导出' },
  },
  {
    path: '/directory',
    name: 'EnterpriseDirectory',
    component: () => import('../views/EnterpriseDirectory.vue'),
    meta: { title: '动态名录' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { title: '页面未找到' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title + ' - 体融识界'
  }
  next()
})

export default router
