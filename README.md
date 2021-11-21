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

The following stats will be exposed for prometheus on /metrics endpoint:

```
# HELP xb7_collector_ds_lock Lock status of downstream channel, bool.
# TYPE xb7_collector_ds_lock gauge

# HELP xb7_collector_ds_freq Frequency of downstream channel in MHz.
# TYPE xb7_collector_ds_freq gauge

# HELP xb7_collector_ds_snr SNR of downstream channel in dB.
# TYPE xb7_collector_ds_snr gauge

# HELP xb7_collector_ds_power Power level of channel, in dBmV.
# TYPE xb7_collector_ds_power gauge

# HELP xb7_collector_us_lock Lock status of upstrea channel, bool.
# TYPE xb7_collector_us_lock gauge

# HELP xb7_collector_us_freq Frequency of upstream channel in MHz.
# TYPE xb7_collector_us_freq gauge

# HELP xb7_collector_us_symbol Symbol rate of upstream channel.
# TYPE xb7_collector_us_symbol gauge

# HELP xb7_collector_us_power Power level of channel, in dBmV.
# TYPE xb7_collector_us_power gauge

# HELP xb7_collector_ds_unerrored_total Unerrored Codewords of downstream channel, int.
# TYPE xb7_collector_ds_unerrored_total counter

# HELP xb7_collector_ds_correctable_total Unerrored Codewords of downstream channel, int.
# TYPE xb7_collector_ds_correctable_total counter

# HELP xb7_collector_ds_uncorrectable_total Unerrored Codewords of downstream channel, int.
# TYPE xb7_collector_ds_uncorrectable_total counter
```