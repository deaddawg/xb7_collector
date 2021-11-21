# xb7_collector
HTTP collector for Comcast XB7 modem

Uses BeautifulSoup to scrape from Comcast XB7 admin page, exposes metrics on port 7007 (by default)

TODO: add docker container

```
Usage: collector.py [OPTIONS]

Options:
  -i, --ip_address TEXT  IP address of XB7.
  -u, --username TEXT    Username to auth XB7 with.
  -P, --password TEXT    Password to auth XB7 with.
  -p, --port INTEGER     Port to run prometheus collector on.
  -d, --debug
  --help                 Show this message and exit.
  ```