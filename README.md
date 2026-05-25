# DataFeedPrice

Tick-by-tick price data for backtesting. Organized as one subfolder per instrument.

## Available instruments

| Symbol | Description | Ticks | Size | Period |
|---|---|---|---|---|
| [XAUUSD](./XAUUSD) | Gold vs USD | 286M | 2.47 GB | 2021-05-24 -> 2026-05-24 |
| [US500](./US500) | S&P 500 Index CFD | 90M | 0.87 GB | 2021-05-24 -> 2026-05-24 |

## Schema (all instruments)

- `timestamp` - timestamp[ms], UTC
- `bid_price`, `ask_price` - float64
- `bid_volume`, `ask_volume` - float64

## Mirror on Hugging Face

- https://huggingface.co/datasets/CarlosSilva1/xauusd-ticks
- https://huggingface.co/datasets/CarlosSilva1/us500-ticks

## License

CC-BY-4.0. Not investment advice.
