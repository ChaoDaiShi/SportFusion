<template>
  <div class="industry-dashboard">
    <h2 class="page-title">产业全景可视化大屏</h2>

    <!-- 概览指标 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6">
        <StatCard label="企业总数" :value="overview.total_enterprises" unit="家" icon="OfficeBuilding" color="#409eff" />
      </el-col>
      <el-col :span="6">
        <StatCard label="体育企业数" :value="overview.sport_enterprises" unit="家" icon="TrophyBase" color="#67c23a" />
      </el-col>
      <el-col :span="6">
        <StatCard label="总产出指数" :value="overview.total_output_index" unit="" icon="Coin" color="#e6a23c" />
      </el-col>
      <el-col :span="6">
        <StatCard label="平均体育占比" :value="overview.avg_sport_ratio_pct" unit="%" icon="TrendCharts" color="#f56c6c" />
      </el-col>
    </el-row>

    <!-- 关键指标仪表盘 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="8">
        <el-card>
          <GaugeChart title="CR3市场集中度" :value="gauges.cr3" :max="100" unit="%" color="#409eff" :height="200" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <GaugeChart title="产业多样性指数" :value="gauges.diversity" :max="1" unit="" color="#67c23a" :height="200" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <GaugeChart title="跨界经营率" :value="gauges.crossoverRate" :max="100" unit="%" color="#e6a23c" :height="200" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 业态结构饼图 + 区域热力图 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="12">
        <el-card>
          <template #header>业态结构分布</template>
          <PieChart title="" :data="pieData" :height="400" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>全国产业规模热力图</template>
          <MapHeatmap title="" :data="mapData" :height="400" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 产业健康雷达图 + 企业漏斗图 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="12">
        <el-card>
          <template #header>产业健康度评估（6维雷达）</template>
          <RadarChart title="" :indicators="radarIndicators" :series="radarSeries" :height="400" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>企业识别漏斗</template>
          <FunnelChart title="" :data="funnelData" :height="400" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 区域×业态堆叠柱状图 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="24">
        <el-card>
          <template #header>Top10区域业态结构（堆叠柱状图）</template>
          <BarChart title="" :labels="stackedLabels" :series="stackedSeries" yName="企业数量" :height="400" :stacked="true" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 各业态年度趋势 + 业态矩形树图 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="14">
        <el-card>
          <template #header>各业态年度趋势（2019-2025）</template>
          <LineChart title="" :labels="trendLabels" :series="trendSeries" :height="380" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>业态规模矩形树图</template>
          <TreemapChart title="" :data="treemapData" name="产出指数" :height="380" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import StatCard from '../components/StatCard.vue'
import PieChart from '../components/PieChart.vue'
import MapHeatmap from '../components/MapHeatmap.vue'
import LineChart from '../components/LineChart.vue'
import BarChart from '../components/BarChart.vue'
import GaugeChart from '../components/GaugeChart.vue'
import RadarChart from '../components/RadarChart.vue'
import FunnelChart from '../components/FunnelChart.vue'
import TreemapChart from '../components/TreemapChart.vue'
import { getDashboardData } from '../api/chart'
import { useDataStore } from '../store/data'

const dataStore = useDataStore()

const overview = ref({
  total_enterprises: 0, sport_enterprises: 0,
  total_output_index: 0, avg_sport_ratio_pct: 0, crossover_count: 0,
})
const pieData = ref([])
const mapData = ref([])
const trendLabels = ref([])
const trendSeries = ref([])
const gauges = ref({ cr3: 0, diversity: 0, crossoverRate: 0 })
const radarIndicators = ref([])
const radarSeries = ref([])
const funnelData = ref([])
const stackedLabels = ref([])
const stackedSeries = ref([])
const treemapData = ref([])

// --------------- Demo data ---------------
const pieDemo = [
  { name: '赛事运营', value: 12850 }, { name: '健身服务', value: 9630 },
  { name: '体育培训', value: 7540 }, { name: '体育用品', value: 11200 },
  { name: '运动康复', value: 2340 }, { name: '其他体育', value: 3120 },
]

const mapDemo = [
  { name: '北京', value: 8520 }, { name: '上海', value: 7810 }, { name: '广东', value: 12450 },
  { name: '浙江', value: 6420 }, { name: '江苏', value: 7180 }, { name: '山东', value: 5360 },
  { name: '四川', value: 3980 }, { name: '湖北', value: 3450 }, { name: '福建', value: 4120 },
]

const trendDemoLabels = ['2019', '2020', '2021', '2022', '2023', '2024']
const trendDemoSeries = [
  { name: '赛事', data: [8200, 7800, 9500, 10500, 11800, 12850] },
  { name: '健身', data: [6500, 5800, 7200, 8300, 9100, 9630] },
  { name: '培训', data: [4800, 4200, 5500, 6200, 6800, 7540] },
  { name: '用品', data: [7000, 7200, 8500, 9200, 10200, 11200] },
]

// --------------- Chart data builders ---------------
function buildAllDemo() {
  overview.value = {
    total_enterprises: 76687, sport_enterprises: 8950,
    total_output_index: 578000, avg_sport_ratio_pct: 64.71, crossover_count: 977,
  }
  pieData.value = pieDemo
  mapData.value = mapDemo
  trendLabels.value = trendDemoLabels
  trendSeries.value = trendDemoSeries

  // Gauges
  gauges.value = { cr3: 67.9, diversity: 0.76, crossoverRate: 10.92 }

  // Radar
  radarIndicators.value = [
    { name: '产业规模', max: 100 },
    { name: '业态多样性', max: 100 },
    { name: '均衡度', max: 100 },
    { name: '区域集中度', max: 100 },
    { name: '专业化程度', max: 100 },
    { name: '跨界活力', max: 100 },
  ]
  radarSeries.value = [{
    name: '当前产业',
    data: [85, 76, 62, 68, 73, 55],
    areaStyle: { opacity: 0.2, color: '#409eff' },
    lineStyle: { color: '#409eff' },
    itemStyle: { color: '#409eff' },
  }]

  // Funnel
  funnelData.value = [
    { name: '全量企业', value: 76687 },
    { name: '含体育关键词', value: 32150 },
    { name: '体育相关企业', value: 12480 },
    { name: '明确体育企业', value: 8950 },
    { name: '跨界经营企业', value: 977 },
  ]

  // Stacked bar
  stackedLabels.value = ['成都', '绵阳', '宜宾', '乐山', '泸州', '南充', '德阳', '达州', '广安', '眉山']
  const catColors = {
    '健身休闲': '#409eff', '体育用品': '#67c23a', '体育赛事': '#e6a23c',
    '体育培训': '#f56c6c', '体育场馆': '#909399', '体育管理': '#9b59b6',
  }
  const regionCats = {
    '成都': [2200, 1800, 1200, 950, 600, 400],
    '绵阳': [380, 250, 180, 140, 80, 50],
    '宜宾': [290, 200, 140, 100, 60, 40],
    '乐山': [260, 180, 120, 90, 50, 35],
    '泸州': [220, 150, 100, 75, 45, 30],
    '南充': [190, 130, 85, 65, 40, 25],
    '德阳': [170, 110, 75, 55, 35, 20],
    '达州': [140, 90, 60, 45, 28, 18],
    '广安': [120, 80, 52, 38, 22, 15],
    '眉山': [105, 70, 45, 32, 18, 12],
  }
  const catNames = ['健身休闲', '体育用品', '体育赛事', '体育培训', '体育场馆', '体育管理']
  stackedSeries.value = catNames.map((cat, i) => ({
    name: cat,
    data: stackedLabels.value.map((r) => regionCats[r]?.[i] || 0),
    itemStyle: { color: catColors[cat] },
    last: i === catNames.length - 1,
  }))

  // Treemap
  treemapData.value = [
    { name: '健身休闲', value: 3134, itemStyle: { color: '#409eff' } },
    { name: '体育用品', value: 2321, itemStyle: { color: '#67c23a' } },
    { name: '体育赛事', value: 1245, itemStyle: { color: '#e6a23c' } },
    { name: '体育培训', value: 895, itemStyle: { color: '#f56c6c' } },
    { name: '体育场馆', value: 754, itemStyle: { color: '#909399' } },
    { name: '体育管理', value: 601, itemStyle: { color: '#9b59b6' } },
    { name: '电子竞技', value: 143, itemStyle: { color: '#e056a0' } },
    { name: '体育传媒', value: 116, itemStyle: { color: '#1abc9c' } },
  ]
}

onMounted(async () => {
  try {
    const fileId = dataStore.queryParams.fileId
    const res = await getDashboardData(fileId)
    if (res.code === 200 && res.data) {
      const d = res.data
      overview.value = d.overview || overview.value

      // Pie & Map & Line from API
      pieData.value = d.pie?.series?.[0]?.data || pieDemo
      mapData.value = d.map?.data || mapDemo
      trendLabels.value = d.line?.labels || trendDemoLabels
      trendSeries.value = d.line?.series || trendDemoSeries

      // Gauges
      if (d.concentration) {
        gauges.value.cr3 = d.concentration.cr3_pct || 0
      }
      if (d.structure) {
        gauges.value.diversity = d.structure.diversity_index || 0
        gauges.value.crossoverRate = d.structure.crossover_rate_pct || 0
      }

      // Radar from structure/concentration
      if (d.overview && d.structure && d.concentration) {
        const scaleScore = Math.min(100, Math.round((d.overview.total_output_index || 0) / 6000))
        const divScore = Math.round((d.structure.diversity_index || 0) * 100)
        const balScore = d.structure.balance_assessment === '业态较为多元，存在主导业态' ? 62
          : d.structure.balance_assessment === '高度多元' ? 85 : 45
        const concScore = Math.round(d.concentration.cr3_pct || 0)
        const specScore = Math.round(((d.structure.dominant_category?.share_pct || 0) / 40) * 100)
        const crossScore = Math.round((d.structure.crossover_rate_pct || 0) * 5)

        radarIndicators.value = [
          { name: '产业规模', max: 100 }, { name: '业态多样性', max: 100 },
          { name: '均衡度', max: 100 }, { name: '区域集中度', max: 100 },
          { name: '专业化程度', max: 100 }, { name: '跨界活力', max: 100 },
        ]
        radarSeries.value = [{
          name: '当前产业',
          data: [scaleScore, divScore, balScore, concScore, specScore, crossScore],
          areaStyle: { opacity: 0.2, color: '#409eff' },
          lineStyle: { color: '#409eff' },
          itemStyle: { color: '#409eff' },
        }]
      }

      // Funnel from overview
      if (d.overview) {
        const total = d.overview.total_enterprises || 76687
        const sport = d.overview.sport_enterprises || 8950
        const crossover = d.overview.crossover_count || 977
        funnelData.value = [
          { name: '全量企业', value: total },
          { name: '含体育业务', value: Math.round(total * 0.42) },
          { name: '体育相关企业', value: Math.round(sport * 1.4) },
          { name: '明确体育企业', value: sport },
          { name: '跨界经营企业', value: crossover },
        ]
      }

      // Stacked bar & Treemap from category data
      if (d.pie?.series?.[0]?.data) {
        treemapData.value = d.pie.series[0].data
      }
      if (d.bar?.series) {
        stackedLabels.value = d.bar.labels || stackedLabels.value
        stackedSeries.value = d.bar.series.map((s, i, arr) => ({
          ...s, last: i === arr.length - 1,
        }))
      }

      // Fill remaining with demo
      if (!radarIndicators.value.length) buildRemainingDemo()
      return
    }
  } catch { /* fallback */ }

  buildAllDemo()
})

function buildRemainingDemo() {
  // Called when API succeeded for some but not all fields
  if (!radarIndicators.value.length) {
    radarIndicators.value = [
      { name: '产业规模', max: 100 }, { name: '业态多样性', max: 100 },
      { name: '均衡度', max: 100 }, { name: '区域集中度', max: 100 },
      { name: '专业化程度', max: 100 }, { name: '跨界活力', max: 100 },
    ]
    radarSeries.value = [{
      name: '当前产业', data: [85, 76, 62, 68, 73, 55],
      areaStyle: { opacity: 0.2, color: '#409eff' },
      lineStyle: { color: '#409eff' }, itemStyle: { color: '#409eff' },
    }]
  }
  if (!funnelData.value.length) {
    funnelData.value = [
      { name: '全量企业', value: 76687 }, { name: '含体育关键词', value: 32150 },
      { name: '体育相关企业', value: 12480 }, { name: '明确体育企业', value: 8950 },
      { name: '跨界经营企业', value: 977 },
    ]
  }
  if (!stackedLabels.value.length) {
    stackedLabels.value = ['成都', '绵阳', '宜宾', '乐山', '泸州', '南充', '德阳', '达州', '广安', '眉山']
  }
  if (!treemapData.value.length) {
    treemapData.value = [
      { name: '健身休闲', value: 3134 }, { name: '体育用品', value: 2321 },
      { name: '体育赛事', value: 1245 }, { name: '体育培训', value: 895 },
    ]
  }
}
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; }
</style>
