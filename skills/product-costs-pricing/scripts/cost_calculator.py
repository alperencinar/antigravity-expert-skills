#!/usr/bin/env python3
import sys
import argparse

# Base Exchange Rate
EXCHANGE_RATE = 46.82

# API Prices per 1M tokens: (input, output, cache_hit)
MODEL_PRICES = {
    # Gemini
    "gemini-2.5-flash-lite": (0.075, 0.300, 0.01875),
    "gemini-2.5-flash": (0.150, 0.600, 0.0375),
    "gemini-3.1-flash-lite": (0.070, 0.280, 0.0175),
    "gemini-3.1-flash": (0.140, 0.560, 0.035),
    # DeepSeek
    "deepseek-v4-pro": (0.140, 0.280, 0.050),
    "deepseek-chat": (0.140, 0.280, 0.014),
    # Claude
    "claude-3-5-haiku": (0.80, 4.00, 0.08),
    "claude-3-5-sonnet": (3.00, 15.00, 0.30)
}

def calculate_costs(model, input_tokens, output_tokens, cache_pct=0.0):
    if model not in MODEL_PRICES:
        raise ValueError(f"Unknown model: {model}. Available: {list(MODEL_PRICES.keys())}")
        
    in_rate, out_rate, cache_rate = MODEL_PRICES[model]
    
    # Calculate caching
    cached_tokens = input_tokens * (cache_pct / 100.0)
    uncached_tokens = input_tokens - cached_tokens
    
    input_cost = (uncached_tokens * in_rate + cached_tokens * cache_rate) / 1,000,000.0
    # Wait, 1,000,000.0 has commas, which is a tuple in python: 1, 0, 0
    # Let's fix that! In Python, commas are separators. It must be 1000000.0!
    # Let's write: 1000000.0
    input_cost = (uncached_tokens * in_rate + cached_tokens * cache_rate) / 1000000.0
    output_cost = (output_tokens * out_rate) / 1000000.0
    
    total_cost_usd = input_cost + output_cost
    total_cost_try = total_cost_usd * EXCHANGE_RATE
    
    return total_cost_usd, total_cost_try

def main():
    parser = argparse.ArgumentParser(description="Calculate LLM API run costs and pricing margins.")
    parser.add_argument("--model", type=str, default="deepseek-v4-pro", help="Model name.")
    parser.add_argument("--input", type=int, default=1000, help="Input tokens count.")
    parser.add_argument("--output", type=int, default=500, help="Output tokens count.")
    parser.add_argument("--cache-pct", type=float, default=0.0, help="Percentage of prompt cached (0-100).")
    parser.add_argument("--price-try", type=float, help="Suggested product price in TRY.")
    parser.add_argument("--credits", type=int, help="Credit amount given to the user for the product price.")
    parser.add_argument("--credits-per-run", type=int, default=75, help="Credits consumed per standard run.")
    
    args = parser.parse_args()
    
    try:
        usd_cost, try_cost = calculate_costs(args.model, args.input, args.output, args.cache_pct)
        print("==================================================")
        print(f"Cost Summary for {args.model}:")
        print(f"  Input Tokens:  {args.input:,} ({args.cache_pct}% cached)")
        print(f"  Output Tokens: {args.output:,}")
        print(f"  Total Cost (USD): ${usd_cost:.6f}")
        print(f"  Total Cost (TRY): {try_cost:.4f} TL")
        print("==================================================")
        
        if args.price_try and args.credits:
            runs_provided = args.credits / args.credits_per_run
            total_execution_cost_try = runs_provided * try_cost
            gross_profit_try = args.price_try - total_execution_cost_try
            margin = (gross_profit_try / args.price_try) * 100.0
            
            # Suggest a safety buffer (which includes retry costs, parities, etc. usually +20%)
            buffer_multiplier = 1.20
            cost_with_buffer_try = try_cost * buffer_multiplier
            total_buffered_cost_try = runs_provided * cost_with_buffer_try
            buffered_gross_profit_try = args.price_try - total_buffered_cost_try
            buffered_margin = (buffered_gross_profit_try / args.price_try) * 100.0
            
            print(f"Pricing & Margins (for {args.credits:,} Credits at {args.price_try} TL):")
            print(f"  Total Runs Provided:  {runs_provided:.2f} runs")
            print(f"  Raw Runs Cost (TRY):  {total_execution_cost_try:.2f} TL")
            print(f"  Gross Profit (Raw):   {gross_profit_try:.2f} TL")
            print(f"  Profit Margin (Raw):  {margin:.2f}%")
            print(f"  ----------------------------------------------")
            print(f"  Buffered Cost (+20%): {total_buffered_cost_try:.2f} TL")
            print(f"  Gross Profit (Buff):  {buffered_gross_profit_try:.2f} TL")
            print(f"  Profit Margin (Buff): {buffered_margin:.2f}%")
            
            # Recommendation
            if buffered_margin < 50.0:
                print("  ❌ WARNING: Buffered margin is under 50%! Consider raising prices or lowering credits.")
            elif buffered_margin < 70.0:
                print("  ⚠️ NOTICE: Healthy margin for subscriptions, but check if consumable packages require >70% margin.")
            else:
                print("  ✅ EXCELLENT: Healthy gross margins (>70%).")
            print("==================================================")
            
    except Exception as e:
        print("Error:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
