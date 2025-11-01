# px6-proxy-fetcher

Small helper that grabs your active proxies from [PROXY6.net](https://px6.me/) and drops them into a text file you can hand to whatever is doing the crawling. I've leaned on PX6 as my low-cost proxy pool for months; it's been steady and easy to manage, so this script wraps the one task I end up repeating the most.

## installation

Install from PyPI:

```bash
pip install px6-proxy-fetcher
# want .env support? pip install px6-proxy-fetcher[dotenv]
```

## getting started

First, grab your API key from the [PROXY6.net dashboard](https://px6.me/). Then run it:

```bash
export PX6_API_KEY="your_api_key_here"
px6-proxy-fetcher --print-env
```

That writes `proxies.txt` in the current directory containing your active proxies in `scheme://user:pass@host:port` format. With `--print-env`, it also emits shell exports for `PROXY_LIST` (comma-separated proxy URLs) and `PROXY_STRATEGY` (defaults to `round_robin`).

Options:
- `-o path/to/file.txt` - write to a different location
- `-q` - quiet mode (errors only)
- `-v` - verbose mode (debug output)
- `--print-env` - output shell export statements
- `--timeout SECONDS` - HTTP timeout for API requests (default: 30)

If `python-dotenv` is installed, a local `.env` file will be loaded automatically.

## cron idea

```
0 */6 * * * cd /path/to/px6-proxy-fetcher && px6-proxy-fetcher -o /var/run/proxies.txt
```

Keep `proxies.txt` out of Git; it holds authenticated endpoints. The script writes it with 600 permissions so only your user can read it, and the included `.gitignore` already skips it.

## requirements

- Python 3.9 or later
- A [PROXY6.net](https://px6.me/) account with an API key

## license

MIT - see the included `LICENSE` file.
