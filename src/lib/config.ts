import yaml from "js-yaml";

export interface ChatConfig {
  branding: {
    appName: string;
    logoPath: string;
    logoWidth: number;
    logoHeight: number;
    description?: string;
    chatOpeners?: string[];
    fullDescription?: string;
  };
  categories?: {
    [key: string]: {
      icon: string;
      description: string;
      openers: string[];
    };
  };
  buttons: {
    enableFileUpload: boolean;
    chatInputPlaceholder: string;
  };
  threads: {
    showHistory: boolean;
    enableDeletion: boolean;
    enableTitleEdit: boolean;
    autoGenerateTitles: boolean;
    sidebarOpenByDefault: boolean;
  };
  theme: {
    fontFamily: "sans" | "serif" | "mono";
    fontSize: "small" | "medium" | "large";
    colorScheme: "light" | "dark" | "auto";
  };
  ui: {
    autoCollapseToolCalls: boolean;
    chatWidth: "default" | "wide";
  };
  mcp?: {
    enabled: boolean;
    servers?: {
      [key: string]: {
        url?: string;
        command?: string;
        args?: string[];
        env?: Record<string, string>;
      };
    };
  };
}

// Default configuration
export const defaultConfig: ChatConfig = {
  branding: {
    appName: "hooxibot",
    logoPath: "/logo.png",
    logoWidth: 32,
    logoHeight: 32,
    description: "AI 어시스턴트와 대화를 시작하세요",
    chatOpeners: [
      "오늘의 날씨는 어때?",
      "간단한 요리 레시피 추천해줘",
      "Python 코딩 도움이 필요해",
      "재미있는 이야기 들려줘",
    ],
    fullDescription: "/full-description.md",
  },
  buttons: {
    enableFileUpload: true,
    chatInputPlaceholder: "무엇이든 물어보세요",
  },
  threads: {
    showHistory: false,
    enableDeletion: true,
    enableTitleEdit: true,
    autoGenerateTitles: true,
    sidebarOpenByDefault: false,
  },
  theme: {
    fontFamily: "sans",
    fontSize: "medium",
    colorScheme: "light",
  },
  ui: {
    autoCollapseToolCalls: true,
    chatWidth: "wide",
  },
  mcp: {
    enabled: false,
    servers: {},
  },
};

export function mergeConfig(config: Partial<ChatConfig> = {}): ChatConfig {
  return {
    branding: { ...defaultConfig.branding, ...config.branding },
    buttons: { ...defaultConfig.buttons, ...config.buttons },
    threads: { ...defaultConfig.threads, ...config.threads },
    theme: { ...defaultConfig.theme, ...config.theme },
    ui: { ...defaultConfig.ui, ...config.ui },
    mcp: config.mcp
      ? { 
          enabled: config.mcp.enabled ?? defaultConfig.mcp?.enabled ?? false,
          servers: { ...defaultConfig.mcp?.servers, ...config.mcp.servers },
        }
      : defaultConfig.mcp ?? { enabled: false, servers: {} },
  };
}

// Load chat categories from YAML file
async function loadChatCategories(): Promise<any | undefined> {
  try {
    const response = await fetch("/chat-categories.yaml");
    if (!response.ok) {
      console.warn("Failed to fetch chat-categories.yaml, status:", response.status);
      return undefined;
    }

    const yamlText = await response.text();
    console.log("chat-categories.yaml loaded successfully");
    const data = yaml.load(yamlText) as { categories?: any };
    return data.categories;
  } catch (error) {
    console.warn("Failed to load chat-categories.yaml:", error);
    return undefined;
  }
}

// Load chat openers from separate file
async function loadChatOpeners(): Promise<string[] | undefined> {
  try {
    const response = await fetch("/chat-openers.yaml");
    if (!response.ok) {
      console.warn("Failed to fetch chat-openers.yaml, status:", response.status);
      return undefined;
    }

    const yamlText = await response.text();
    console.log("chat-openers.yaml loaded successfully");
    const data = yaml.load(yamlText) as { chatOpeners?: string[] };
    console.log("Parsed chat openers:", data.chatOpeners?.length, "items");
    return data.chatOpeners;
  } catch (error) {
    console.warn("Failed to load chat-openers.yaml:", error);
    return undefined;
  }
}

// Load configuration from YAML file
export async function loadConfig(): Promise<ChatConfig> {
  try {
    // Try to load settings.yaml first, fallback to chat-config.yaml
    let response = await fetch("/settings.yaml");
    if (!response.ok) {
      response = await fetch("/chat-config.yaml");
    }
    if (!response.ok) {
      console.warn("Failed to load settings.yaml or chat-config.yaml, using default config");
      return defaultConfig;
    }
    const yamlText = await response.text();
    const config = yaml.load(yamlText) as Partial<ChatConfig>;

    // Load chat openers separately
    const chatOpeners = await loadChatOpeners();
    
    // Load chat categories
    const categories = await loadChatCategories();

    // Merge config with chat openers and categories
    const mergedConfig = mergeConfig(config);
    if (chatOpeners) {
      mergedConfig.branding.chatOpeners = chatOpeners;
    }
    if (categories) {
      mergedConfig.categories = categories;
    }

    return mergedConfig;
  } catch (error) {
    console.error("Error loading config:", error);
    return defaultConfig;
  }
}
