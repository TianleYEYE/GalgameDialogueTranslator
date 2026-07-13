<template>
  <div class="app-shell">
    <main class="translator-console">
      <section class="topbar">
        <label class="window-picker">
          <span>{{ ui.gameWindow }}</span>
          <select v-model="selectedWindowLabel" @change="applySelectedWindow">
            <option value="">{{ ui.noWindowSelected }}</option>
            <option v-for="window in windowOptions" :key="window.hwnd" :value="window.label">
              {{ window.label }}
            </option>
          </select>
        </label>
        <button class="btn btn-ghost" :disabled="isTranslating" @click="refreshWindows">
          {{ ui.refreshWindows }}
        </button>
        <button class="btn btn-primary overlay-toggle" type="button" @click="toggleTranslationOverlay">
          {{ overlayVisible ? ui.hideOverlay : ui.showOverlay }}
        </button>
        <label class="stream-overlay-toggle" :title="overlayCaptureHint">
          <input v-model="overlayCaptureVisible" type="checkbox" />
          <span>{{ overlayCaptureLabel }}</span>
        </label>
        <button class="btn btn-ghost" type="button" @click="resetOverlayPosition">
          {{ overlayResetLabel }}
        </button>
        <button class="btn btn-ghost" type="button" @click="togglePlaceHint">
          {{ ui.placeBeside }}
        </button>
      </section>

      <section class="output-card">
        <div class="section-head">
          <span>{{ ui.translationOutput }}</span>
          <div class="reading-tools">
            <span>{{ ui.readingDirection }}</span>
            <button class="icon-toggle" :class="{ active: layout === 'horizontal' }" @click="layout = 'horizontal'">
              ↔
            </button>
            <button class="icon-toggle" :class="{ active: layout === 'vertical' }" @click="layout = 'vertical'">
              ↕
            </button>
            <span class="tool-divider"></span>
            <button class="icon-toggle" type="button" @click="showDisplayPanel = !showDisplayPanel">⚙</button>
          </div>
        </div>

        <div class="panel-stack" :class="{ horizontal: layout === 'horizontal' }">
          <section class="reading-panel">
            <div class="panel-meta">
              <span class="dot dot-source"></span>
              <span>{{ leftOutput }}</span>
              <button class="small-action" type="button" @click="collectSelection">{{ ui.collect }}</button>
            </div>
            <textarea
              ref="sourceTextarea"
              v-model="sourceText"
              class="dialogue-surface editable-panel"
              :style="panelFontStyle"
              spellcheck="false"
            ></textarea>
          </section>

          <section class="reading-panel">
            <div class="panel-meta">
              <span class="dot dot-target"></span>
              <span>{{ rightOutput }}</span>
              <button class="small-action" type="button" @click="copyTranslation">{{ ui.copy }}</button>
              <button class="small-action" type="button" @click="collectCurrent">{{ ui.collect }}</button>
            </div>
            <div class="dialogue-surface translated-panel" :style="panelFontStyle">
              <p>{{ translatedText || ui.emptyTranslation }}</p>
            </div>
          </section>
        </div>

        <div class="primary-actions">
          <button class="btn btn-primary btn-wide" :disabled="isTranslating" @click="startOcrTranslation">
            ▶ {{ isTranslating ? ui.translating : ui.start }}
          </button>
          <button class="btn btn-ghost btn-wide" :disabled="isTranslating" @click="runTextTranslation">
            ⟳ {{ ui.retranslate }}
          </button>
          <button class="btn btn-danger btn-wide" @click="stopTranslation">
            ■ {{ ui.stop }}
          </button>
        </div>
      </section>

      <section class="settings-deck">
        <div class="settings-panel">
          <h3>{{ ui.ocrEngine }}</h3>
          <label class="stack-field">
            <span>{{ ui.ocr }}</span>
            <select v-model="ocrEngine">
              <option>tesseract</option>
              <option>openai-vision</option>
            </select>
          </label>
          <button class="square-btn" type="button" @click="selectCaptureArea">{{ ui.selectArea }}</button>
        </div>

        <div class="settings-panel">
          <h3>{{ ui.translationService }}</h3>
          <label class="stack-field">
            <span>{{ ui.translator }}</span>
            <select v-model="translator">
              <option>deepseek</option>
              <option>grok</option>
              <option>openai</option>
              <option>libretranslate</option>
              <option>argos</option>
            </select>
          </label>
          <button class="square-btn" type="button" @click="showProviderPanel = !showProviderPanel">⚙</button>
        </div>

        <div class="settings-panel">
          <h3>{{ ui.textStyle }}</h3>
          <div class="font-stepper">
            <button @click="decreaseFont">A-</button>
            <input v-model="fontSize" />
            <button @click="increaseFont">A+</button>
          </div>
          <label class="stack-field">
            <span>{{ ui.fontFamily }}</span>
            <select v-model="fontFamily">
              <option>Microsoft YaHei UI</option>
              <option>SimSun</option>
              <option>Yu Mincho</option>
              <option>serif</option>
            </select>
          </label>
        </div>

        <div class="settings-panel">
          <h3>{{ ui.layoutMode }}</h3>
          <div class="layout-buttons">
            <button class="icon-toggle" :class="{ active: layout === 'horizontal' }" @click="layout = 'horizontal'">▦</button>
            <button class="icon-toggle" :class="{ active: layout === 'vertical' }" @click="layout = 'vertical'">▥</button>
          </div>
          <label class="stack-field">
            <span>{{ ui.systemLanguage }}</span>
            <select v-model="systemLanguage">
              <option value="en">English</option>
              <option value="zh-CN">简体中文</option>
            </select>
          </label>
        </div>

        <div class="settings-panel capture-preview">
          <h3>{{ ui.subtitleArea }}</h3>
          <button class="preview-refresh" :disabled="isPreviewing" type="button" @click="refreshCapturePreview">
            {{ isPreviewing ? ui.previewing : ui.refreshPreview }}
          </button>
          <div class="crop-preview">
            <img v-if="previewImage" :src="previewImage" alt="Selected subtitle area preview" />
            <div v-else class="preview-placeholder">{{ ui.noPreview }}</div>
          </div>
          <div class="crop-values">
            <input v-model="cropLeft" />
            <input v-model="cropTop" />
            <input v-model="cropRight" />
            <input v-model="cropBottom" />
          </div>
        </div>
      </section>

      <section v-if="showDisplayPanel || showProviderPanel" class="config-drawer">
        <div v-if="showDisplayPanel" class="drawer-grid">
          <label class="stack-field">
            <span>{{ ui.leftOutput }}</span>
            <select v-model="leftOutput">
              <option>Original OCR</option>
              <option>Japanese</option>
              <option>English</option>
              <option>Simplified Chinese</option>
              <option>Traditional Chinese</option>
            </select>
          </label>
          <label class="stack-field">
            <span>{{ ui.rightOutput }}</span>
            <select v-model="rightOutput">
              <option>Simplified Chinese</option>
              <option>Traditional Chinese</option>
              <option>English</option>
              <option>Japanese</option>
            </select>
          </label>
          <label class="check-field">
            <input v-model="lockCurrentLine" type="checkbox" />
            <span>{{ ui.lockCurrentLine }}</span>
          </label>
        </div>

        <div v-if="showProviderPanel" class="drawer-grid">
          <label class="stack-field">
            <span>{{ ui.model }}</span>
            <select v-model="model">
              <option v-for="modelOption in modelOptions" :key="modelOption" :value="modelOption">
                {{ modelOption }}
              </option>
              <option value="__custom__">{{ ui.customModel }}</option>
            </select>
          </label>
          <label v-if="model === '__custom__'" class="stack-field">
            <span>{{ ui.customModel }}</span>
            <input v-model="customModel" placeholder="model-id" />
          </label>
          <label class="stack-field">
            <span>{{ ui.apiUrl }}</span>
            <input v-model="apiUrl" />
          </label>
          <label class="stack-field">
            <span>{{ ui.apiKey }}</span>
            <input v-model="apiKey" type="password" autocomplete="off" />
          </label>
          <label class="stack-field">
            <span>{{ ui.libreUrl }}</span>
            <input v-model="libreUrl" />
          </label>
          <label class="stack-field">
            <span>{{ ui.libreTarget }}</span>
            <input v-model="libreTarget" />
          </label>
          <label class="stack-field">
            <span>{{ ui.intervalMs }}</span>
            <input v-model="intervalMs" />
          </label>
          <label class="stack-field">
            <span>{{ ui.context }}</span>
            <input v-model="contextLines" />
          </label>
          <label class="stack-field">
            <span>{{ ui.stableReads }}</span>
            <input v-model="stableReads" />
          </label>
        </div>
      </section>

      <section class="diagnostic-panel">
        <button class="vocab-toggle" type="button" @click="showLogPanel = !showLogPanel">
          <span>▣</span>
          {{ ui.logs }} ({{ logEntries.length }})
          <span class="chevron">{{ showLogPanel ? "⌃" : "⌄" }}</span>
        </button>
        <div v-if="showLogPanel" class="log-body">
          <div v-for="entry in logEntries" :key="entry.id" class="log-line" :class="entry.level">
            <span>{{ entry.time }}</span>
            <strong>{{ entry.level.toUpperCase() }}</strong>
            <p>{{ entry.message }}</p>
          </div>
        </div>
      </section>

      <section class="vocab-drawer">
        <button class="vocab-toggle" type="button" @click="toggleVocabularyPanel">
          <span>▰</span>
          {{ ui.vocabulary }} ({{ collectedCount }})
          <span class="chevron">{{ showVocabularyPanel ? "⌃" : "⌄" }}</span>
        </button>
        <div v-if="showVocabularyPanel" class="vocab-body">
          <div class="vocab-toolbar">
            <span>{{ vocabularyHint }}</span>
            <button class="small-action" type="button" @click="refreshVocabularyCount">{{ ui.refreshVocabulary }}</button>
          </div>
          <div class="vocab-filters">
            <input v-model="vocabularySearch" :placeholder="ui.vocabSearch" />
            <select v-model="vocabularyKindFilter">
              <option value="all">{{ ui.vocabAllKinds }}</option>
              <option value="word">{{ ui.vocabWords }}</option>
              <option value="line">{{ ui.vocabLines }}</option>
            </select>
            <select v-model="vocabularyStatusFilter">
              <option value="all">{{ ui.vocabAllStatuses }}</option>
              <option v-for="option in vocabularyStatusOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <select v-model="vocabularyPageSize">
              <option value="12">12 / page</option>
              <option value="24">24 / page</option>
              <option value="48">48 / page</option>
            </select>
          </div>
          <div v-if="vocabularyEntries.length" class="vocab-results">
            <div class="vocab-page-info">
              <span>{{ ui.vocabShowing }} {{ pagedVocabularyRows.length }} / {{ filteredVocabularyRows.length }}</span>
              <div class="vocab-pager">
                <button class="small-action" type="button" :disabled="vocabularyPage <= 1" @click="vocabularyPage -= 1">
                  {{ ui.vocabPrev }}
                </button>
                <span>{{ vocabularyPage }} / {{ vocabularyPageCount }}</span>
                <button class="small-action" type="button" :disabled="vocabularyPage >= vocabularyPageCount" @click="vocabularyPage += 1">
                  {{ ui.vocabNext }}
                </button>
              </div>
            </div>
            <div class="vocab-card-list">
              <article v-for="entry in pagedVocabularyRows" :key="entry.id" class="vocab-card">
                <div class="vocab-card-main">
                  <div>
                    <span class="vocab-label">{{ ui.vocabSource }}</span>
                    <p class="vocab-source-text">{{ entry.source }}</p>
                  </div>
                  <div>
                    <span class="vocab-label">{{ ui.vocabTranslation }}</span>
                    <p class="vocab-translation-text">{{ entry.translation || "..." }}</p>
                  </div>
                </div>
                <div class="vocab-card-footer">
                  <div class="vocab-card-meta">
                    <span>{{ entry.kind }}</span>
                    <span>{{ entry.sourceLanguage }} -> {{ entry.targetLanguage }}</span>
                    <span>{{ entry.createdAt }}</span>
                    <span>{{ entry.windowTitle }}</span>
                  </div>
                  <div class="vocab-card-actions">
                    <button
                      class="small-action vocab-fill"
                      type="button"
                      :disabled="isBackfillingVocabulary"
                      @click="retranslateVocabularyEntry(entry)"
                    >
                      {{ entry.translation ? ui.retranslateVocabulary : ui.backfillTranslation }}
                    </button>
                    <select class="vocab-status-select" :value="entry.status" @change="updateVocabularyStatus(entry, $event.target.value)">
                      <option v-for="option in vocabularyStatusOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </option>
                    </select>
                    <button
                      class="small-action vocab-delete"
                      type="button"
                      :disabled="isDeletingVocabulary"
                      @click="deleteVocabularyEntry(entry)"
                    >
                      {{ ui.deleteVocabulary }}
                    </button>
                  </div>
                </div>
              </article>
            </div>
          </div>
          <div v-else class="vocab-empty">{{ ui.vocabEmpty }}</div>
        </div>
      </section>

      <footer class="status-bar">
        <span class="connection-dot"></span>
        <span>{{ statusMessage || ui.ready }}</span>
        <span>OCR: {{ ui.ready }}</span>
        <span>{{ ui.translationService }}: {{ translator }}</span>
        <span class="push-end">{{ ui.versionLatest }}</span>
      </footer>
    </main>

    <section v-if="isSelectingArea" class="area-selector-backdrop">
      <div class="area-selector-dialog">
        <div class="area-selector-head">
          <strong>{{ ui.selectingArea }}</strong>
          <button class="small-action" type="button" @click="cancelCaptureAreaSelection">{{ ui.stop }}</button>
        </div>
        <div
          class="area-selector-frame"
          @pointerdown="beginCaptureAreaSelection"
          @pointermove="moveCaptureAreaSelection"
          @pointerup="finishCaptureAreaSelection"
          @pointercancel="cancelCaptureAreaSelection"
        >
          <img ref="selectionImageElement" :src="selectionImage" alt="Full game window preview" draggable="false" />
          <div
            v-if="selectionBox"
            class="area-selection-box"
            :style="{
              left: `${selectionBox.x * 100}%`,
              top: `${selectionBox.y * 100}%`,
              width: `${selectionBox.width * 100}%`,
              height: `${selectionBox.height * 100}%`
            }"
          ></div>
        </div>
        <span class="area-selector-hint">{{ ui.areaSelectorHint }}</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { buildOverlayGeometry, normalizeOverlayBounds } from "./overlay-state.js";

const messages = {
  en: {
    gameWindow: "Game window",
    refreshWindows: "Refresh",
    placeBeside: "Place beside",
    translationOutput: "Translation output",
    readingDirection: "Reading direction",
    customModel: "Custom model",
    translating: "Translating",
    start: "Start auto translate",
    retranslate: "Retranslate",
    stop: "Stop",
    collect: "Collect",
    copy: "Copy",
    leftOutput: "Source language",
    rightOutput: "Translation language",
    model: "Model",
    noWindowSelected: "Choose a visible game window",
    translator: "Translator",
    ocr: "OCR engine",
    vocabulary: "Vocabulary collection",
    refreshVocabulary: "Refresh",
    vocabSource: "Source",
    vocabTranslation: "Translation",
    vocabStatus: "Status",
    vocabMeta: "Meta",
    vocabEmpty: "No vocabulary collected yet.",
    backfillTranslation: "Translate",
    retranslateVocabulary: "Retranslate",
    deleteVocabulary: "Delete",
    confirmDeleteVocabulary: "Delete this vocabulary entry?",
    vocabSearch: "Search source or translation",
    vocabAllKinds: "All types",
    vocabWords: "Words",
    vocabLines: "Lines",
    vocabAllStatuses: "All statuses",
    vocabStatusNew: "New",
    vocabStatusLearning: "Learning",
    vocabStatusMastered: "Mastered",
    vocabStatusIgnored: "Ignored",
    vocabShowing: "Showing",
    vocabPrev: "Prev",
    vocabNext: "Next",
    fontFamily: "Font",
    textStyle: "Text style",
    layoutMode: "Layout mode",
    systemLanguage: "UI language",
    lockCurrentLine: "Lock current line",
    intervalMs: "Interval ms",
    context: "Context",
    stableReads: "Stable reads",
    apiUrl: "API URL",
    apiKey: "API Key",
    libreUrl: "Libre URL",
    libreTarget: "Libre target",
    selectArea: "Custom area",
    subtitleArea: "Subtitle area",
    ocrEngine: "OCR engine",
    translationService: "Translation service",
    emptyTranslation: "Translation will appear here.",
    ready: "Ready",
    noSource: "No source text to translate.",
    noWindow: "Select or type a game window title first.",
    noSelection: "Select text in the source panel first.",
    collected: "Collected to vocabulary.",
    copied: "Copied.",
    stopped: "Stopped",
    watching: "Watching subtitle area...",
    noNewText: "No new subtitle text.",
    gameWindowClosed: "Game window closed. Auto translation stopped.",
    previewWindowMissing: "Selected game window is not visible. Window list refreshed.",
    refreshing: "Refreshing windows...",
    windowsLoaded: "Window list refreshed.",
    selectingArea: "Drag over the game subtitle area...",
    areaSelectorHint: "Drag on the screenshot to select the subtitle area.",
    areaUpdated: "Capture area updated.",
    refreshPreview: "Refresh preview",
    previewing: "Capturing...",
    noPreview: "No preview yet",
    logs: "Run logs",
    settingsLoaded: "Local settings loaded.",
    settingsSaved: "Local settings saved.",
    placeHint: "Use the native window controls to place this beside the game.",
    versionLatest: "Current version is latest",
    titleWorking: "Translating...",
    showOverlay: "Show translation overlay",
    hideOverlay: "Hide translation overlay",
    overlayDecrease: "Decrease overlay size",
    overlayIncrease: "Increase overlay size",
    overlayClose: "Hide overlay"
  },
  "zh-CN": {
    gameWindow: "游戏窗口",
    refreshWindows: "刷新",
    placeBeside: "置于旁边",
    translationOutput: "翻译输出",
    readingDirection: "阅读方向",
    customModel: "自定义模型",
    translating: "翻译中",
    start: "开始自动翻译",
    retranslate: "重新翻译",
    stop: "停止",
    collect: "收集",
    copy: "复制",
    leftOutput: "原文语言",
    rightOutput: "翻译语言",
    model: "模型",
    noWindowSelected: "选择可见游戏窗口",
    translator: "翻译器",
    ocr: "OCR 引擎",
    vocabulary: "词汇收集",
    refreshVocabulary: "刷新",
    vocabSource: "原文",
    vocabTranslation: "翻译",
    vocabStatus: "状态",
    vocabMeta: "信息",
    vocabEmpty: "暂无收集词汇。",
    backfillTranslation: "补译",
    retranslateVocabulary: "重新翻译",
    deleteVocabulary: "删除",
    confirmDeleteVocabulary: "确认删除这条词汇？",
    vocabSearch: "搜索原文或翻译",
    vocabAllKinds: "全部类型",
    vocabWords: "单词",
    vocabLines: "句子",
    vocabAllStatuses: "全部状态",
    vocabStatusNew: "新收集",
    vocabStatusLearning: "学习中",
    vocabStatusMastered: "已掌握",
    vocabStatusIgnored: "忽略",
    vocabShowing: "显示",
    vocabPrev: "上一页",
    vocabNext: "下一页",
    fontFamily: "字体",
    textStyle: "文字",
    layoutMode: "布局模式",
    systemLanguage: "界面语言",
    lockCurrentLine: "锁定当前行",
    intervalMs: "间隔 ms",
    context: "上下文",
    stableReads: "稳定读取",
    apiUrl: "API 地址",
    apiKey: "API Key",
    libreUrl: "Libre 地址",
    libreTarget: "Libre 目标",
    selectArea: "自定义区域",
    subtitleArea: "字幕区域",
    ocrEngine: "OCR 引擎",
    translationService: "翻译服务",
    emptyTranslation: "翻译会显示在这里。",
    ready: "就绪",
    noSource: "没有可翻译的原文。",
    noWindow: "请先选择或输入游戏窗口标题。",
    noSelection: "请先在原文区域选中文本。",
    collected: "已收藏到词汇本。",
    copied: "已复制。",
    stopped: "已停止",
    watching: "正在监听字幕区域...",
    noNewText: "暂无新字幕。",
    gameWindowClosed: "游戏窗口已关闭，已自动停止翻译。",
    previewWindowMissing: "所选游戏窗口不可见，已刷新窗口列表。",
    refreshing: "正在刷新窗口...",
    windowsLoaded: "窗口列表已刷新。",
    selectingArea: "请在游戏字幕区域拖拽选区...",
    areaSelectorHint: "请在游戏截图上拖拽选择字幕区域。",
    areaUpdated: "捕获区域已更新。",
    refreshPreview: "刷新预览",
    previewing: "截图中...",
    noPreview: "暂无预览",
    logs: "运行日志",
    settingsLoaded: "已加载本地配置。",
    settingsSaved: "已保存本地配置。",
    placeHint: "请使用系统窗口功能将本窗口放到游戏旁边。",
    versionLatest: "当前版本最新",
    titleWorking: "正在翻译...",
    showOverlay: "显示翻译小窗",
    hideOverlay: "隐藏翻译小窗",
    overlayDecrease: "缩小小窗",
    overlayIncrease: "放大小窗",
    overlayClose: "隐藏小窗"
  }
};

const providerModels = {
  deepseek: ["deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
  grok: ["grok-4", "grok-3", "grok-3-mini"],
  openai: ["gpt-5-mini", "gpt-5", "gpt-4.1-mini", "gpt-4.1"],
  libretranslate: ["local-libretranslate"],
  argos: ["local-argos"]
};

const showProviderPanel = ref(false);
const showDisplayPanel = ref(false);
const showVocabularyPanel = ref(false);
const showLogPanel = ref(true);
const overlayVisible = ref(false);
const overlayX = ref(null);
const overlayY = ref(null);
const overlayWidth = ref(0);
const overlayHeight = ref(0);
const overlayCaptureVisible = ref(false);
const windowTitle = ref("");
const selectedWindowHwnd = ref(0);
const selectedWindowLabel = ref("");
const windowOptions = ref([]);
const leftOutput = ref("English");
const rightOutput = ref("Simplified Chinese");
const layout = ref("horizontal");
const model = ref("deepseek-v4-flash");
const customModel = ref("");
const translator = ref("deepseek");
const ocrEngine = ref("tesseract");
const fontSize = ref("20");
const fontFamily = ref("Microsoft YaHei UI");
const systemLanguage = ref("zh-CN");
const lockCurrentLine = ref(false);
const intervalMs = ref("1500");
const contextLines = ref("6");
const stableReads = ref("3");
const apiUrl = ref("https://api.deepseek.com");
const apiKey = ref("");
const libreUrl = ref("http://127.0.0.1:5000");
const libreTarget = ref("zh-Hans");
const cropLeft = ref("0.05");
const cropTop = ref("0.62");
const cropRight = ref("0.95");
const cropBottom = ref("0.95");
const sourceText = ref("Select a game window, then click Start translation.");
const translatedText = ref("");
const previewImage = ref("");
const isPreviewing = ref(false);
const isTranslating = ref(false);
const statusMessage = ref("");
const titleDots = ref(0);
const collectedCount = ref(0);
const vocabularyEntries = ref([]);
const vocabularySearch = ref("");
const vocabularyKindFilter = ref("all");
const vocabularyStatusFilter = ref("all");
const vocabularyPage = ref(1);
const vocabularyPageSize = ref("12");
const isBackfillingVocabulary = ref(false);
const isDeletingVocabulary = ref(false);
const sourceTextarea = ref(null);
const isSelectingArea = ref(false);
const selectionImage = ref("");
const selectionImageElement = ref(null);
const selectionBox = ref(null);
const logEntries = ref([]);

let titleTimer = null;
let logId = 0;
let settingsSaveTimer = null;
let settingsReady = false;
let applyingSettings = false;
let autoTranslateToken = 0;
let autoTranslateTimer = null;
let lastAutoSourceText = "";
let pendingOcrText = "";
let pendingOcrCount = 0;
let overlayUnlisteners = [];
let captureAreaSelectionStart = null;
let captureAreaSelectionResume = null;

const ui = computed(() => messages[systemLanguage.value] || messages.en);
const overlayCaptureLabel = computed(() =>
  systemLanguage.value === "zh-CN" ? "允许截图/串流" : "Show in capture"
);
const overlayCaptureHint = computed(() =>
  systemLanguage.value === "zh-CN"
    ? "允许截图、录屏、OBS 和串流软件捕获字幕。请将字幕放在 OCR 区域之外，避免重复识别。"
    : "Allow screenshots, recording, OBS, and streaming software to capture the overlay. Keep it outside the OCR area to avoid repeated recognition."
);
const overlayResetLabel = computed(() =>
  systemLanguage.value === "zh-CN" ? "重置小窗位置" : "Reset overlay"
);
const modelOptions = computed(() => providerModels[translator.value] || providerModels.deepseek);
const titleHint = computed(() => `${ui.value.titleWorking}${".".repeat(titleDots.value + 1)}`);
const vocabularyHint = computed(() => `${collectedCount.value} item(s) collected.`);
const vocabularyStatusOptions = computed(() => [
  { value: "new", label: ui.value.vocabStatusNew },
  { value: "learning", label: ui.value.vocabStatusLearning },
  { value: "mastered", label: ui.value.vocabStatusMastered },
  { value: "ignored", label: ui.value.vocabStatusIgnored }
]);
const vocabularyRows = computed(() =>
  vocabularyEntries.value.map((entry, index) => ({
    id: `${entry.created_at || entry.createdAt || index}-${index}`,
    source: String(entry.source || ""),
    translation: String(entry.translation || ""),
    sourceContext: String(entry.source_context || entry.sourceContext || ""),
    sourceLanguage: String(entry.source_language || entry.sourceLanguage || ""),
    targetLanguage: String(entry.target_language || entry.targetLanguage || ""),
    windowTitle: String(entry.window_title || entry.windowTitle || ""),
    kind: String(entry.kind || "word"),
    status: String(entry.status || "new"),
    createdAtRaw: String(entry.created_at || entry.createdAt || ""),
    createdAt: formatVocabularyTime(entry.created_at || entry.createdAt || "")
  }))
);
const filteredVocabularyRows = computed(() => {
  const query = vocabularySearch.value.trim().toLowerCase();
  return vocabularyRows.value.filter((entry) => {
    const matchesQuery =
      !query ||
      entry.source.toLowerCase().includes(query) ||
      entry.translation.toLowerCase().includes(query) ||
      entry.windowTitle.toLowerCase().includes(query);
    const matchesKind = vocabularyKindFilter.value === "all" || entry.kind === vocabularyKindFilter.value;
    const matchesStatus = vocabularyStatusFilter.value === "all" || entry.status === vocabularyStatusFilter.value;
    return matchesQuery && matchesKind && matchesStatus;
  });
});
const vocabularyPageCount = computed(() =>
  Math.max(Math.ceil(filteredVocabularyRows.value.length / (Number.parseInt(vocabularyPageSize.value, 10) || 12)), 1)
);
const pagedVocabularyRows = computed(() => {
  const size = Number.parseInt(vocabularyPageSize.value, 10) || 12;
  const safePage = Math.min(Math.max(vocabularyPage.value, 1), vocabularyPageCount.value);
  const start = (safePage - 1) * size;
  return filteredVocabularyRows.value.slice(start, start + size);
});
const panelFontStyle = computed(() => ({
  fontFamily: fontFamily.value,
  fontSize: `${Number.parseInt(fontSize.value, 10) || 20}px`
}));
const selectedWindow = computed(() =>
  windowOptions.value.find((item) => Number(item.hwnd) === Number(selectedWindowHwnd.value)) || null
);

watch(isTranslating, (active) => {
  document.title = active ? `(${titleHint.value}) 天楽 Galgame 翻译器` : "天楽 Galgame 翻译器";
});

watch(titleDots, () => {
  if (isTranslating.value) {
    document.title = `(${titleHint.value}) 天楽 Galgame 翻译器`;
  }
});

watch(overlayCaptureVisible, (active) => {
  if (!active || applyingSettings) {
    return;
  }
  const warning = systemLanguage.value === "zh-CN"
    ? "串流捕获已开启：请将翻译字幕移出 OCR 选区，避免字幕被重复识别。"
    : "Stream capture is enabled. Keep the overlay outside the OCR area to avoid repeated recognition.";
  statusMessage.value = warning;
  addLog("warn", warning);
});

watch(translator, (provider) => {
  if (applyingSettings) {
    return;
  }
  const options = providerModels[provider] || providerModels.deepseek;
  if (!options.includes(model.value) && model.value !== "__custom__") {
    model.value = options[0];
  }
  if (provider === "deepseek") {
    apiUrl.value = "https://api.deepseek.com";
  } else if (provider === "grok") {
    apiUrl.value = "https://api.x.ai/v1";
  } else if (provider === "openai") {
    apiUrl.value = "https://api.openai.com/v1";
  }
});

watch(
  [
    windowTitle,
    selectedWindowHwnd,
    selectedWindowLabel,
    leftOutput,
    rightOutput,
    layout,
    model,
    customModel,
    translator,
    ocrEngine,
    fontSize,
    fontFamily,
    systemLanguage,
    lockCurrentLine,
    intervalMs,
    contextLines,
    stableReads,
    apiUrl,
    apiKey,
    libreUrl,
    libreTarget,
    cropLeft,
    cropTop,
    cropRight,
    cropBottom,
    overlayCaptureVisible,
    overlayX,
    overlayY,
    overlayWidth,
    overlayHeight
  ],
  scheduleSettingsSave
);

watch([vocabularySearch, vocabularyKindFilter, vocabularyStatusFilter, vocabularyPageSize], () => {
  vocabularyPage.value = 1;
});

watch(vocabularyPageCount, (count) => {
  if (vocabularyPage.value > count) {
    vocabularyPage.value = count;
  }
});

onMounted(async () => {
  listen("overlay-bounds-changed", (event) => {
    const bounds = normalizeOverlayBounds(event.payload);
    overlayX.value = bounds.x;
    overlayY.value = bounds.y;
    overlayWidth.value = bounds.width || overlayWidth.value;
    overlayHeight.value = bounds.height || overlayHeight.value;
  }).then((unlisten) => {
    overlayUnlisteners.push(unlisten);
  });
  listen("overlay-hidden", () => {
    overlayVisible.value = false;
  }).then((unlisten) => {
    overlayUnlisteners.push(unlisten);
  });
  listen("overlay-maintenance-error", (event) => {
    addLog("warn", `Overlay maintenance: ${String(event.payload || "unknown error")}`);
  }).then((unlisten) => {
    overlayUnlisteners.push(unlisten);
  });
  titleTimer = window.setInterval(() => {
    titleDots.value = (titleDots.value + 1) % 3;
  }, 450);
  await bootApp();
});

onUnmounted(() => {
  overlayUnlisteners.forEach((unlisten) => unlisten());
  if (titleTimer) {
    window.clearInterval(titleTimer);
  }
  if (settingsSaveTimer) {
    window.clearTimeout(settingsSaveTimer);
  }
  stopAutoTranslateLoop();
});

function addLog(level, message) {
  const now = new Date();
  logEntries.value.unshift({
    id: ++logId,
    level,
    time: now.toLocaleTimeString(),
    message
  });
  if (logEntries.value.length > 80) {
    logEntries.value.length = 80;
  }
}

function safeApiKey() {
  return apiKey.value.trim();
}

function settingsSnapshot() {
  return {
    windowTitle: windowTitle.value,
    selectedWindowHwnd: selectedWindowHwnd.value,
    selectedWindowLabel: selectedWindowLabel.value,
    leftOutput: leftOutput.value,
    rightOutput: rightOutput.value,
    layout: layout.value,
    model: model.value,
    customModel: customModel.value,
    translator: translator.value,
    ocrEngine: ocrEngine.value,
    fontSize: fontSize.value,
    fontFamily: fontFamily.value,
    systemLanguage: systemLanguage.value,
    lockCurrentLine: lockCurrentLine.value,
    intervalMs: intervalMs.value,
    contextLines: contextLines.value,
    stableReads: stableReads.value,
    apiUrl: apiUrl.value,
    apiKey: apiKey.value,
    libreUrl: libreUrl.value,
    libreTarget: libreTarget.value,
    cropLeft: cropLeft.value,
    cropTop: cropTop.value,
    cropRight: cropRight.value,
    cropBottom: cropBottom.value,
    overlayCaptureVisible: overlayCaptureVisible.value,
    overlayX: overlayX.value,
    overlayY: overlayY.value,
    overlayWidth: overlayWidth.value,
    overlayHeight: overlayHeight.value
  };
}

function applySettings(settings) {
  if (!settings || typeof settings !== "object") {
    return;
  }
  applyingSettings = true;
  const assignString = (key, target) => {
    if (typeof settings[key] === "string") {
      target.value = settings[key];
    }
  };
  assignString("windowTitle", windowTitle);
  assignString("selectedWindowLabel", selectedWindowLabel);
  if (Number.isFinite(Number(settings.selectedWindowHwnd))) {
    selectedWindowHwnd.value = Number(settings.selectedWindowHwnd);
  }
  assignString("leftOutput", leftOutput);
  assignString("rightOutput", rightOutput);
  assignString("layout", layout);
  assignString("model", model);
  assignString("customModel", customModel);
  assignString("translator", translator);
  assignString("ocrEngine", ocrEngine);
  assignString("fontSize", fontSize);
  assignString("fontFamily", fontFamily);
  assignString("systemLanguage", systemLanguage);
  assignString("intervalMs", intervalMs);
  assignString("contextLines", contextLines);
  assignString("stableReads", stableReads);
  assignString("apiUrl", apiUrl);
  assignString("apiKey", apiKey);
  assignString("libreUrl", libreUrl);
  assignString("libreTarget", libreTarget);
  assignString("cropLeft", cropLeft);
  assignString("cropTop", cropTop);
  assignString("cropRight", cropRight);
  assignString("cropBottom", cropBottom);
  if (typeof settings.lockCurrentLine === "boolean") {
    lockCurrentLine.value = settings.lockCurrentLine;
  }
  if (typeof settings.overlayCaptureVisible === "boolean") {
    overlayCaptureVisible.value = settings.overlayCaptureVisible;
  }
  const savedOverlayBounds = normalizeOverlayBounds({
    x: settings.overlayX,
    y: settings.overlayY,
    width: settings.overlayWidth,
    height: settings.overlayHeight
  });
  overlayX.value = savedOverlayBounds.x;
  overlayY.value = savedOverlayBounds.y;
  overlayWidth.value = savedOverlayBounds.width || 0;
  overlayHeight.value = savedOverlayBounds.height || 0;
  window.setTimeout(() => {
    applyingSettings = false;
  }, 0);
}

async function bootApp() {
  addLog("info", "App mounted. Loading local settings.");
  try {
    const response = await invoke("load_settings_command");
    applySettings(response.settings || {});
    addLog("info", `${ui.value.settingsLoaded} path=${response.path || "unknown"}, apiKeyConfigured=${safeApiKey() ? "yes" : "no"}`);
  } catch (error) {
    addLog("warn", `Local settings could not be loaded: ${String(error || "unknown error")}`);
  } finally {
    settingsReady = true;
  }
  await refreshWindows();
  await refreshVocabularyCount();
  if (windowTitle.value.trim()) {
    refreshCapturePreview();
  }
}

async function saveSettingsNow() {
  if (!settingsReady) {
    return;
  }
  try {
    await invoke("save_settings_command", {
      request: {
        settings: settingsSnapshot()
      }
    });
  } catch (error) {
    addLog("warn", `Local settings could not be saved: ${String(error || "unknown error")}`);
  }
}

function scheduleSettingsSave() {
  if (!settingsReady) {
    return;
  }
  if (settingsSaveTimer) {
    window.clearTimeout(settingsSaveTimer);
  }
  settingsSaveTimer = window.setTimeout(() => {
    saveSettingsNow();
  }, 500);
}

function activeModel() {
  return model.value === "__custom__" ? customModel.value.trim() : model.value;
}

function targetLanguage() {
  return rightOutput.value === "Original OCR" ? "Simplified Chinese" : rightOutput.value;
}

function floatValue(value, fallback) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cropRequest() {
  return {
    left: floatValue(cropLeft.value, 0.05),
    top: floatValue(cropTop.value, 0.62),
    right: floatValue(cropRight.value, 0.95),
    bottom: floatValue(cropBottom.value, 0.95)
  };
}

function togglePlaceHint() {
  statusMessage.value = ui.value.placeHint;
  addLog("info", ui.value.placeHint);
}

function increaseFont() {
  fontSize.value = String((Number.parseInt(fontSize.value, 10) || 20) + 1);
}

function decreaseFont() {
  fontSize.value = String(Math.max((Number.parseInt(fontSize.value, 10) || 20) - 1, 10));
}

function formatVocabularyTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

async function toggleVocabularyPanel() {
  showVocabularyPanel.value = !showVocabularyPanel.value;
  if (showVocabularyPanel.value) {
    await refreshVocabularyCount();
  }
}

function baseRequest() {
  if (translator.value !== "libretranslate" && translator.value !== "argos" && !safeApiKey()) {
    addLog("warn", `API key is empty for ${translator.value}. Configure it once; it will be saved locally.`);
  }
  return {
    translator: translator.value,
    targetLanguage: targetLanguage(),
    model: activeModel(),
    apiUrl: apiUrl.value,
    apiKey: safeApiKey(),
    libreUrl: libreUrl.value,
    libreTarget: libreTarget.value
  };
}

async function withBusy(message, action) {
  isTranslating.value = true;
  statusMessage.value = message;
  try {
    await action();
  } catch (error) {
    const detail = String(error || "Operation failed");
    statusMessage.value = detail;
    addLog("error", detail);
  } finally {
    isTranslating.value = false;
  }
}

function intervalDelay() {
  const parsed = Number.parseInt(intervalMs.value, 10);
  return Number.isFinite(parsed) ? Math.max(parsed, 500) : 1500;
}

function stableReadCount() {
  const parsed = Number.parseInt(stableReads.value, 10);
  return Number.isFinite(parsed) ? Math.max(parsed, 1) : 3;
}

function canonicalOcrText(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

function ocrTextsAreSimilar(left, right) {
  const a = canonicalOcrText(left);
  const b = canonicalOcrText(right);
  if (!a || !b) {
    return false;
  }
  if (a.includes(b) || b.includes(a)) {
    const shorter = Math.min(a.length, b.length);
    const longer = Math.max(a.length, b.length);
    return shorter >= 10 && shorter / longer >= 0.55;
  }
  const maxLength = Math.max(a.length, b.length);
  let same = 0;
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    if (a[index] === b[index]) {
      same += 1;
    }
  }
  return same / maxLength >= 0.78;
}

function ocrQualityScore(text) {
  const words = (text.match(/[A-Za-z]{2,}/g) || []).length;
  const letters = (text.match(/[A-Za-z]/g) || []).length;
  const noise = (text.match(/[^A-Za-z0-9\s,.!?;:'"-]/g) || []).length;
  return words * 100 + letters - noise * 4 - Math.floor(text.length / 8);
}

function resetOcrStability() {
  pendingOcrText = "";
  pendingOcrCount = 0;
}

function acceptStableOcrText(text) {
  if (text === pendingOcrText || ocrTextsAreSimilar(text, pendingOcrText)) {
    pendingOcrCount += 1;
    if (ocrQualityScore(text) > ocrQualityScore(pendingOcrText)) {
      pendingOcrText = text;
    }
  } else {
    pendingOcrText = text;
    pendingOcrCount = 1;
  }
  return pendingOcrCount >= stableReadCount() ? pendingOcrText : "";
}

function stopAutoTranslateLoop() {
  autoTranslateToken += 1;
  if (autoTranslateTimer) {
    window.clearTimeout(autoTranslateTimer);
    autoTranslateTimer = null;
  }
}

function isWindowMissingError(error) {
  return String(error || "").toLowerCase().includes("window not found");
}

async function stopBecauseGameWindowClosed(error) {
  stopAutoTranslateLoop();
  isTranslating.value = false;
  if (overlayVisible.value) {
    await invoke("hide_translation_overlay_command").catch(() => {});
    overlayVisible.value = false;
  }
  resetOcrStability();
  statusMessage.value = ui.value.gameWindowClosed;
  selectedWindowHwnd.value = 0;
  selectedWindowLabel.value = "";
  addLog("warn", `${ui.value.gameWindowClosed} ${String(error || "").split("\n").at(-1) || ""}`.trim());
  await refreshWindows();
}

function scheduleNextAutoTranslate(token) {
  if (!isTranslating.value || token !== autoTranslateToken) {
    return;
  }
  autoTranslateTimer = window.setTimeout(() => {
    runAutoTranslateTick(token);
  }, intervalDelay());
}

function overlayRequest() {
  const crop = cropRequest();
  const geometry = buildOverlayGeometry({
    game: selectedWindow.value,
    crop,
    fontSize: fontSize.value,
    savedBounds: {
      x: overlayX.value,
      y: overlayY.value,
      width: overlayWidth.value,
      height: overlayHeight.value
    }
  });
  return {
    text: translatedText.value || "",
    language: rightOutput.value,
    fontFamily: fontFamily.value,
    fontSize: Math.max(Number.parseInt(fontSize.value, 10) || 20, 12),
    captureVisible: overlayCaptureVisible.value,
    ...geometry
  };
}

function invokeOverlayCommand(command, args = {}, timeoutMs = 1200) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`${command} timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    invoke(command, args).then(
      (result) => {
        window.clearTimeout(timer);
        resolve(result);
      },
      (error) => {
        window.clearTimeout(timer);
        reject(error);
      }
    );
  });
}

async function syncTranslationOverlay(ensureVisible = false) {
  if ((!ensureVisible && !overlayVisible.value) || !selectedWindow.value) {
    return false;
  }
  try {
    const command = ensureVisible
      ? "show_translation_overlay_command"
      : "update_translation_overlay_command";
    const request = overlayRequest();
    addLog("info", `Overlay command started: ${command}, textLength=${request.text.length}`);
    await invokeOverlayCommand(command, { request }, ensureVisible ? 3000 : 1200);
    addLog("info", `Overlay command finished: ${command}`);
    return true;
  } catch (error) {
    addLog("error", `Translation overlay failed: ${String(error || "unknown error")}`);
    return false;
  }
}

async function toggleTranslationOverlay() {
  if (overlayVisible.value) {
    addLog("info", "Overlay hide requested by main window.");
    await invokeOverlayCommand("hide_translation_overlay_command").catch((error) => {
      addLog("warn", `Overlay hide failed: ${String(error || "unknown error")}`);
    });
    overlayVisible.value = false;
    addLog("info", "Translation overlay hidden.");
    return;
  }
  if (!windowTitle.value.trim() || !selectedWindow.value) {
    statusMessage.value = ui.value.noWindow;
    addLog("warn", "Translation overlay blocked: no visible game window selected.");
    return;
  }
  const initialRequest = overlayRequest();
  overlayWidth.value = initialRequest.width;
  overlayHeight.value = initialRequest.height;
  addLog("info", `Overlay show requested. position=${initialRequest.x},${initialRequest.y}, size=${initialRequest.width}x${initialRequest.height}`);
  const overlayShown = await syncTranslationOverlay(true);
  if (!overlayShown) {
    statusMessage.value = "Translation overlay could not be opened. Check run logs.";
    return;
  }
  overlayVisible.value = true;
  addLog("info", "Translation overlay shown.");
}

async function resetOverlayPosition() {
  overlayX.value = null;
  overlayY.value = null;
  overlayWidth.value = 0;
  overlayHeight.value = 0;
  if (overlayVisible.value) {
    await syncTranslationOverlay(true);
  }
  addLog("info", "Overlay position reset to the selected game window.");
}

watch([translatedText, rightOutput, fontFamily, fontSize, overlayCaptureVisible], () => {
  syncTranslationOverlay();
});

async function runAutoTranslateTick(token) {
  if (!isTranslating.value || token !== autoTranslateToken) {
    return;
  }

  const crop = cropRequest();
  try {
    addLog("info", `Auto tick: OCR request started. crop=${JSON.stringify(crop)}`);
    const ocrResponse = await invoke("ocr_text_command", {
      request: {
        windowTitle: windowTitle.value.trim(),
        hwnd: selectedWindowHwnd.value,
        ocrEngine: ocrEngine.value,
        model: activeModel(),
        apiUrl: apiUrl.value,
        apiKey: safeApiKey(),
        ...crop
      }
    });
    addLog("info", `Auto tick: OCR request finished. sourceLength=${(ocrResponse.source || "").length}`);
    if (!isTranslating.value || token !== autoTranslateToken) {
      return;
    }

    const nextSource = (ocrResponse.source || "").trim();
    if (!nextSource) {
      resetOcrStability();
      statusMessage.value = "OCR returned empty text. Check preview area or OCR engine.";
      addLog("warn", "Auto tick: OCR returned empty source text.");
    } else if (ocrTextsAreSimilar(nextSource, lastAutoSourceText)) {
      statusMessage.value = ui.value.noNewText;
      addLog("info", "Auto tick: same subtitle text, waiting.");
    } else {
      const stableSource = acceptStableOcrText(nextSource);
      if (!stableSource) {
        statusMessage.value = `Waiting for stable OCR (${pendingOcrCount}/${stableReadCount()}).`;
        addLog("info", `Auto tick: waiting for stable OCR (${pendingOcrCount}/${stableReadCount()}).`);
        return;
      }
      const translateResponse = await invoke("translate_text_command", {
        request: {
          ...baseRequest(),
          text: stableSource
        }
      });
      lastAutoSourceText = stableSource;
      sourceText.value = stableSource;
      const nextTranslation = translateResponse.translation || "";
      translatedText.value = nextTranslation;
      statusMessage.value = nextTranslation ? ui.value.watching : "Translation returned empty text. Check API key/model/provider settings.";
      addLog("info", `Auto tick translated. sourceLength=${stableSource.length}, translationLength=${nextTranslation.length}`);
    }
  } catch (error) {
    if (isWindowMissingError(error)) {
      await stopBecauseGameWindowClosed(error);
      return;
    }
    const detail = String(error || "Auto translation failed");
    statusMessage.value = detail;
    addLog("error", `Auto tick failed: ${detail}`);
  } finally {
    scheduleNextAutoTranslate(token);
  }
}

async function refreshWindows() {
  statusMessage.value = ui.value.refreshing;
  addLog("info", "Requesting visible window list.");
  try {
    const response = await invoke("list_windows_command");
    windowOptions.value = response.windows || [];
    restoreSelectedWindow();
    statusMessage.value = ui.value.windowsLoaded;
    addLog("info", `Window list refreshed: ${windowOptions.value.length} windows found.`);
  } catch (error) {
    const detail = String(error || "Failed to refresh windows");
    statusMessage.value = detail;
    addLog("error", detail);
  }
}

function applySelectedWindow() {
  const selected = windowOptions.value.find((item) => item.label === selectedWindowLabel.value);
  if (selected) {
    windowTitle.value = selected.title;
    selectedWindowHwnd.value = Number(selected.hwnd) || 0;
    addLog("info", `Selected window: ${selected.label}`);
    refreshCapturePreview();
  }
}

function restoreSelectedWindow() {
  if (!windowOptions.value.length) {
    return;
  }
  const savedHwnd = Number(selectedWindowHwnd.value) || 0;
  const savedTitle = windowTitle.value.trim().toLowerCase();
  const matched =
    windowOptions.value.find((item) => Number(item.hwnd) === savedHwnd) ||
    windowOptions.value.find((item) => savedTitle && item.title.toLowerCase().includes(savedTitle)) ||
    windowOptions.value.find((item) => savedTitle && savedTitle.includes(item.title.toLowerCase()));
  if (matched) {
    selectedWindowLabel.value = matched.label;
    windowTitle.value = matched.title;
    selectedWindowHwnd.value = Number(matched.hwnd) || 0;
    addLog("info", `Restored window selection: ${matched.label}`);
  }
}

async function refreshCapturePreview() {
  if (!windowTitle.value.trim()) {
    addLog("warn", "Preview skipped: no game window selected.");
    return;
  }

  isPreviewing.value = true;
  const crop = cropRequest();
  addLog("info", `Capturing preview: ${JSON.stringify(crop)}`);
  try {
    const response = await invoke("preview_area_command", {
      request: {
        windowTitle: windowTitle.value.trim(),
        hwnd: selectedWindowHwnd.value,
        ...crop
      }
    });
    previewImage.value = response.data_url || "";
    addLog("info", `Preview captured: ${response.width}x${response.height} from window ${response.window_width || "?"}x${response.window_height || "?"}.`);
  } catch (error) {
    if (isWindowMissingError(error)) {
      previewImage.value = "";
      selectedWindowHwnd.value = 0;
      selectedWindowLabel.value = "";
      statusMessage.value = ui.value.previewWindowMissing;
      addLog("warn", ui.value.previewWindowMissing);
      await refreshWindows();
      return;
    }
    addLog("error", `Preview failed: ${String(error || "unknown error")}`);
  } finally {
    isPreviewing.value = false;
  }
}

async function startOcrTranslation() {
  if (!windowTitle.value.trim()) {
    statusMessage.value = ui.value.noWindow;
    addLog("warn", "Start blocked: no game window selected.");
    return;
  }

  const crop = cropRequest();
  stopAutoTranslateLoop();
  isTranslating.value = true;
  lastAutoSourceText = "";
  resetOcrStability();
  const token = autoTranslateToken;
  statusMessage.value = ui.value.watching;
  addLog("info", `Start auto OCR translation. window="${windowTitle.value}", ocr=${ocrEngine.value}, translator=${translator.value}, target=${targetLanguage()}, interval=${intervalDelay()}ms, crop=${JSON.stringify(crop)}`);
  await refreshCapturePreview();
  runAutoTranslateTick(token);
}

async function selectCaptureArea() {
  if (!windowTitle.value.trim()) {
    statusMessage.value = ui.value.noWindow;
    addLog("warn", "Area selection blocked: no game window selected.");
    return;
  }

  statusMessage.value = ui.value.selectingArea;
  addLog("info", "Opening draggable capture-area selector.");
  const wasTranslating = isTranslating.value;
  const wasOverlayVisible = overlayVisible.value;
  if (wasTranslating) {
    stopAutoTranslateLoop();
    isTranslating.value = false;
  }
  if (wasOverlayVisible) {
    await invoke("hide_translation_overlay_command").catch(() => {});
    overlayVisible.value = false;
  }
  captureAreaSelectionResume = { wasTranslating, wasOverlayVisible };
  try {
    const response = await invoke("preview_area_command", {
      request: {
        windowTitle: windowTitle.value.trim(),
        hwnd: selectedWindowHwnd.value,
        left: 0,
        top: 0,
        right: 1,
        bottom: 1
      }
    });
    selectionImage.value = response.data_url || "";
    selectionBox.value = null;
    captureAreaSelectionStart = null;
    isSelectingArea.value = Boolean(selectionImage.value);
    if (!isSelectingArea.value) {
      throw new Error("Full game window preview returned empty image.");
    }
    addLog("info", `Capture-area image loaded: ${response.width}x${response.height}.`);
  } catch (error) {
    const detail = String(error || "Failed to select area");
    statusMessage.value = detail;
    addLog("error", detail);
    await restoreAfterCaptureAreaSelection();
  }
}

function selectionPoint(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  return {
    x: Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1),
    y: Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1)
  };
}

function beginCaptureAreaSelection(event) {
  event.currentTarget.setPointerCapture?.(event.pointerId);
  captureAreaSelectionStart = selectionPoint(event);
  selectionBox.value = { ...captureAreaSelectionStart, width: 0, height: 0 };
}

function moveCaptureAreaSelection(event) {
  if (!captureAreaSelectionStart) {
    return;
  }
  const current = selectionPoint(event);
  selectionBox.value = {
    x: Math.min(captureAreaSelectionStart.x, current.x),
    y: Math.min(captureAreaSelectionStart.y, current.y),
    width: Math.abs(current.x - captureAreaSelectionStart.x),
    height: Math.abs(current.y - captureAreaSelectionStart.y)
  };
}

async function finishCaptureAreaSelection(event) {
  if (!captureAreaSelectionStart) {
    return;
  }
  moveCaptureAreaSelection(event);
  const box = selectionBox.value;
  captureAreaSelectionStart = null;
  if (!box || box.width < 0.01 || box.height < 0.01) {
    await cancelCaptureAreaSelection();
    return;
  }
  cropLeft.value = String(box.x);
  cropTop.value = String(box.y);
  cropRight.value = String(box.x + box.width);
  cropBottom.value = String(box.y + box.height);
  isSelectingArea.value = false;
  selectionImage.value = "";
  selectionBox.value = null;
  statusMessage.value = ui.value.areaUpdated;
  addLog("info", `Capture area updated: left=${cropLeft.value}, top=${cropTop.value}, right=${cropRight.value}, bottom=${cropBottom.value}`);
  await refreshCapturePreview();
  await restoreAfterCaptureAreaSelection();
}

async function cancelCaptureAreaSelection() {
  captureAreaSelectionStart = null;
  isSelectingArea.value = false;
  selectionImage.value = "";
  selectionBox.value = null;
  statusMessage.value = ui.value.stopped;
  addLog("warn", "Area selection cancelled.");
  await restoreAfterCaptureAreaSelection();
}

async function restoreAfterCaptureAreaSelection() {
  const resume = captureAreaSelectionResume;
  captureAreaSelectionResume = null;
  if (!resume) {
    return;
  }
  if (resume.wasOverlayVisible) {
    overlayVisible.value = true;
    await syncTranslationOverlay(true);
  }
  if (resume.wasTranslating) {
    await startOcrTranslation();
  }
}

async function runTextTranslation() {
  const text = sourceText.value.trim();
  if (!text) {
    statusMessage.value = ui.value.noSource;
    addLog("warn", "Manual translation blocked: no source text.");
    return;
  }

  addLog("info", `Manual translation started. sourceLength=${text.length}, translator=${translator.value}, target=${targetLanguage()}`);
  await withBusy(ui.value.titleWorking, async () => {
    const response = await invoke("translate_text_command", {
      request: {
        ...baseRequest(),
        text
      }
    });
    sourceText.value = response.source || text;
    translatedText.value = response.translation || "";
    addLog("info", `Manual translation finished. translationLength=${(response.translation || "").length}`);
    statusMessage.value = ui.value.ready;
  });
}

function stopTranslation() {
  stopAutoTranslateLoop();
  isTranslating.value = false;
  if (overlayVisible.value) {
    invoke("hide_translation_overlay_command").catch(() => {});
    overlayVisible.value = false;
  }
  statusMessage.value = ui.value.stopped;
  addLog("warn", "Stop requested.");
}

async function copyTranslation() {
  try {
    await navigator.clipboard.writeText(translatedText.value || "");
    statusMessage.value = ui.value.copied;
    addLog("info", "Translation copied to clipboard.");
  } catch {
    statusMessage.value = translatedText.value || "";
    addLog("error", "Clipboard write failed.");
  }
}

async function collectSelection() {
  const textarea = sourceTextarea.value;
  const selected = textarea
    ? textarea.value.slice(textarea.selectionStart || 0, textarea.selectionEnd || 0).trim()
    : "";
  if (!selected) {
    statusMessage.value = ui.value.noSelection;
    addLog("warn", "Collect selection blocked: no selected source text.");
    return;
  }
  const translation = await translateForVocabulary(selected, sourceText.value, translatedText.value);
  await collectEntry(selected, translation);
}

async function collectCurrent() {
  const source = sourceText.value.trim();
  if (!source) {
    statusMessage.value = ui.value.noSource;
    addLog("warn", "Collect current blocked: no source text.");
    return;
  }
  await collectEntry(source, translatedText.value.trim());
}

async function collectEntry(source, translation) {
  try {
    await invoke("collect_vocabulary_command", {
      request: {
        source,
        translation,
        sourceContext: sourceText.value.trim(),
        sourceLanguage: leftOutput.value,
        targetLanguage: rightOutput.value,
        windowTitle: windowTitle.value,
        kind: source.includes("\n") || source.length > 32 ? "line" : "word",
        note: "",
        tags: "tauri"
      }
    });
    await refreshVocabularyCount();
    statusMessage.value = ui.value.collected;
    addLog("info", `Vocabulary collected. total=${collectedCount.value}`);
  } catch (error) {
    const detail = String(error || "Failed to collect vocabulary");
    statusMessage.value = detail;
    addLog("error", detail);
  }
}

function vocabularyTranslationPrompt(source, sourceContext = "", translatedContext = "") {
  const term = source.trim();
  const context = sourceContext.trim();
  const translated = translatedContext.trim();
  if (!context || context === term) {
    return term;
  }
  return [
    "Translate the selected vocabulary item according to its meaning in the visual novel line.",
    "Return only the vocabulary translation, not the full sentence.",
    "",
    `Selected item: ${term}`,
    `Original line: ${context}`,
    translated ? `Existing line translation: ${translated}` : ""
  ]
    .filter(Boolean)
    .join("\n");
}

async function translateForVocabulary(source, sourceContext = "", translatedContext = "") {
  const text = source.trim();
  if (!text) {
    return "";
  }
  try {
    const response = await invoke("translate_text_command", {
      request: {
        ...baseRequest(),
        text: vocabularyTranslationPrompt(text, sourceContext, translatedContext)
      }
    });
    return response.translation || "";
  } catch (error) {
    addLog("warn", `Vocabulary translation failed: ${String(error || "unknown error")}`);
    return "";
  }
}

async function retranslateVocabularyEntry(entry) {
  if (!entry.source || !entry.createdAtRaw) {
    return;
  }
  isBackfillingVocabulary.value = true;
  try {
    const translation = await translateForVocabulary(entry.source, entry.sourceContext || sourceText.value, translatedText.value);
    if (!translation) {
      statusMessage.value = "Vocabulary translation returned empty text.";
      return;
    }
    await invoke("update_vocabulary_command", {
      request: {
        createdAt: entry.createdAtRaw,
        source: entry.source,
        translation,
        status: entry.status
      }
    });
    await refreshVocabularyCount();
    statusMessage.value = ui.value.collected;
    addLog("info", `Vocabulary retranslated: ${entry.source}`);
  } catch (error) {
    const detail = String(error || "Failed to update vocabulary");
    statusMessage.value = detail;
    addLog("error", detail);
  } finally {
    isBackfillingVocabulary.value = false;
  }
}

async function updateVocabularyStatus(entry, status) {
  if (!entry.source || !entry.createdAtRaw) {
    return;
  }
  try {
    await invoke("update_vocabulary_command", {
      request: {
        createdAt: entry.createdAtRaw,
        source: entry.source,
        translation: entry.translation,
        status
      }
    });
    await refreshVocabularyCount();
    addLog("info", `Vocabulary status updated: ${entry.source} -> ${status}`);
  } catch (error) {
    const detail = String(error || "Failed to update vocabulary status");
    statusMessage.value = detail;
    addLog("error", detail);
  }
}

async function deleteVocabularyEntry(entry) {
  if (!entry.source || !entry.createdAtRaw) {
    return;
  }
  if (!window.confirm(ui.value.confirmDeleteVocabulary)) {
    return;
  }
  isDeletingVocabulary.value = true;
  try {
    await invoke("delete_vocabulary_command", {
      request: {
        createdAt: entry.createdAtRaw,
        source: entry.source
      }
    });
    await refreshVocabularyCount();
    statusMessage.value = ui.value.ready;
    addLog("info", `Vocabulary deleted: ${entry.source}`);
  } catch (error) {
    const detail = String(error || "Failed to delete vocabulary");
    statusMessage.value = detail;
    addLog("error", detail);
  } finally {
    isDeletingVocabulary.value = false;
  }
}

async function refreshVocabularyCount() {
  try {
    const response = await invoke("list_vocabulary_command");
    vocabularyEntries.value = Array.isArray(response.entries) ? response.entries.slice().reverse() : [];
    collectedCount.value = Number(response.count) || 0;
    addLog("info", `Vocabulary loaded. total=${collectedCount.value}`);
  } catch (error) {
    addLog("warn", `Vocabulary count could not be loaded: ${String(error || "unknown error")}`);
  }
}
</script>
