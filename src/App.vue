<template>
  <div class="app-shell">
    <main class="surface">
      <section class="control-card">
        <div class="status-ribbon">
          <strong>Game Dialogue Translator</strong>
          <span v-if="isTranslating" class="title-badge">{{ titleHint }}</span>
          <span class="window-state">{{ statusMessage || ui.ready }}</span>
        </div>

        <div class="control-ribbon">
          <label class="field field-window">
            <span>{{ ui.windowTitle }}</span>
            <input v-model="windowTitle" />
          </label>
          <button class="btn btn-ghost" :disabled="isTranslating" @click="refreshWindows">
            {{ ui.refreshWindows }}
          </button>
          <button class="btn btn-ghost" type="button" @click="toggleLayout">
            {{ layout === "vertical" ? ui.layoutVertical : ui.layoutHorizontal }}
          </button>
        </div>

        <div class="action-ribbon">
          <button class="btn btn-primary" :disabled="isTranslating" @click="startOcrTranslation">
            {{ isTranslating ? ui.translating : ui.start }}
          </button>
          <button class="btn btn-ghost" :disabled="isTranslating" @click="runTextTranslation">
            {{ ui.retranslate }}
          </button>
          <button class="btn btn-danger" @click="stopTranslation">{{ ui.stop }}</button>
          <span class="ribbon-divider"></span>
          <button class="btn btn-ghost" :disabled="isTranslating" @click="collectSelection">
            {{ ui.collectSelection }}
          </button>
          <button class="btn btn-ghost" :disabled="isTranslating" @click="collectCurrent">
            {{ ui.collectCurrent }}
          </button>
          <button class="btn btn-ghost push-end" type="button" @click="advancedOpen = !advancedOpen">
            {{ advancedOpen ? ui.hideAdvanced : ui.advanced }}
          </button>
        </div>

        <div class="settings-matrix">
          <label class="field">
            <span>{{ ui.leftOutput }}</span>
            <select v-model="leftOutput">
              <option>Original OCR</option>
              <option>Japanese</option>
              <option>English</option>
              <option>Simplified Chinese</option>
              <option>Traditional Chinese</option>
            </select>
          </label>

          <label class="field">
            <span>{{ ui.rightOutput }}</span>
            <select v-model="rightOutput">
              <option>Simplified Chinese</option>
              <option>Traditional Chinese</option>
              <option>English</option>
              <option>Japanese</option>
            </select>
          </label>

          <label class="field field-tight">
            <span>{{ ui.layout }}</span>
            <select v-model="layout">
              <option value="vertical">{{ ui.layoutVertical }}</option>
              <option value="horizontal">{{ ui.layoutHorizontal }}</option>
            </select>
          </label>

          <label class="field">
            <span>{{ ui.model }}</span>
            <select v-model="model">
              <option v-for="modelOption in modelOptions" :key="modelOption" :value="modelOption">
                {{ modelOption }}
              </option>
              <option value="__custom__">{{ ui.customModel }}</option>
            </select>
          </label>

          <label class="field field-wide">
            <span>{{ ui.windowList }}</span>
            <select v-model="selectedWindowLabel" @change="applySelectedWindow">
              <option value="">{{ ui.noWindowSelected }}</option>
              <option v-for="window in windowOptions" :key="window.hwnd" :value="window.label">
                {{ window.label }}
              </option>
            </select>
          </label>

          <label class="field field-tight">
            <span>{{ ui.translator }}</span>
            <select v-model="translator">
              <option>deepseek</option>
              <option>grok</option>
              <option>openai</option>
              <option>libretranslate</option>
              <option>argos</option>
            </select>
          </label>

          <label class="field field-tight">
            <span>{{ ui.ocr }}</span>
            <select v-model="ocrEngine">
              <option>tesseract</option>
              <option>openai-vision</option>
            </select>
          </label>
        </div>

        <div class="utility-strip">
          <button class="btn btn-ghost" type="button" @click="showProviderPanel = !showProviderPanel">
            {{ ui.providerConfigs }}
          </button>
          <button class="btn btn-ghost" type="button" @click="showVocabularyPanel = !showVocabularyPanel">
            {{ ui.vocabulary }}
          </button>
          <span class="strip-spacer"></span>
          <label class="mini-field">
            <span>{{ ui.fontSize }}</span>
            <input v-model="fontSize" />
          </label>
          <label class="mini-field language-field">
            <span>{{ ui.systemLanguage }}</span>
            <select v-model="systemLanguage">
              <option value="en">English</option>
              <option value="zh-CN">Simplified Chinese</option>
            </select>
          </label>
          <label class="check-field">
            <input v-model="lockCurrentLine" type="checkbox" />
            <span>{{ ui.lockCurrentLine }}</span>
          </label>
        </div>

        <section v-if="advancedOpen" class="advanced-panel">
          <div class="advanced-grid">
            <label class="field field-tight">
              <span>{{ ui.intervalMs }}</span>
              <input v-model="intervalMs" />
            </label>
            <label class="field field-tight">
              <span>{{ ui.context }}</span>
              <input v-model="contextLines" />
            </label>
            <label class="field field-tight">
              <span>{{ ui.stableReads }}</span>
              <input v-model="stableReads" />
            </label>
            <label class="field">
              <span>{{ ui.apiUrl }}</span>
              <input v-model="apiUrl" />
            </label>
            <label v-if="model === '__custom__'" class="field">
              <span>{{ ui.customModel }}</span>
              <input v-model="customModel" placeholder="model-id" />
            </label>
            <label class="field field-tight">
              <span>{{ ui.apiKey }}</span>
              <input v-model="apiKey" type="password" autocomplete="off" />
            </label>
            <label class="field">
              <span>{{ ui.libreUrl }}</span>
              <input v-model="libreUrl" />
            </label>
            <label class="field field-tight">
              <span>{{ ui.libreTarget }}</span>
              <input v-model="libreTarget" />
            </label>
          </div>

          <div class="capture-row">
            <span class="capture-label">{{ ui.captureArea }}</span>
            <button class="btn btn-ghost" :disabled="isTranslating" type="button" @click="selectCaptureArea">
              {{ ui.selectArea }}
            </button>
            <label class="mini-field"><span>Left</span><input v-model="cropLeft" /></label>
            <label class="mini-field"><span>Top</span><input v-model="cropTop" /></label>
            <label class="mini-field"><span>Right</span><input v-model="cropRight" /></label>
            <label class="mini-field"><span>Bottom</span><input v-model="cropBottom" /></label>
          </div>
        </section>

        <section v-if="showProviderPanel" class="mini-panel">
          <strong>{{ ui.providerConfigs }}</strong>
          <span>{{ ui.providerHint }}</span>
        </section>

        <section v-if="showVocabularyPanel" class="mini-panel">
          <strong>{{ ui.vocabulary }}</strong>
          <span>{{ vocabularyHint }}</span>
        </section>
      </section>

      <section class="reading-stage">
        <div class="reading-heading">
          <p class="eyebrow">Bilingual Overlay</p>
          <h1>{{ ui.stageTitle }}</h1>
          <p>{{ ui.stageSubtitle }}</p>
        </div>

        <div class="panel-stack" :class="{ horizontal: layout === 'horizontal' }">
          <section class="reading-panel">
            <div class="panel-label">{{ ui.firstPanel }}: {{ leftOutput }}</div>
            <textarea
              ref="sourceTextarea"
              v-model="sourceText"
              class="panel-surface panel-large editable-panel"
              :style="panelFontStyle"
              spellcheck="false"
            ></textarea>
          </section>

          <section class="reading-panel">
            <div class="panel-label">{{ ui.secondPanel }}: {{ rightOutput }}</div>
            <div class="panel-surface panel-large translated-panel" :style="panelFontStyle">
              <p>{{ translatedText || ui.emptyTranslation }}</p>
            </div>
          </section>
        </div>
        <p v-if="statusMessage" class="status-line">{{ statusMessage }}</p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";

const messages = {
  en: {
    windowTitle: "Window title",
    refreshWindows: "Refresh windows",
    layoutVertical: "Top / Bottom",
    layoutHorizontal: "Left / Right",
    customModel: "Custom model",
    translating: "Translating",
    start: "Start OCR",
    retranslate: "Retranslate",
    stop: "Stop",
    collectSelection: "Collect Selection",
    collectCurrent: "Collect Current",
    hideAdvanced: "Hide Advanced",
    advanced: "Advanced & Capture",
    leftOutput: "First area",
    rightOutput: "Second area",
    layout: "Layout",
    model: "Model",
    windowList: "Window list",
    noWindowSelected: "Choose a visible game window",
    translator: "Translator",
    ocr: "OCR",
    providerConfigs: "Models & Key",
    vocabulary: "Vocabulary",
    fontSize: "Font size",
    systemLanguage: "System language",
    lockCurrentLine: "Lock line",
    intervalMs: "Interval ms",
    context: "Context",
    stableReads: "Stable reads",
    apiUrl: "API URL",
    apiKey: "API Key",
    libreUrl: "Libre URL",
    libreTarget: "Libre target",
    captureArea: "Capture ratios",
    selectArea: "Select area",
    providerHint: "API keys stay local in this running app. Use environment variables or a local config file for long-term storage.",
    stageTitle: "Bilingual Reading Stage",
    stageSubtitle: "Player-first visual novel reading, with language learning support kept close but quiet.",
    firstPanel: "First panel",
    secondPanel: "Second panel",
    emptyTranslation: "Translation will appear here.",
    ready: "Ready",
    noSource: "No source text to translate.",
    noWindow: "Select or type a game window title first.",
    noSelection: "Select text in the source panel first.",
    collected: "Collected to vocabulary.",
    stopped: "Stopped",
    refreshing: "Refreshing windows...",
    windowsLoaded: "Window list refreshed.",
    selectingArea: "Drag over the game subtitle area...",
    areaUpdated: "Capture area updated.",
    titleWorking: "Translating..."
  },
  "zh-CN": {
    windowTitle: "窗口标题",
    refreshWindows: "刷新窗口",
    layoutVertical: "上下布局",
    layoutHorizontal: "左右布局",
    customModel: "自定义模型",
    translating: "翻译中",
    start: "启动 OCR",
    retranslate: "重新翻译",
    stop: "停止",
    collectSelection: "收藏选中",
    collectCurrent: "收藏当前",
    hideAdvanced: "隐藏高级",
    advanced: "高级与捕获",
    leftOutput: "第一区域",
    rightOutput: "第二区域",
    layout: "布局",
    model: "模型",
    windowList: "窗口列表",
    noWindowSelected: "选择可见游戏窗口",
    translator: "翻译器",
    ocr: "OCR",
    providerConfigs: "模型与 Key",
    vocabulary: "词汇本",
    fontSize: "字体大小",
    systemLanguage: "系统语言",
    lockCurrentLine: "锁定行",
    intervalMs: "间隔 ms",
    context: "上下文",
    stableReads: "稳定读取",
    apiUrl: "API 地址",
    apiKey: "API Key",
    libreUrl: "Libre 地址",
    libreTarget: "Libre 目标",
    captureArea: "捕获比例",
    selectArea: "手动选区",
    providerHint: "API Key 只保存在本次运行界面中。长期保存建议使用环境变量或本地配置文件。",
    stageTitle: "双语阅读舞台",
    stageSubtitle: "先保证 galgame 阅读沉浸感，再把语言学习能力放在顺手的位置。",
    firstPanel: "第一区域",
    secondPanel: "第二区域",
    emptyTranslation: "翻译会显示在这里。",
    ready: "就绪",
    noSource: "没有可翻译的原文。",
    noWindow: "请先选择或输入游戏窗口标题。",
    noSelection: "请先在原文区域选中文本。",
    collected: "已收藏到词汇本。",
    stopped: "已停止",
    refreshing: "正在刷新窗口...",
    windowsLoaded: "窗口列表已刷新。",
    selectingArea: "请在游戏字幕区域拖拽选区...",
    areaUpdated: "捕获区域已更新。",
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

const advancedOpen = ref(false);
const showProviderPanel = ref(false);
const showVocabularyPanel = ref(false);
const windowTitle = ref("");
const selectedWindowLabel = ref("");
const windowOptions = ref([]);
const leftOutput = ref("Original OCR");
const rightOutput = ref("Simplified Chinese");
const layout = ref("horizontal");
const model = ref("deepseek-v4-flash");
const customModel = ref("");
const translator = ref("deepseek");
const ocrEngine = ref("tesseract");
const fontSize = ref("18");
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
const sourceText = ref("Select a game window, then click Start OCR.\nYou can also paste text here and click Retranslate.");
const translatedText = ref("");
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
  fontSize: `${Number.parseInt(fontSize.value, 10) || 18}px`
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

function toggleLayout() {
  layout.value = layout.value === "vertical" ? "horizontal" : "vertical";
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
    sourceText.value = response.source || "";
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
    if (response.source) {
      sourceText.value = response.source;
    }
    translatedText.value = response.translation || "";
    statusMessage.value = ui.value.ready;
  });
}

function stopTranslation() {
  isTranslating.value = false;
  statusMessage.value = ui.value.stopped;
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
