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
          <div class="crop-preview">
            <div class="crop-box"></div>
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

      <section class="vocab-drawer">
        <button class="vocab-toggle" type="button" @click="showVocabularyPanel = !showVocabularyPanel">
          <span>▰</span>
          {{ ui.vocabulary }} ({{ collectedCount }})
          <span class="chevron">{{ showVocabularyPanel ? "⌃" : "⌄" }}</span>
        </button>
        <div v-if="showVocabularyPanel" class="vocab-body">{{ vocabularyHint }}</div>
      </section>

      <footer class="status-bar">
        <span class="connection-dot"></span>
        <span>{{ statusMessage || ui.ready }}</span>
        <span>OCR: {{ ui.ready }}</span>
        <span>{{ ui.translationService }}: {{ translator }}</span>
        <span class="push-end">{{ ui.versionLatest }}</span>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";

const messages = {
  en: {
    gameWindow: "Game window",
    refreshWindows: "Refresh",
    placeBeside: "Place beside",
    translationOutput: "Translation output",
    readingDirection: "Reading direction",
    layoutVertical: "Top / Bottom",
    layoutHorizontal: "Left / Right",
    customModel: "Custom model",
    translating: "Translating",
    start: "Start translation",
    retranslate: "Retranslate",
    stop: "Stop",
    collect: "Collect",
    copy: "Copy",
    leftOutput: "Source language",
    rightOutput: "Translation language",
    layout: "Layout",
    model: "Model",
    noWindowSelected: "Choose a visible game window",
    translator: "Translator",
    ocr: "OCR engine",
    providerConfigs: "Service config",
    vocabulary: "Vocabulary collection",
    fontSize: "Font size",
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
    refreshing: "Refreshing windows...",
    windowsLoaded: "Window list refreshed.",
    selectingArea: "Drag over the game subtitle area...",
    areaUpdated: "Capture area updated.",
    placeHint: "Use the native window controls to place this beside the game.",
    versionLatest: "Current version is latest",
    titleWorking: "Translating..."
  },
  "zh-CN": {
    gameWindow: "游戏窗口",
    refreshWindows: "刷新",
    placeBeside: "置于旁边",
    translationOutput: "翻译输出",
    readingDirection: "阅读方向",
    layoutVertical: "上下布局",
    layoutHorizontal: "左右布局",
    customModel: "自定义模型",
    translating: "翻译中",
    start: "开始翻译",
    retranslate: "重新翻译",
    stop: "停止",
    collect: "收集",
    copy: "复制",
    leftOutput: "原文语言",
    rightOutput: "翻译语言",
    layout: "布局",
    model: "模型",
    noWindowSelected: "选择可见游戏窗口",
    translator: "翻译器",
    ocr: "OCR 引擎",
    providerConfigs: "服务配置",
    vocabulary: "词汇收集",
    fontSize: "字号",
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
    refreshing: "正在刷新窗口...",
    windowsLoaded: "窗口列表已刷新。",
    selectingArea: "请在游戏字幕区域拖拽选区...",
    areaUpdated: "捕获区域已更新。",
    placeHint: "请使用系统窗口功能将本窗口放到游戏旁边。",
    versionLatest: "当前版本最新",
    titleWorking: "正在翻译..."
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
const windowTitle = ref("");
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
const sourceText = ref("「——それでも、\n君と出会えたことは、\n俺にとって、奇跡だった。」");
const translatedText = ref("「——即使如此，\n能够与你相遇，\n对我来说也是一种奇迹。」");
const isTranslating = ref(false);
const statusMessage = ref("");
const titleDots = ref(0);
const collectedCount = ref(0);
const sourceTextarea = ref(null);

let titleTimer = null;

const ui = computed(() => messages[systemLanguage.value] || messages.en);
const modelOptions = computed(() => providerModels[translator.value] || providerModels.deepseek);
const titleHint = computed(() => `${ui.value.titleWorking}${".".repeat(titleDots.value + 1)}`);
const vocabularyHint = computed(() => `${collectedCount.value} item(s) collected in this session.`);
const panelFontStyle = computed(() => ({
  fontFamily: fontFamily.value,
  fontSize: `${Number.parseInt(fontSize.value, 10) || 20}px`
}));

watch(isTranslating, (active) => {
  document.title = active ? `(${ui.value.titleWorking}) Game Dialogue Translator` : "Game Dialogue Translator";
});

watch(translator, (provider) => {
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

onMounted(() => {
  titleTimer = window.setInterval(() => {
    titleDots.value = (titleDots.value + 1) % 3;
  }, 450);
  refreshWindows();
});

onUnmounted(() => {
  if (titleTimer) {
    window.clearInterval(titleTimer);
  }
});

function safeApiKey() {
  return apiKey.value.trim();
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

function togglePlaceHint() {
  statusMessage.value = ui.value.placeHint;
}

function increaseFont() {
  fontSize.value = String((Number.parseInt(fontSize.value, 10) || 20) + 1);
}

function decreaseFont() {
  fontSize.value = String(Math.max((Number.parseInt(fontSize.value, 10) || 20) - 1, 10));
}

function baseRequest() {
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
    statusMessage.value = String(error || "Operation failed");
  } finally {
    isTranslating.value = false;
  }
}

async function refreshWindows() {
  statusMessage.value = ui.value.refreshing;
  try {
    const response = await invoke("list_windows_command");
    windowOptions.value = response.windows || [];
    statusMessage.value = ui.value.windowsLoaded;
  } catch (error) {
    statusMessage.value = String(error || "Failed to refresh windows");
  }
}

function applySelectedWindow() {
  const selected = windowOptions.value.find((item) => item.label === selectedWindowLabel.value);
  if (selected) {
    windowTitle.value = selected.title;
  }
}

async function startOcrTranslation() {
  if (!windowTitle.value.trim()) {
    statusMessage.value = ui.value.noWindow;
    return;
  }

  await withBusy(ui.value.titleWorking, async () => {
    const response = await invoke("ocr_translate_command", {
      request: {
        ...baseRequest(),
        windowTitle: windowTitle.value.trim(),
        ocrEngine: ocrEngine.value,
        left: floatValue(cropLeft.value, 0.05),
        top: floatValue(cropTop.value, 0.62),
        right: floatValue(cropRight.value, 0.95),
        bottom: floatValue(cropBottom.value, 0.95)
      }
    });
    sourceText.value = response.source || sourceText.value;
    translatedText.value = response.translation || "";
    statusMessage.value = ui.value.ready;
  });
}

async function selectCaptureArea() {
  if (!windowTitle.value.trim()) {
    statusMessage.value = ui.value.noWindow;
    return;
  }

  statusMessage.value = ui.value.selectingArea;
  try {
    const response = await invoke("select_area_command", {
      request: {
        windowTitle: windowTitle.value.trim()
      }
    });
    if (response.cancelled) {
      statusMessage.value = ui.value.stopped;
      return;
    }
    cropLeft.value = String(response.left);
    cropTop.value = String(response.top);
    cropRight.value = String(response.right);
    cropBottom.value = String(response.bottom);
    statusMessage.value = ui.value.areaUpdated;
  } catch (error) {
    statusMessage.value = String(error || "Failed to select area");
  }
}

async function runTextTranslation() {
  const text = sourceText.value.trim();
  if (!text) {
    statusMessage.value = ui.value.noSource;
    return;
  }

  await withBusy(ui.value.titleWorking, async () => {
    const response = await invoke("translate_text_command", {
      request: {
        ...baseRequest(),
        text
      }
    });
    sourceText.value = response.source || text;
    translatedText.value = response.translation || "";
    statusMessage.value = ui.value.ready;
  });
}

function stopTranslation() {
  isTranslating.value = false;
  statusMessage.value = ui.value.stopped;
}

async function copyTranslation() {
  try {
    await navigator.clipboard.writeText(translatedText.value || "");
    statusMessage.value = ui.value.copied;
  } catch {
    statusMessage.value = translatedText.value || "";
  }
}

async function collectSelection() {
  const textarea = sourceTextarea.value;
  const selected = textarea
    ? textarea.value.slice(textarea.selectionStart || 0, textarea.selectionEnd || 0).trim()
    : "";
  if (!selected) {
    statusMessage.value = ui.value.noSelection;
    return;
  }
  await collectEntry(selected, "");
}

async function collectCurrent() {
  const source = sourceText.value.trim();
  if (!source) {
    statusMessage.value = ui.value.noSource;
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
        sourceLanguage: leftOutput.value,
        targetLanguage: rightOutput.value,
        windowTitle: windowTitle.value,
        kind: source.includes("\n") || source.length > 32 ? "line" : "word",
        note: "",
        tags: "tauri"
      }
    });
    collectedCount.value += 1;
    statusMessage.value = ui.value.collected;
  } catch (error) {
    statusMessage.value = String(error || "Failed to collect vocabulary");
  }
}
</script>
