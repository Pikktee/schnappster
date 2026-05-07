# Evidence-Based Deal Analysis

Schnappster now treats bargain detection as a bounded analysis funnel instead of one
large prompt.

## Pipeline

1. **Product Analyst** (`OPENAI_CHEAP_MODEL`)
   Extracts a product key, category, uncertainty and a small set of comparison queries.
2. **Comparison Judge** (`OPENAI_CHEAP_MODEL`)
   Classifies same-search comparison ads as comparable, worse, better, bundle, accessory or
   unknown. This prevents unrelated search results from polluting the market value.
3. **Market Estimator** (deterministic Python)
   Computes a conservative median market value from accepted comparisons and stores confidence,
   delta and comparison count.
4. **Final Deal Scorer** (`OPENAI_MODEL` only for likely deals)
   Produces the single user-facing `bargain_score`, `ai_summary` and `ai_reasoning`. If the
   deterministic estimate is not promising enough, this step uses `OPENAI_CHEAP_MODEL`.

The UI can keep treating `bargain_score` as the main result. Additional evidence is persisted
for debugging and later display:

- `estimated_market_price`
- `market_price_confidence`
- `price_delta_percent`
- `comparison_count`
- `comparison_summary`
- `deal_evidence`

## Cost Controls

Use these environment variables to tune the funnel:

```env
OPENAI_CHEAP_MODEL=openai/gpt-5.4-nano
OPENAI_MODEL=openai/gpt-5.4-mini
AI_MAX_COMPARISON_CANDIDATES=12
AI_STRONG_MODEL_MIN_DELTA_PERCENT=18
AI_STRONG_MODEL_MIN_SAVINGS_EUR=75
```

Images are not controlled by an env flag. The final scoring model first gets a text-only
prompt and may call the `request_product_images` tool when visible product details are
needed. Only then Schnappster downloads all available ad images, optimizes them, and runs a
second multimodal final scoring call.

## Model Recommendation

For OpenRouter-compatible routing:

- **Cheap/high-volume steps:** `openai/gpt-5.4-nano`
- **Final scoring for likely bargains:** `openai/gpt-5.4-mini`
- **Higher-quality final scoring for expensive/unclear deals:** `openai/gpt-5.4`
- **Alternative cheap text-only model:** `qwen/qwen3-30b-a3b`
- **Alibaba/Qwen stronger alternative:** `qwen/qwen3.6-35b-a3b`

As of 2026-05-05, OpenRouter lists GPT-5.4 nano at $0.20/M input and
$1.25/M output, GPT-5.4 mini at $0.75/M input and $4.50/M output, and GPT-5.4
at $2.50/M input and $15/M output. Qwen3 30B A3B is listed at $0.08/M input
and $0.28/M output, while Qwen3.6 35B A3B is listed around $0.1612/M input and
$0.9653/M output. Check provider pricing before large runs because model IDs
and prices move.
