/**
 * 数字格式化 - 万元
 */
export function formatMoney(value, decimals = 2) {
  if (value == null) return '0.00'
  return Number(value).toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * 百分比格式化
 */
export function formatPercent(value, decimals = 1) {
  if (value == null) return '0.0%'
  return (Number(value) * 100).toFixed(decimals) + '%'
}

/**
 * 日期格式化
 */
export function formatDate(date, format = 'YYYY-MM-DD') {
  if (!date) return ''
  const d = new Date(date)
  const map = {
    YYYY: d.getFullYear(),
    MM: String(d.getMonth() + 1).padStart(2, '0'),
    DD: String(d.getDate()).padStart(2, '0'),
    HH: String(d.getHours()).padStart(2, '0'),
    mm: String(d.getMinutes()).padStart(2, '0'),
    ss: String(d.getSeconds()).padStart(2, '0'),
  }
  return format.replace(/YYYY|MM|DD|HH|mm|ss/g, (k) => map[k])
}

/**
 * 文件大小格式化
 */
export function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return size.toFixed(1) + ' ' + units[i]
}

/**
 * 业态分类标签颜色映射
 */
export function getCategoryColor(category) {
  const map = {
    '赛事': '#409eff',
    '健身': '#67c23a',
    '培训': '#e6a23c',
    '用品': '#f56c6c',
    '非体育': '#909399',
  }
  return map[category] || '#909399'
}

/**
 * CSV数据导出
 */
export function exportCSV(data, filename = 'export.csv') {
  if (!data || !data.length) return
  const headers = Object.keys(data[0])
  const rows = data.map((row) => headers.map((h) => `"${String(row[h] ?? '').replace(/"/g, '""')}"`).join(','))
  const csv = [headers.join(','), ...rows].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
