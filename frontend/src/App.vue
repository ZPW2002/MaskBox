<template>
  <el-config-provider :locale="elementLocale">
    <div class="app-shell">
      <header class="app-header">
        <div class="brand">
          <div class="brand-mark">M</div>
          <div>
            <div class="brand-name">{{ t('common.appName') }}</div>
            <div class="brand-slogan">{{ t('common.slogan') }}</div>
          </div>
        </div>
        <el-menu mode="horizontal" :default-active="activePath" router class="app-menu">
          <el-menu-item index="/">{{ t('common.folders') }}</el-menu-item>
          <el-menu-item index="/masks">{{ t('common.masks') }}</el-menu-item>
        </el-menu>
        <div class="header-right">
          <el-select
            :model-value="locale"
            class="locale-select"
            @update:model-value="changeLocale"
          >
            <el-option label="中文" value="zh" />
            <el-option label="English" value="en" />
          </el-select>
        </div>
      </header>
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import en from 'element-plus/es/locale/lang/en'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import { setLocale, type AppLocale } from '@/i18n'

const { t, locale } = useI18n()
const route = useRoute()

const activePath = computed(() => route.path)
const elementLocale = computed(() => (locale.value === 'zh' ? zhCn : en))

function changeLocale(value: string | number | boolean | object | undefined): void {
  if (value === 'zh' || value === 'en') setLocale(value as AppLocale)
}
</script>

<style scoped>
.app-shell {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 250px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #7c4dff, #4d9fff);
  color: #fff;
  font-weight: 700;
  font-size: 20px;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 14px rgba(124, 77, 255, 0.28);
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.brand-slogan {
  font-size: 12px;
  color: #909399;
}

.app-menu {
  flex: 1;
  border-bottom: none;
}

.header-right {
  margin-left: auto;
}

.locale-select {
  width: 110px;
}

.app-main {
  flex: 1;
  padding: 20px 24px 32px;
}
</style>
