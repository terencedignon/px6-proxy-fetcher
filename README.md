# px6-proxy-fetcher

Small helper that grabs your active proxies from [PROXY6.net](https://px6.me/) and drops them into a text file you can hand to whatever is doing the crawling. I've leaned on PX6 as my low-cost proxy pool for months; it's been steady and easy to manage, so this script wraps the one task I end up repeating the most.

## getting started

Clone this repo, jump into it, and install it in editable mode:

```bash
pip install -e .
# want .env support? pip install -e .[dotenv]
```

Run it after setting your API key:

```bash
export PX6_API_KEY="your_api_key_here"
px6-proxy-fetcher --print-env
```

That writes `proxies.txt` in the current directory and, with `--print-env`, emits the exports for `PROXY_LIST` and `PROXY_STRATEGY`. You can point the output elsewhere with `-o path/to/file.txt`. Verbosity toggles: `-q` for quiet, `-v` for chatty.

If `python-dotenv` is present, a local `.env` file will be loaded automatically.

## cron idea

```
0 */6 * * * cd /path/to/px6-proxy-fetcher && px6-proxy-fetcher -o /var/run/proxies.txt
```

Keep `proxies.txt` out of Git-it holds authenticated endpoints. The included `.gitignore` already skips it.

## license

MIT-see the included `LICENSE` file.
