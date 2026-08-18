# Provider research notes

## Sarvam AI — India
Official pricing: https://docs.sarvam.ai/api/getting-started/pricing
Official limits/credits: https://docs.sarvam.ai/api/getting-started/ratelimits
Official quickstart: https://docs.sarvam.ai/api/getting-started/quickstart

Findings: new users receive ₹100 free credits; credits are universal and do not expire; Starter rate limit is 60 req/min generally and 40 req/min for Sarvam-105B; API supports chat completion, speech-to-text, translation, TTS, and document/vision services. Models listed include sarvam-105b, sarvam-105b-conversations, Gemma-4 31B beta, and other beta models. The docs emphasize Indian-language optimization; Romanian quality is unverified, so Sarvam is a candidate specialist/fallback, not assumed primary for Romanian editorial synthesis.

## Mistral AI — Europe / France
Official usage limits: https://docs.mistral.ai/admin/billing-usage/usage-limits
Official models: https://docs.mistral.ai/models
Findings: Free mode allows API keys and included monthly usage within the limits shown on the Limits page; no fixed quota was captured from the general usage page because current limits are account/model dependent. API exposes completion models and token/request rate limits. Mistral is a strong European candidate for Romanian evaluation and is already in the IZZ.ro OpenAI-compatible provider catalog.

Open questions to verify next: Google/Groq/Cerebras/OpenRouter free quotas; whether Japan/Korea/Israel providers have real public APIs and free access; academic evidence for routing, ensembles, self-consistency, and verifier stages.

## Google Gemini — America / Google
Official pricing: https://ai.google.dev/gemini-api/docs/pricing
Official rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
Findings: Google states that developers can start free; free tier includes limited model access, free input/output tokens, and Google AI Studio access. Limits vary by model/project and are visible in AI Studio; measured dimensions include RPM, TPM, RPD. Free-tier content may be used to improve products. Suitable primary/quality provider, but quota and data-use caveat must be explicit.

## Groq — America / United States
Official rate limits: https://console.groq.com/docs/rate-limits
Findings: official docs expose a Free Plan table with model-specific RPM/RPD/TPM/TPD; examples include openai/gpt-oss-120b and 20b at 30 RPM, 1K RPD, 8K TPM, 200K TPD, plus qwen/qwen3.6-27b. Rate limit headers and retry-after are available. Strong speed/fallback candidate, not an unrestricted free service.

## Cerebras — America / United States
Official rate limits: https://inference-docs.cerebras.ai/support/rate-limits
Findings: Free Trial tier offers 5 RPM, 30K TPM, 1M TPH, 1M TPD for gpt-oss-120b and gemma-4-31b; new accounts receive $5 free credits after adding a verified payment method; credits expire after 30 days; docs explicitly say no permanent free tier. Good trial/speed benchmark candidate, not a perpetual free production fallback.

## SEA-LION — Singapore / Asia
Official API: https://docs.sea-lion.ai/guides/inferencing/api
Findings: API key can be created as a trial key; OpenAI-compatible chat completions endpoint; models include Qwen-SEA-LION v4.5 27B instruct, Llama-SEA-LION v3.5 70B reasoning, SEA-Guard safety classifier, and SEA-LION ModernBERT embeddings. Supports text generation, translation, summarization, function calling, guard classification, embeddings. Focus is Southeast Asian languages, so Romanian suitability is unverified; good regional specialist/guard candidate, not primary Romanian editor.

## NAVER HyperCLOVA X / CLOVA Studio — South Korea / Asia
Official overview: https://api.ncloud-docs.com/docs/en/ai-naver-clovastudio-summary
Findings: REST APIs for sentence generation, tuning, router, skill trainer, chat completions, structured outputs, function calling, RAG reasoning, reranker, embeddings, streaming. Test API keys exist, but the official page did not establish a clear free quota/credit amount; therefore it is not qualified as a verified free provider yet.

## AI21 Labs / Jamba — Israel / Asia
Official pricing: https://docs.ai21.com/docs/usage-cost
Official models: https://docs.ai21.com/docs/jamba-foundation-models
Findings: new accounts receive $10 free credit valid for 3 months; API/SDK/playground access; Jamba supports 9 official languages (English, Spanish, French, Portuguese, Italian, Dutch, German, Arabic, Hebrew), not Romanian. Good multilingual/English verifier candidate, not Romanian primary.

## Scaleway Generative APIs — France / Europe
Official API/pricing: https://www.scaleway.com/en/generative-apis/
Official FAQ: https://www.scaleway.com/en/docs/generative-apis/faq/
Findings: OpenAI-compatible serverless APIs hosted in Paris; 1,000,000 free tokens for new customers, then pay per token; supports chat, vision, embeddings, structured outputs, function calling, RAG and batches. Catalog includes Mistral, Gemma, Llama, Qwen, GLM and embedding models. Strong European hosting/privacy and controlled fallback candidate; free allowance is one-time/new-customer, not perpetual.

## OpenRouter — America / United States
Official limits: https://openrouter.ai/docs/api_reference/limits
Free variant: https://openrouter.ai/docs/guides/routing/model-variants/free
Free router: https://openrouter.ai/docs/guides/routing/routers/free-router
Official FAQ: https://openrouter.ai/docs/faq
Findings: OpenAI-compatible API and dynamic free router; free models have 20 RPM, 50 requests/day without purchased credits, or 1,000/day after at least $10 credits; availability changes and free model selection can be random. Supports filtering for structured outputs, tools, vision; actual selected model is returned. Excellent development/fallback pool, unsuitable as the sole quality-critical production editor because model availability and identity vary.

## Structured outputs and contract support
Mistral custom structured outputs: https://docs.mistral.ai/studio-api/conversations/structured-output/custom
Mistral JSON mode: https://docs.mistral.ai/studio-api/conversations/structured-output/json_mode
Gemini structured outputs: https://ai.google.dev/gemini-api/docs/structured-output
Findings: Mistral supports JSON mode and custom JSON schema/Pydantic structured output; Gemini supports JSON Schema, Pydantic/Zod, structured extraction/classification/agentic workflows. These are important for IZZ.ro's strict article contract. Sarvam documentation states its flagship chat models are optimized for Indian languages and lists language coverage that does not include Romanian; its open-source Gemma/GLM models are not tuned by Sarvam for Indian languages.

## Routing research
FrugalGPT, arXiv: https://arxiv.org/abs/2305.05176
Findings: proposes prompt adaptation, approximation, and LLM cascades; reports matching the best individual model with up to 98% cost reduction in its experiments, but this is a research result on its benchmarks, not a guaranteed IZZ.ro result.

RouteLLM, ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/5503a7c69d48a2f86fc00b3dc09de686-Abstract-Conference.html
Findings: learns a router from preference data to select between stronger and weaker models; reports over 2x cost reduction without sacrificing response quality on public benchmarks and generalization to unseen model pairs.

RouterBench, arXiv: https://arxiv.org/abs/2403.12031
Findings: benchmark/framework for multi-LLM routing with over 405k inference outcomes, multiple datasets and models, and theoretical evaluation of routing strategies. Supports evaluating quality-cost tradeoffs rather than assuming a provider ranking.

Architectural implication: start with deterministic routing by task class and provider health; later learn a router from IZZ.ro's own accepted/rejected outputs. Use a strong judge/verifier only for difficult or high-risk items, not for every item, to avoid duplicating cost.

## Claude Code as orchestrator/validator
Official headless/Agent SDK docs: https://docs.anthropic.com/en/docs/claude-code/headless
Official auth docs: https://docs.anthropic.com/en/docs/claude-code/iam
Official costs docs: https://docs.anthropic.com/en/docs/claude-code/costs
Official Pro/Max access: https://support.anthropic.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan
Findings: Claude Code can run non-interactively with `claude -p`, `--bare`, `--allowedTools`, `--output-format json` and `--json-schema`; it can therefore act as a scripted orchestrator, project-specific linter, reviewer, and structured validator. Pro/Max login gives Claude Code access through the subscription, and Pro/Claude Code usage shares the plan's limits; setting ANTHROPIC_API_KEY causes Claude Code to use API billing instead of subscription login. Headless `--bare` mode does not use subscription OAuth credentials or system keychain and requires ANTHROPIC_API_KEY or another provider credential. Therefore local interactive orchestration can use the Pro session, while unattended CI requires a deliberate credential path (Anthropic API/Console, Bedrock/Vertex/Foundry, or a pre-authenticated runner) and must not assume that a local Pro login exists in GitHub Actions.

Architecture decision: Claude Code should be added as a first-class `orchestrator_validator` stage, but separate from the provider router. In local Windows operation it can orchestrate fetch -> generator -> validators, inspect logs, run tests, compare outputs, and approve/reject batches through `claude -p` with JSON schema. In CI, use it only when authentication is explicitly provisioned; otherwise the deterministic Python pipeline and API providers remain the unattended path. The subscription is valuable for local/operator-driven runs and reviews, but not a magic API key for arbitrary background jobs.

## Subscription-based CLI access without classic API keys
Claude Code: https://docs.anthropic.com/en/docs/claude-code/headless ; https://docs.anthropic.com/en/docs/claude-code/iam ; https://support.anthropic.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan
Findings: local Claude Code can authenticate with a Claude Pro/Max account and run `claude -p` non-interactively; structured JSON output is available. However `--bare` skips OAuth/subscription credentials and requires API or provider credentials. A local cached login can support operator-driven scripts, while unattended CI needs deliberate trusted authentication; Pro usage is shared with Claude and subject to plan limits.

Gemini CLI: https://geminicli.com/docs/get-started/authentication/ ; https://geminicli.com/docs/resources/quota-and-pricing/ ; https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
Findings: Gemini CLI docs describe account login and quotas, but Google's official deprecation page says that from June 18, 2026 personal/Google AI Pro/Ultra Google-login access to Gemini CLI stopped and users should migrate to Antigravity CLI. Thus do not design around a personal Gemini subscription for current Gemini CLI; use supported Antigravity path, API key, Vertex AI, or organization Code Assist Standard/Enterprise where applicable.

OpenAI Codex CLI: https://learn.chatgpt.com/docs/auth
Findings: Codex CLI supports both Sign in with ChatGPT for subscription access and API-key authentication for usage-based access in local work. OpenAI recommends API-key authentication for programmatic CI/CD; ChatGPT Enterprise can issue Codex access tokens for trusted non-interactive local workflows. Cached ChatGPT credentials are sensitive and must never enter the repository. Therefore ChatGPT/Codex is suitable as a local subscription-based orchestrator/validator, but unattended public CI should use a dedicated trusted credential path.
