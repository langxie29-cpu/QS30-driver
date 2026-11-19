import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { randomUUID } from "node:crypto";

const [root, mode, inputPath] = process.argv.slice(2);
const pkg = join(root, "app/node_modules/@deepseek-ai/dsh");
const modules = join(pkg, "node_modules");
const model = "deepseek-v4-flash";
const provider = "deepseek-official";
const endpoint = "https://api.deepseek.com";
const receipt = {model, provider, endpoint, requests: 0, http_status: null,
                 failed_requests: 0, usage: null, finish: null, cost: "UNKNOWN"};
const emit = (data) => process.stdout.write(JSON.stringify(data) + "\n");
try {
    const { default: yaml } = await import(pathToFileURL(join(modules, "yaml/dist/index.js")));
    const settings = yaml.parse(readFileSync(join(root, "data/settings.yaml"), "utf8"));
    const currentModel = settings?.["agent-default-model"];
    const route = settings?.["llm-deepseek"] ?? {};
    const url = route.baseURL ?? process.env.DEEPSEEK_BASE_URL ?? endpoint;
    if (currentModel?.model !== model || currentModel?.provider !== provider || url !== endpoint) {
        throw new Error("IDENTITY_MISMATCH");
    }
    const { DeepSeekAdapter, resolveAdapterOptions } = await import(pathToFileURL(
        join(modules, "@deepseek-ai/dsh-llm-deepseek/lib/index.js")));
    const { createUserMessage } = await import(pathToFileURL(
        join(modules, "@deepseek-ai/dsh-llm/lib/index.js")));
    const options = resolveAdapterOptions({ apiKeyEnv: route.apiKeyEnv, baseURL: endpoint,
        thinking: "disabled", reasoningEffort: "off", maxTokens: 2200, streamIdleTimeoutMs: 90000 });
    const store = yaml.parse(readFileSync(join(root, "data/.credentials.yaml"), "utf8"));
    const apiKey = process.env[options.apiKeyEnv] ?? store?.[options.apiKeyEnv];
    if (typeof apiKey !== "string" || !apiKey.trim()) throw new Error("MISSING_CREDENTIAL");
    const adapter = new DeepSeekAdapter({options: () => options, resolveApiKey: async () => apiKey,
                                      resolveUserId: () => randomUUID()});
    const catalog = await adapter.listModels(provider);
    if (!catalog.some((entry) => entry.id === model && entry.provider === provider)) {
        throw new Error("IDENTITY_MISMATCH");
    }

    if (mode === "probe") {
        emit({status: "VERIFIED", model, provider, endpoint, transport: "installed DeepSeek Harness adapter",
              credential_present: true, provider_requests: 0, tools: "none", max_requests_per_call: 1});
    } else {
        if (mode !== "call" || !inputPath) throw new Error("INVALID_MODE");
        const prompt = readFileSync(inputPath, "utf8");
        if (Buffer.byteLength(prompt) > 16000) throw new Error("INPUT_CAP");
        const fetchOriginal = globalThis.fetch.bind(globalThis);
        globalThis.fetch = async (uri, settings) => {
            const payload = JSON.parse(settings.body);
            if (receipt.requests || String(uri) !== endpoint + "/chat/completions" ||
                settings.method !== "POST" || payload.model !== model || payload.tools?.length ||
                payload.max_tokens !== 2200) throw new Error("REQUEST_BOUND");
            receipt.requests += 1;
            const response = await fetchOriginal(uri, {...settings, redirect: "error"});
            receipt.http_status = response.status;
            return response;
        };
        const events = [];
        const message = createUserMessage({content:[{type:"text",text:prompt}],source:{kind:"user"}});
        for await (const record of adapter.stream({
            provider, model, messages:[message], tools:[], maxTokens:2200,
            signal:AbortSignal.timeout(120000)
        })) {
            if (record.type === "text-delta") events.push({type: record.type, text: record.text});
            if (record.type === "usage") receipt.usage = record.usage;
            if (record.type === "finish") receipt.finish = record.reason.kind;
        }
        emit({receipt, events});
        if (receipt.finish !== "stop") process.exitCode = 2;
    }
} catch (error) {
    receipt.failed_requests = receipt.requests;
    const raw = typeof error?.code === "string" ? error.code : error?.message;
    const diagnosis = typeof raw === "string" && /^[A-Z0-9_]{1,70}$/.test(raw) ? raw : "SETUP_OR_TRANSPORT_ERROR";
    emit({receipt, failure: diagnosis});
    process.exitCode = 2;
}

