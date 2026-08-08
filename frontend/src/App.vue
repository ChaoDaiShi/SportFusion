<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span>体融识界</span></div>
      <nav aria-label="主导航">
        <section v-for="group in navigationGroups" :key="group.label" class="nav-group">
          <h2>{{ group.label }}</h2>
          <RouterLink v-for="item in group.items" :key="`${group.label}-${item.path}-${item.label}`" :to="item.path" class="nav-item">
            <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
          </RouterLink>
        </section>
      </nav>
      <div class="system-note"><span></span>真实接口优先<br>演示保障可用</div>
    </aside>
    <main class="app-main"><RouterView /></main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { navigationGroups } from './config/navigation'
</script>

<style scoped>
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 176px minmax(0, 1fr); background: var(--sf-bg); }
.app-sidebar { position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 18px 12px; border-right: 1px solid var(--sf-line); background: var(--sf-surface-muted); }
.brand { display: flex; align-items: center; gap: 9px; padding: 0 8px 18px; font-size: 16px; font-weight: 900; }
.brand-mark { width: 26px; height: 26px; border-radius: 7px; background: var(--sf-blue); box-shadow: 8px 8px 0 -4px var(--sf-red); }
.nav-group { margin-top: 15px; }
.nav-group h2 { margin: 0 8px 6px; color: #8a887f; font-size: 10px; letter-spacing: .12em; font-weight: 600; }
.nav-item { display: flex; align-items: center; gap: 8px; margin: 2px 0; padding: 9px 10px; border-radius: 7px; color: var(--sf-text); font-size: 13px; text-decoration: none; }
.nav-item.router-link-active { background: var(--sf-ink); color: white; font-weight: 800; }
.nav-item.router-link-active .el-icon { color: var(--sf-yellow); }
.system-note { margin-top: 20px; padding: 12px 8px; border-top: 1px solid #d7cebd; color: var(--sf-muted); font-size: 11px; line-height: 1.7; }
.system-note > span { display: inline-block; width: 7px; height: 7px; margin-right: 6px; border-radius: 50%; background: var(--sf-teal); }
.app-main { min-width: 0; padding: 18px; }
@media (max-width: 1024px) { .app-shell { grid-template-columns: 132px minmax(0, 1fr); }.brand { font-size: 14px; }.nav-item { font-size: 12px; padding-inline: 8px; }.app-main { padding: 12px; } }
</style>
