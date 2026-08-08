export const navigationGroups = [
  {
    label: '监测总览',
    items: [
      { path: '/monitoring', label: '统计监测驾驶舱', icon: 'DataAnalysis' },
      { path: '/risks', label: '风险事件中心', icon: 'Warning' },
    ],
  },
  {
    label: '核心分析',
    items: [
      { path: '/data', label: '企业数据治理', icon: 'Files' },
      { path: '/recognition', label: '企业边界识别', icon: 'Search' },
      { path: '/compare', label: '经营比重测算', icon: 'ScaleToOriginal' },
      { path: '/industry-analysis', label: '产业规模分析', icon: 'TrendCharts' },
    ],
  },
  {
    label: '可信验证',
    items: [
      { path: '/model-evaluation', label: '模型性能评估', icon: 'Histogram' },
      { path: '/data', label: '数据过程追踪', icon: 'Connection' },
    ],
  },
  {
    label: '成果应用',
    items: [
      { path: '/assistant', label: '智能决策问答', icon: 'ChatLineSquare' },
      { path: '/export', label: '报告与成果中心', icon: 'Download' },
    ],
  },
]
